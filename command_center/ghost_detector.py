"""
Ghost Detector - Detects ghosting risks
"""
from datetime import datetime
from typing import Dict, List
from task_engine.tracker import TaskTracker, RiskLevel


class GhostDetector:
    """Detects ghosting risks across projects"""
    
    def __init__(self, tracker: TaskTracker):
        self.tracker = tracker
    
    def detect_all_risks(self) -> Dict[str, str]:
        """Detect ghosting risks for all projects"""
        projects = set(t.project_id for t in self.tracker._tasks.values())
        risks = {}
        
        for project_id in projects:
            risk = self.tracker.detect_ghosting_risk(project_id)
            risks[project_id] = risk.value
        
        return risks
    
    def get_high_risk_projects(self) -> List[str]:
        """Get projects with medium or high ghosting risk"""
        risks = self.detect_all_risks()
        return [
            pid for pid, risk in risks.items()
            if risk in ("medium", "high", "critical")
        ]
    
    def get_risk_summary(self) -> Dict:
        """Get summary of all ghosting risks"""
        risks = self.detect_all_risks()
        summary = {
            "total_projects": len(risks),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "high_risk_projects": []
        }
        
        for pid, risk in risks.items():
            summary[risk] += 1
            if risk != "low":
                summary["high_risk_projects"].append(pid)
        
        return summary