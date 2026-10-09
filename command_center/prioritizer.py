"""
Task Prioritizer - Prioritizes tasks
"""
from datetime import datetime
from typing import List
from task_engine.tracker import Task


class TaskPrioritizer:
    """Prioritizes tasks for execution"""
    
    def prioritize(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by priority and deadline"""
        def sort_key(t: Task):
            priority_score = -t.priority
            
            if t.deadline:
                try:
                    deadline = datetime.fromisoformat(t.deadline)
                    deadline_score = (deadline - datetime.now()).days
                except:
                    deadline_score = 999
            else:
                deadline_score = 999
            
            overdue = 0
            if t.deadline:
                try:
                    if datetime.fromisoformat(t.deadline) < datetime.now():
                        overdue = -1
                except:
                    pass
            
            return (overdue, deadline_score, priority_score)
        
        return sorted(tasks, key=sort_key)