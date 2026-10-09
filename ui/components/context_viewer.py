"""Context Viewer Component - Right sidebar showing live memory and context"""
from textual.widget import Widget
from textual.widgets import Static, Tree
from textual.message import Message
from textual.reactive import reactive


class ContextViewer(Widget):
    """Right sidebar showing live memory, tasks, and context"""
    
    DEFAULT_CSS = """
    ContextViewer {
        width: 1fr;
        background: $panel;
        padding: 1;
    }
    
    .context-section {
        margin-bottom: 1;
    }
    
    .context-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """
    
    def compose(self):
        yield Static("🧠 CONTEXT VIEWER", classes="context-title")
        yield Static("---")
        
        with Static(classes="context-section"):
            yield Static("Active Tasks:", classes="context-title")
            yield Static("1. [ ] Review project timeline\n2. [x] Complete memory setup\n3. [ ] Start editing session")
        
        yield Static("---")
        
        with Static(classes="context-section"):
            yield Static("Ghosting Risk: 🔵 LOW", id="risk-level")
        
        yield Static("---")
        
        with Static(classes="context-section"):
            yield Static("Recent Memory:", classes="context-title")
            yield Static("• Project initialized\n• Memory patterns loaded\n• No bleed detected")