"""
Daily Planner - Generates daily operational plans
"""
from datetime import datetime
from typing import List, Dict
from task_engine.scheduler import TaskScheduler
from command_center.analyzer import WorkloadAnalyzer
from command_center.ghost_detector import GhostDetector


class DailyPlanner:
    """Generates daily operational plans"""
    
    def __init__(self, scheduler: TaskScheduler):
        self.scheduler = scheduler
        self.tracker = scheduler.tracker
    
    def generate_plan(self, project_id: str, max_tasks: int = 5) -> Dict:
        """Generate a daily plan for a project"""
        prioritized = self.scheduler.prioritize_tasks(project_id)[:max_tasks]
        
        tasks = []
        for i, task in enumerate(prioritized):
            deadline_str = ""
            if task.deadline:
                try:
                    deadline = datetime.fromisoformat(task.deadline)
                    deadline_str = deadline.strftime("%b %d, %Y")
                except:
                    pass
            
            tasks.append({
                "order": i + 1,
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "deadline": deadline_str,
                "priority": task.priority,
            })
        
        # Get ghosting risk
        analyzer = WorkloadAnalyzer(self.tracker)
        workload = analyzer.analyze(project_id)
        detector = GhostDetector(self.tracker)
        risk = detector.detect_all_risks().get(project_id, "low")
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "project_id": project_id,
            "tasks": tasks,
            "workload_status": workload.get("status", "unknown"),
            "ghosting_risk": risk
        }
    
    def generate_all_plans(self) -> List[Dict]:
        """Generate plans for all active projects"""
        projects = set(t.project_id for t in self.tracker._tasks.values())
        return [self.generate_plan(pid) for pid in projects]