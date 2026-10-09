"""
Shali Project Isolation Module
Ensures zero memory bleed between client projects
"""
from .manager import ProjectManager
from .scope_guard import scope_guard

__all__ = ['ProjectManager', 'scope_guard']