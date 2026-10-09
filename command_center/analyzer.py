"""
Workload Analyzer - Analyzes project workload
"""
from typing import Dict, List
from task_engine.tracker import TaskTracker, RiskLevel


class WorkloadAnalyzer:
    """Analyzes workload across projects"""
    
    def __init__(self, tracker: TaskTracker):
        self.tracker = tracker
    
    def analyze(self, project_id: str) -> Dict:
        """Analyze workload for a project"""
        tasks = self.tracker.get_project_tasks(project_id)
        incomplete = [t for t in tasks if not t.complete]
        overdue = self.tracker.get_overdue_tasks(project_id)
        
        # Calculate workload score based on priority sum
        total_priority = sum(t.priority for t in incomplete)
        workload_score = min(10, total_priority // 5)
        
        # Determine status
        if workload_score <= 3:
            status = "light"
        elif workload_score <= 6:
            status = "moderate"
        else:
            status = "heavy"
        
        return {
            "total_tasks": len(tasks),
            "incomplete": len(incomplete),
            "overdue": len(overdue),
            "workload_score": workload_score,
            "status": status
        }
    
    def get_all_workloads(self) -> Dict[str, Dict]:
        """Get workload analysis for all projects"""
        projects = set(t.project_id for t in self.tracker._tasks.values())
        return {
            pid: self.analyze(pid)
            for pid in projects
        }
    
    def get_busiest_projects(self, limit: int = 5) -> List[Dict]:
        """Get projects with heaviest workload"""
        workloads = self.get_all_workloads()
        sorted_projects = sorted(
            workloads.items(),
            key=lambda x: x[1].get("workload_score", 0),
            reverse=True
        )
        return [
            {"project_id": pid, **data}
            for pid, data in sorted_projects[:limit]
        ]