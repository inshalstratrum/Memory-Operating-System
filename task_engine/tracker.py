"""
Task Tracker - Deadline tracking and ghosting risk detection
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Task:
    id: str
    project_id: str
    title: str
    description: str
    deadline: Optional[str]
    created_at: str
    updated_at: str
    complete: bool = False
    priority: int = 5
    assigned_to: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class TaskTracker:
    """Tracks tasks and detects ghosting risks"""
    
    def __init__(self, data_file: str = "./data/tasks.json"):
        self.data_file = Path(data_file)
        self._tasks: Dict[str, Task] = {}
        self._load_tasks()
    
    def _load_tasks(self) -> None:
        """Load tasks from storage"""
        if self.data_file.exists():
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                for tid, tdata in data.items():
                    self._tasks[tid] = Task(**tdata)
    
    def _save_tasks(self) -> None:
        """Save tasks to storage"""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(
                {tid: asdict(t) for tid, t in self._tasks.items()},
                f,
                indent=2,
                default=str
            )
    
    def create_task(
        self,
        project_id: str,
        title: str,
        description: str = "",
        deadline: Optional[str] = None,
        priority: int = 5,
        assigned_to: Optional[str] = None,
        tags: List[str] = None
    ) -> Task:
        """Create a new task"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._tasks)}"
        
        task = Task(
            id=task_id,
            project_id=project_id,
            title=title,
            description=description,
            deadline=deadline,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            priority=priority,
            assigned_to=assigned_to,
            tags=tags or []
        )
        
        self._tasks[task_id] = task
        self._save_tasks()
        return task
    
    def get_project_tasks(self, project_id: str) -> List[Task]:
        """Get all tasks for a project"""
        return [
            t for t in self._tasks.values()
            if t.project_id == project_id
        ]
    
    def get_overdue_tasks(self, project_id: str) -> List[Task]:
        """Get overdue tasks for a project"""
        now = datetime.now()
        tasks = self.get_project_tasks(project_id)
        overdue = []
        
        for task in tasks:
            if task.deadline and not task.complete:
                try:
                    deadline = datetime.fromisoformat(task.deadline)
                    if deadline < now:
                        overdue.append(task)
                except:
                    pass
        
        return overdue
    
    def complete_task(self, task_id: str) -> bool:
        """Mark a task as complete"""
        if task_id in self._tasks:
            self._tasks[task_id].complete = True
            self._tasks[task_id].updated_at = datetime.now().isoformat()
            self._save_tasks()
            return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save_tasks()
            return True
        return False
    
    def detect_ghosting_risk(
        self,
        project_id: str,
        days_since_contact: Optional[int] = None
    ) -> RiskLevel:
        """
        Detect ghosting risk for a project
        
        Algorithm:
        - HIGH: >3 overdue tasks + no contact for 3+ days
        - MEDIUM: >1 overdue task + no contact for 7+ days
        - LOW: No overdue tasks
        """
        overdue = self.get_overdue_tasks(project_id)
        overdue_count = len(overdue)
        
        # If days_since_contact not provided, check task deadlines
        if days_since_contact is None:
            # Calculate from most recent task deadline
            project_tasks = self.get_project_tasks(project_id)
            deadlines = [
                datetime.fromisoformat(t.deadline)
                for t in project_tasks
                if t.deadline
            ]
            if deadlines:
                most_recent = max(deadlines)
                days_since_contact = (datetime.now() - most_recent).days
            else:
                days_since_contact = 0
        
        # Risk assessment
        if overdue_count >= 3 and days_since_contact >= 3:
            return RiskLevel.HIGH
        elif overdue_count >= 1 and days_since_contact >= 7:
            return RiskLevel.MEDIUM
        elif overdue_count >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def get_risky_projects(self) -> Dict[str, RiskLevel]:
        """Get ghosting risk levels for all projects"""
        projects = set(t.project_id for t in self._tasks.values())
        risks = {}
        
        for project_id in projects:
            risks[project_id] = self.detect_ghosting_risk(project_id)
        
        return {
            pid: risk.value
            for pid, risk in risks.items()
            if risk != RiskLevel.LOW
        }
    
    def get_upcoming_deadlines(self, days: int = 7) -> List[Task]:
        """Get tasks due within specified days"""
        now = datetime.now()
        end = now + timedelta(days=days)
        
        upcoming = []
        for task in self._tasks.values():
            if task.deadline and not task.complete:
                try:
                    deadline = datetime.fromisoformat(task.deadline)
                    if now <= deadline <= end:
                        upcoming.append(task)
                except:
                    pass
        
        return sorted(upcoming, key=lambda t: t.deadline or "")