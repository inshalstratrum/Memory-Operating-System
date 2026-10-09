"""Architecture Canvas Component - Drag-and-drop node editor"""
from textual.widget import Widget
from textual.widgets import Static
from textual.message import Message


class Node(Static):
    """A node in the architecture canvas"""
    
    DEFAULT_CSS = """
    Node {
        background: $surface;
        border: round $primary;
        padding: 1 2;
        margin: 1;
        min-width: 20;
    }
    """
    
    def __init__(self, name: str, node_type: str = "default"):
        super().__init__()
        self.node_name = name
        self.node_type = node_type
    
    def compose(self):
        yield Static(f"[{self.node_type}] {self.node_name}")


class ArchitectureCanvas(Widget):
    """Visual architecture canvas with nodes and connections"""
    
    DEFAULT_CSS = """
    ArchitectureCanvas {
        layout: vertical;
    }
    
    #canvas-container {
        height: 1fr;
        background: $surface-darken-1;
    }
    """
    
    def compose(self):
        yield Static("⚙️ ARCHITECTURE CANVAS", classes="context-title")
        yield Static("Drag nodes to create connections. Ctrl+Click to add nodes.")
        
        with Static(id="canvas-container"):
            yield Node("Orchestrator", "core")
            yield Node("Project Manager", "module")
            yield Node("Task Engine", "module")
            yield Node("Memory DB", "data")
            yield Node("Command Center", "core")