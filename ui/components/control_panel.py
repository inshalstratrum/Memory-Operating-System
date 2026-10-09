"""God-Control Panel Component - Emergency overrides and system controls"""
from textual.widget import Widget
from textual.widgets import Static, Button
from textual.containers import Horizontal, Vertical
from textual.message import Message


class GodControlPanel(Widget):
    """God-mode control panel for emergency overrides"""
    
    DEFAULT_CSS = """
    GodControlPanel {
        layout: vertical;
    }
    
    .control-section {
        margin-bottom: 2;
    }
    
    .Control-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    .emergency-btn {
        background: $error;
        color: white;
        margin: 1;
    }
    
    .warning-btn {
        background: $warning;
        color: black;
        margin: 1;
    }
    """
    
    def compose(self):
        yield Static("👑 GOD CONTROL PANEL", classes="Control-title")
        
        with Static(classes="control-section"):
            yield Static("Emergency Controls:", classes="Control-title")
            yield Button("🛑 EMERGENCY STOP", id="emergency-stop", variant="error")
            yield Button("🔄 FORCE RESTART", id="force-restart", variant="warning")
        
        with Static(classes="control-section"):
            yield Static("System Status:", classes="Control-title")
            yield Static("• Memory Engine: [green]ONLINE[/]")
            yield Static("• Task Engine: [green]ONLINE[/]")
            yield Static("• Ghost Detector: [green]ONLINE[/]")
        
        with Static(classes="control-section"):
            yield Static("Quick Actions:", classes="Control-title")
            yield Button("Generate Daily Plan", id="daily-plan", variant="success")
            yield Button("Check Ghosting Risks", id="check-ghosting", variant="primary")
    
    def on_button_pressed(self, event):
        if event.button.id == "emergency-stop":
            self.app.bell()
            self.app.exit()
        elif event.button.id == "daily-plan":
            self.generate_daily_plan()
        elif event.button.id == "check-ghosting":
            self.check_ghosting()
    
    def generate_daily_plan(self):
        """Generate daily plan for active project"""
        if self.app.orchestrator:
            scheduler = self.app.orchestrator.task_tracker
            if scheduler:
                plan = scheduler.scheduler.generate_daily_plan(self.app.active_project)
                self.mount(Static(f"Plan: {plan}", classes="chat-ai"))
    
    def check_ghosting(self):
        """Check ghosting risks"""
        if self.app.orchestrator:
            tracker = self.app.orchestrator.task_tracker
            if tracker:
                risks = tracker.detect_ghosting_risk(self.app.active_project)
                self.mount(Static(f"Ghosting Risk: {risks.value}", classes="chat-ai"))