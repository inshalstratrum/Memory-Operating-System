"""
Scope Guard - Prevents memory bleed between projects
"""
from typing import Dict, Any, Optional
import hashlib


class ScopeGuard:
    """Ensures memory operations stay within project boundaries"""
    
    def __init__(self):
        self._project_memories: Dict[str, set] = {}  # project_id -> set of memory_ids
        self._active_project: Optional[str] = None
    
    def set_active_project(self, project_id: str) -> None:
        """Set the currently active project scope"""
        self._active_project = self._sanitize_project_id(project_id)
        if self._active_project not in self._project_memories:
            self._project_memories[self._active_project] = set()
    
    def get_active_project(self) -> Optional[str]:
        """Get the currently active project"""
        return self._active_project
    
    def _sanitize_project_id(self, project_id: str) -> str:
        """Sanitize project ID for safe database naming"""
        import re
        clean = re.sub(r'[^a-z0-9_-]', '_', project_id.lower())
        clean = clean.strip('_')
        if len(clean) < 3:
            clean = "proj_" + clean
        return clean[:60]
    
    def validate_memory(self, memory: Dict[str, Any], project_id: str) -> bool:
        """Validate that memory belongs to the specified project"""
        if not memory:
            return False
        
        memory_project = memory.get('project_id', memory.get('workspace', ''))
        memory_project = self._sanitize_project_id(str(memory_project))
        expected_project = self._sanitize_project_id(project_id)
        
        return memory_project == expected_project
    
    def filter_memories(self, memories: list, project_id: str) -> list:
        """Filter memories to only include those from the specified project"""
        return [
            m for m in memories 
            if self.validate_memory(m, project_id)
        ]
    
    def register_memory(self, memory_id: str, project_id: str) -> None:
        """Register a memory ID as belonging to a project"""
        safe_id = self._sanitize_project_id(project_id)
        if safe_id not in self._project_memories:
            self._project_memories[safe_id] = set()
        self._project_memories[safe_id].add(str(memory_id))
    
    def is_registered(self, memory_id: str, project_id: str) -> bool:
        """Check if a memory ID is registered to a project"""
        safe_id = self._sanitize_project_id(project_id)
        return str(memory_id) in self._project_memories.get(safe_id, set())


# Global scope guard instance
scope_guard = ScopeGuard()


def validate_project_context(project_id: str, memory: dict) -> bool:
    """Convenience function to validate memory belongs to project"""
    return scope_guard.validate_memory(memory, project_id)