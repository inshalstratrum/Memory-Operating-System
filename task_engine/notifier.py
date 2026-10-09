"""
Task Notifier - Alerts and notifications
"""
from datetime import datetime
from typing import List, Dict, Optional
from .tracker import TaskTracker, Task, RiskLevel


class TaskNotifier:
    """Generates alerts for tasks and risks"""
    
    def __init__(self, tracker: TaskTracker):
        self.tracker = tracker
    
    def get_alerts(self, project_id: str) -> List[Dict]:
        """Get all alerts for a project"""
        alerts = []
        
        # Overdue tasks
        overdue = self.tracker.get_overdue_tasks(project_id)
        for task in overdue:
            alerts.append({
                "type": "overdue",
                "severity": "high",
                "task_id": task.id,
                "message": f"Task '{task.title}' is overdue"
            })
        
        # Ghosting risk
        risk = self.tracker.detect_ghosting_risk(project_id)
        if risk != RiskLevel.LOW:
            alerts.append({
                "type": "ghosting_risk",
                "severity": risk.value,
                "message": f"Ghosting risk detected: {risk.value}"
            })
        
        # Upcoming deadlines
        upcoming = self.tracker.get_upcoming_deadlines(3)
        for task in upcoming:
            if task.project_id == project_id:
                alerts.append({
                    "type": "upcoming",
                    "severity": "medium",
                    "task_id": task.id,
                    "message": f"Task '{task.title}' due soon"
                })
        
        return alerts
    
    def get_all_alerts(self) -> List[Dict]:
        """Get alerts across all projects"""
        all_alerts = []
        projects = set(t.project_id for t in self.tracker._tasks.values())
        
        for project_id in projects:
            alerts = self.get_alerts(project_id)
            for alert in alerts:
                alert["project_id"] = project_id
                all_alerts.append(alert)
        
        return sorted(all_alerts, key=lambda a: {
            "high": 0, "critical": 0, "medium": 1, "low": 2
        }.get(a.get("severity", "low"), 3))