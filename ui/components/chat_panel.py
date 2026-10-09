"""Chat Panel Component"""
from textual.widget import Widget
from textual.widgets import Static, Input, Button
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive


class ChatPanel(Widget):
    """Central chat interface"""
    
    DEFAULT_CSS = """
    ChatPanel {
        layout: vertical;
    }
    
    #chat-messages {
        height: 1fr;
        overflow: auto;
    }
    
    #chat-input-area {
        height: 10;
        dock: bottom;
    }
    
    .chat-user {
        background: $boost;
        margin: 1 2;
        padding: 1 2;
        border-radius: 4;
    }
    
    .chat-ai {
        background: $primary;
        margin: 1 2;
        padding: 1 2;
        border-radius: 4;
    }
    """
    
    messages = reactive([])
    
    def compose(self):
        yield Static(id="chat-messages")
        
        with Horizontal(id="chat-input-area"):
            yield Input(placeholder="Type your message...", id="message-input")
            yield Button("Send", id="send-btn", variant="primary")
    
    def on_button_pressed(self, event):
        if event.button.id == "send-btn":
            self.send_message()
    
    def on_input_submitted(self, event):
        if event.input.id == "message-input":
            self.send_message()
    
    def send_message(self):
        input_widget = self.query_one("#message-input", Input)
        text = input_widget.value.strip()
        if text:
            self.add_message("user", text)
            input_widget.value = ""
            # Process through orchestrator
            self.process_message(text)
    
    def add_message(self, sender: str, text: str):
        self.messages.append((sender, text))
        chat = self.query_one("#chat-messages", Static)
        css_class = "chat-user" if sender == "user" else "chat-ai"
        chat.mount(Static(f"{sender}: {text}", classes=css_class))
    
    def process_message(self, text: str):
        """Process message through orchestrator"""
        if self.app.orchestrator:
            result = self.app.orchestrator.process_input(text, self.app.active_project)
            self.add_message("shali", result["text"])