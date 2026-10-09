import datetime
import re

from core.memory import retrieve_memory, store_memory, retrieve_feedback
from core.agents import select_agent, run_agent
from tools.automation import run_task
from project_isolation.manager import ProjectManager
from project_isolation.scope_guard import scope_guard
from task_engine.tracker import TaskTracker


class Orchestrator:
    def __init__(self):
        print("[ORCHESTRATOR] Brain initialized and ready.")
        self.project_manager = ProjectManager()
        self.task_tracker = TaskTracker()
        self.active_project = "command_center"
        scope_guard.set_active_project(self.active_project)

    def set_active_project(self, project_id: str):
        """Set the active project context"""
        self.active_project = project_id
        scope_guard.set_active_project(project_id)
        print(f"[ORCHESTRATOR] Active project set to: {project_id}")

    def rank_memories(self, memories, workspace="command_center"):
        ranked = []
        for m in memories:
            score = 0.5
            if "time" in m:
                try:
                    t = datetime.datetime.fromisoformat(m["time"])
                    score -= (datetime.datetime.now() - t).days * 0.02
                except: pass
            if "importance" in m:
                score += float(m.get("importance", 0)) * 0.5
            if "content" in m:
                feedback_score = retrieve_feedback(m["content"], workspace)
                score += feedback_score * 0.1
            ranked.append((score, m))
        ranked.sort(reverse=True, key=lambda x: x[0])
        return [m[1] for m in ranked[:5]]

    def extract_params(self, user_input):
        filename, content = "output.txt", user_input
        file_match = re.search(r"([\w\.-]+\.(?:txt|py|json|md|html))", user_input)
        if file_match: filename = file_match.group(1)
        content_match = re.search(r"['\"](.*?)['\"]", user_input)
        if content_match: content = content_match.group(1)
        return filename, content

    def should_use_tool(self, user_input):
        ui = user_input.lower()
        tools = {
            "file": ["create a file", "create file", "save file", "make a file", "write a document"],
            "automation": ["run script", "execute", "list files", "delete file", "read file"],
        }
        for tool, keywords in tools.items():
            if any(k in ui for k in keywords): return tool
        return None

    def build_context(self, memories):
        return "".join([f"[{m.get('type','mem')}] {m.get('content','')}\n" if isinstance(m, dict) else f"{m}\n" for m in memories])

    def process_input(self, user_input, project_id="command_center", guidelines="", forced_agent="Auto", feedback="neutral", thread_id=None):
        
        # Update active project context
        self.set_active_project(project_id)
        
        if forced_agent == "Auto":
            agent = select_agent(user_input)
        else:
            agent = forced_agent.lower()
        
        if thread_id:
            from core.memory import retrieve_thread_memory
            raw_memories = retrieve_thread_memory(user_input, project_id, thread_id)
        else:
            raw_memories = retrieve_memory(user_input, project_id)
            
        context = self.build_context(self.rank_memories(raw_memories, project_id))
        
        tool = self.should_use_tool(user_input)
        tool_result = None
        if tool:
            fname, fcontent = self.extract_params(user_input)
            tool_result = run_task(user_input, filename=fname, content=fcontent)
        
        response = run_agent(agent, user_input, context, project_id, guidelines)
        
        if tool_result: 
            response += f"\n\n⚙️ [System Action]:\n{tool_result}"
        
        timestamp = str(datetime.datetime.now())
        memory_meta = {"type": "user_input", "content": user_input, "time": timestamp, "project_id": project_id}
        if thread_id:
            memory_meta["thread_id"] = thread_id
        store_memory(memory_meta, project_id)
        
        response_meta = {"type": "ai_response", "content": response, "time": timestamp, "project_id": project_id}
        if thread_id:
            response_meta["thread_id"] = thread_id
        store_memory(response_meta, project_id)
        
        if feedback in ("up", "down"):
            from core.memory import store_feedback
            store_feedback(user_input, response, feedback, project_id)
        
        return {
            "text": response,
            "agent": agent,
            "memory_pulled": context
        }
