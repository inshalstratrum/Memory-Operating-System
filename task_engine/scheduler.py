"""
Task Scheduler - Planning and prioritization
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .tracker import Task, TaskTracker


class TaskScheduler:
    """Plans tasks and generates daily plans"""
    
    def __init__(self, tracker: TaskTracker):
        self.tracker = tracker
    
    def prioritize_tasks(self, project_id: str) -> List[Task]:
        """Prioritize tasks based on deadline and priority"""
        tasks = self.tracker.get_project_tasks(project_id)
        incomplete = [t for t in tasks if not t.complete]
        
        def sort_key(t: Task):
            # Higher priority value first
            priority_score = -t.priority
            
            # Earlier deadline first
            if t.deadline:
                try:
                    deadline = datetime.fromisoformat(t.deadline)
                    deadline_score = (deadline - datetime.now()).days
                except:
                    deadline_score = 999
            else:
                deadline_score = 999
            
            # Overdue tasks first
            overdue = 0
            if t.deadline:
                try:
                    if datetime.fromisoformat(t.deadline) < datetime.now():
                        overdue = -1
                except:
                    pass
            
            return (overdue, deadline_score, priority_score)
        
        return sorted(incomplete, key=sort_key)
    
    def generate_daily_plan(
        self,
        project_id: str,
        max_tasks: int = 5
    ) -> List[Dict]:
        """Generate a daily plan of tasks"""
        prioritized = self.prioritize_tasks(project_id)[:max_tasks]
        
        plan = []
        for i, task in enumerate(prioritized):
            deadline_str = ""
            if task.deadline:
                try:
                    deadline = datetime.fromisoformat(task.deadline)
                    deadline_str = deadline.strftime("%b %d")
                except:
                    pass
            
            plan.append({
                "order": i + 1,
                "id": task.id,
                "title": task.title,
                "deadline": deadline_str,
                "priority": task.priority,
                "estimated_time": "2-4 hours",  # Default estimate
            })
        
        return plan
    
    def get_workload_analysis(self, project_id: str) -> Dict:
        """Analyze project workload"""
        tasks = self.tracker.get_project_tasks(project_id)
        incomplete = [t for t in tasks if not t.complete]
        overdue = self.tracker.get_overdue_tasks(project_id)
        
        # Calculate workload score
        total_priority = sum(t.priority for t in incomplete)
        workload_score = min(10, total_priority // 5)
        
        return {
            "total_tasks": len(tasks),
            "incomplete": len(incomplete),
            "overdue": len(overdue),
            "workload_score": workload_score,
            "status": self._get_workload_status(workload_score)
        }
    
    def _get_workload_status(self, score: int) -> str:
        """Convert workload score to status string"""
        if score <= 3:
            return "light"
        elif score <= 6:
            return "moderate"
        else:
            return "heavy"