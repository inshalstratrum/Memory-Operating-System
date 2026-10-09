"""Project Sidebar Component"""
from textual.widget import Widget
from textual.widgets import Static, ListView, ListItem
from textual.message import Message
from textual.reactive import reactive


class ProjectItem(ListItem):
    """A project list item"""
    
    def __init__(self, project_id: str, name: str, status: str = "active"):
        super().__init__()
        self.project_id = project_id
        self.name = name
        self.status = status
    
    def compose(self):
        status_icon = "●" if self.status == "active" else "○"
        status_color = "green" if self.status == "active" else "gray"
        yield Static(f"[{status_color}]{status_icon}[/] {self.name}", classes="project-item")


class ProjectSidebar(Widget):
    """Left sidebar with project list"""
    
    DEFAULT_CSS = """
    ProjectSidebar {
        background: $primary;
        padding: 1 2;
    }
    
    .sidebar-header {
        text-align: center;
        margin-bottom: 1;
    }
    
    .project-item {
        padding: 1;
    }
    """
    
    projects = reactive([])
    
    def compose(self):
        with Static(classes="sidebar-header"):
            yield Static("📁 PROJECTS", id="sidebar-title")
        
        yield Static("---", id="separator")
        
        with ListView(id="project-list"):
            yield ProjectItem("command_center", "Command Center", "active")
            yield ProjectItem("project_alpha", "Alpha Project")
            yield ProjectItem("project_beta", "Beta Project")
    
    def on_list_view_selected(self, event):
        """Handle project selection"""
        if hasattr(event.item, 'project_id'):
            self.app.active_project = event.item.project_id
            self.app.bell()