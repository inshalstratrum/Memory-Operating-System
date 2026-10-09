"""
Project Manager - Handles project lifecycle and isolation
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

from .scope_guard import ScopeGuard, scope_guard


@dataclass
class ProjectConfig:
    """Project configuration and metadata"""
    id: str
    name: str
    client_name: str
    created_at: str
    status: str = "active"  # active, archived, completed
    deadline: Optional[str] = None
    priority: int = 5  # 1-10 scale
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class ProjectManager:
    """Manages project lifecycle and isolation"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.projects_file = self.data_dir / "projects.json"
        self.scope_guard = scope_guard
        self._projects: Dict[str, ProjectConfig] = {}
        self._load_projects()
    
    def _load_projects(self) -> None:
        """Load projects from storage"""
        if self.projects_file.exists():
            with open(self.projects_file, 'r') as f:
                data = json.load(f)
                for pid, pdata in data.items():
                    try:
                        self._projects[pid] = ProjectConfig(
                            id=pid,
                            name=pdata.get("name", pid),
                            client_name=pdata.get("client_name", "Unknown"),
                            created_at=pdata.get("created_at", datetime.now().isoformat()),
                            status=pdata.get("status", "active"),
                            deadline=pdata.get("deadline"),
                            priority=pdata.get("priority", 5),
                            tags=pdata.get("tags", [])
                        )
                    except Exception as e:
                        # Skip malformed projects
                        print(f"[WARNING] Skipping malformed project {pid}: {e}")
        else:
            # Default projects
            self._projects["command_center"] = ProjectConfig(
                id="command_center",
                name="Command Center",
                client_name="System",
                created_at=datetime.now().isoformat(),
                status="active",
                priority=10
            )
            self._save_projects()
    
    def _save_projects(self) -> None:
        """Save projects to storage"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.projects_file, 'w') as f:
            json.dump(
                {pid: asdict(p) for pid, p in self._projects.items()},
                f,
                indent=2
            )
    
    def create_project(
        self,
        name: str,
        client_name: str,
        deadline: Optional[str] = None,
        priority: int = 5,
        tags: List[str] = None
    ) -> ProjectConfig:
        """Create a new project with isolated memory"""
        import re
        project_id = re.sub(r'[^a-z0-9_-]', '_', name.lower()).strip('_')[:60]
        
        project = ProjectConfig(
            id=project_id,
            name=name,
            client_name=client_name,
            created_at=datetime.now().isoformat(),
            deadline=deadline,
            priority=priority,
            tags=tags or []
        )
        
        self._projects[project_id] = project
        self._save_projects()
        
        # Initialize isolated memory collection
        self._initialize_project_memory(project_id)
        
        return project
    
    def _initialize_project_memory(self, project_id: str) -> None:
        """Initialize isolated chroma collection for project"""
        # This will be called when storing first memory
        pass
    
    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        """Get project by ID"""
        return self._projects.get(project_id)
    
    def list_projects(self) -> List[ProjectConfig]:
        """List all projects"""
        return list(self._projects.values())
    
    def get_active_project(self) -> Optional[ProjectConfig]:
        """Get currently active project"""
        active_id = self.scope_guard.get_active_project()
        if active_id:
            return self._projects.get(active_id)
        return self._projects.get("command_center")
    
    def set_active_project(self, project_id: str) -> None:
        """Set active project"""
        if project_id in self._projects:
            self.scope_guard.set_active_project(project_id)
    
    def archive_project(self, project_id: str) -> bool:
        """Archive a project"""
        if project_id in self._projects:
            self._projects[project_id].status = "archived"
            self._save_projects()
            return True
        return False
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project (soft delete)"""
        if project_id in self._projects:
            del self._projects[project_id]
            self._save_projects()
            return True
        return False
    
    def get_project_memory_path(self, project_id: str) -> Path:
        """Get the memory path for a project"""
        return self.data_dir / "chroma_db" / project_id