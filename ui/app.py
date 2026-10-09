"""
Shali God-Control UI - Main Application
A three-panel TUI with advanced architecture visualization
"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Horizontal, Vertical
from textual.message import Message

from ui.components.project_sidebar import ProjectSidebar
from ui.components.chat_panel import ChatPanel
from ui.components.context_viewer import ContextViewer
from ui.components.architecture_canvas import ArchitectureCanvas
from ui.components.control_panel import GodControlPanel


class ShaliApp(App):
    """God-Control Architecture UI for Shali"""
    
    CSS_PATH = "shali.tcss"
    
    BINDINGS = [
        ("ctrl+p", "focus_projects", "Projects"),
        ("ctrl+c", "focus_chat", "Chat"),
        ("ctrl+x", "focus_context", "Context"),
        ("ctrl+g", "toggle_canvas", "Canvas"),
        ("ctrl+d", "toggle_control", "Control"),
        ("ctrl+q", "quit", "Quit"),
    ]
    
    def __init__(self, orchestrator=None):
        super().__init__()
        self.orchestrator = orchestrator
        self.active_project = "command_center"
        self.show_canvas = False
        self.show_control = False
    
    def compose(self) -> ComposeResult:
        """Create the UI layout"""
        with Horizontal():
            yield ProjectSidebar(id="sidebar")
            with Vertical():
                with Horizontal(id="main-content"):
                    with Vertical(id="chat-area"):
                        yield Header()
                        yield ChatPanel(id="chat")
                        yield Footer()
                    with Vertical(id="context-area"):
                        yield ContextViewer(id="context")
                    with Vertical(id="canvas-area", classes="hidden"):
                        yield ArchitectureCanvas(id="canvas")
                    with Vertical(id="control-area", classes="hidden"):
                        yield GodControlPanel(id="control")
    
    def on_mount(self) -> None:
        """Initialize the app"""
        self.title = "🧠 Shali - God-Control Architecture UI"
        self.sub_title = "Local First Cognitive Operating System"
    
    def action_focus_projects(self) -> None:
        """Focus the project sidebar"""
        self.query_one(ProjectSidebar).focus()
    
    def action_focus_chat(self) -> None:
        """Focus the chat panel"""
        self.query_one(ChatPanel).focus()
    
    def action_focus_context(self) -> None:
        """Focus the context viewer"""
        self.query_one(ContextViewer).focus()
    
    def action_toggle_canvas(self) -> None:
        """Toggle architecture canvas visibility"""
        self.show_canvas = not self.show_canvas
        canvas = self.query_one("#canvas-area")
        if self.show_canvas:
            canvas.remove_class("hidden")
        else:
            canvas.add_class("hidden")
    
    def action_toggle_control(self) -> None:
        """Toggle god control panel visibility"""
        self.show_control = not self.show_control
        control = self.query_one("#control-area")
        if self.show_control:
            control.remove_class("hidden")
        else:
            control.add_class("hidden")