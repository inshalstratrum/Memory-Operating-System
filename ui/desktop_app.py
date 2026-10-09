import sys
import os
import json
import uuid
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextBrowser, QLineEdit, QPushButton, QLabel, QListWidget, 
                             QInputDialog, QStackedWidget, QGridLayout, 
                             QTextEdit, QFrame, QScrollArea, QDialog, QFormLayout, QComboBox,
                             QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QCursor

PROJECTS_FILE = os.path.abspath("./data/projects.json")

class AIWorker(QThread):
    finished = pyqtSignal(object)

    def __init__(self, orchestrator, user_input, project_id, instructions, forced_agent, thread_id=None):
        super().__init__()
        self.orchestrator = orchestrator
        self.user_input = user_input
        self.project_id = project_id
        self.instructions = instructions
        self.forced_agent = forced_agent
        self.thread_id = thread_id

    def run(self):
        try:
            result = self.orchestrator.process_input(self.user_input, self.project_id, self.instructions, self.forced_agent, thread_id=self.thread_id)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"text": f"[System Error]: {str(e)}", "agent": "error", "memory_pulled": ""})

class MemoryOSMainWindow(QMainWindow):
    def __init__(self, orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.current_project_id = None
        self.current_thread_id = None
        self.load_projects()
        self.init_ui()

    def load_projects(self):
        if os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, "r") as f:
                self.projects = json.load(f)
                for pid, pdata in self.projects.items():
                    if "threads" in pdata:
                        for tid, tdata in pdata["threads"].items():
                            if isinstance(tdata, str):
                                pdata["threads"][tid] = {"name": tdata, "messages": []}
        else:
            self.projects = {}
            self.save_projects()

    def save_projects(self):
        with open(PROJECTS_FILE, "w") as f:
            json.dump(self.projects, f, indent=4)

    def init_ui(self):
        self.setWindowTitle("🧠 Memory OS v5 - Workstation")
        self.resize(1400, 850)
        self.setStyleSheet("background-color: #242424; color: #E5E3DB; font-family: 'Segoe UI';")

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.build_dashboard_screen()
        self.build_project_hub_screen()
        self.build_chat_screen()

        self.refresh_dashboard()

    def build_dashboard_screen(self):
        self.dash_widget = QWidget()
        layout = QVBoxLayout(self.dash_widget)
        layout.setContentsMargins(40, 40, 40, 40)

        header_layout = QHBoxLayout()
        title = QLabel("Projects")
        title.setFont(QFont("Georgia", 24, QFont.Bold))
        
        btn_new_proj = QPushButton("+ New project")
        btn_new_proj.setFixedSize(120, 40)
        btn_new_proj.setStyleSheet("background-color: #E5E3DB; color: #242424; border-radius: 6px; font-weight: bold;")
        btn_new_proj.setCursor(QCursor(Qt.PointingHandCursor))
        btn_new_proj.clicked.connect(self.create_new_project)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_new_proj)
        layout.addLayout(header_layout)
        layout.addSpacing(20)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.grid_widget)
        scroll.setStyleSheet("border: none;")
        layout.addWidget(scroll)

        self.stacked_widget.addWidget(self.dash_widget)

    def refresh_dashboard(self):
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)

        row, col = 0, 0
        for pid, pdata in self.projects.items():
            card = QPushButton()
            card.setFixedSize(350, 180)
            card.setStyleSheet("QPushButton { background-color: #2D2D2D; border: 1px solid #3E3E3E; border-radius: 12px; text-align: left; padding: 20px; } QPushButton:hover { background-color: #383838; border: 1px solid #5A5A5A; }")
            card.setCursor(QCursor(Qt.PointingHandCursor))
            
            c_layout = QVBoxLayout(card)
            c_title = QLabel(pdata["name"])
            c_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
            c_desc = QLabel(pdata["goal"][:100] + "..." if len(pdata["goal"]) > 100 else pdata["goal"])
            c_desc.setWordWrap(True)
            c_desc.setStyleSheet("color: #A0A0A0;")
            
            c_layout.addWidget(c_title)
            c_layout.addWidget(c_desc)
            c_layout.addStretch()
            card.clicked.connect(lambda checked, p=pid: self.open_project_hub(p))
            
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

    def create_new_project(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create a personal project")
        dialog.setFixedSize(500, 300)
        dialog.setStyleSheet("background-color: #242424; color: #E5E3DB;")
        
        layout = QFormLayout(dialog)
        name_input = QLineEdit()
        name_input.setStyleSheet("background-color: #2D2D2D; border: 1px solid #3E3E3E; padding: 10px; border-radius: 6px;")
        layout.addRow("What are you working on?", name_input)
        
        goal_input = QTextEdit()
        goal_input.setStyleSheet("background-color: #2D2D2D; border: 1px solid #3E3E3E; padding: 10px; border-radius: 6px;")
        layout.addRow("What are you trying to achieve?", goal_input)
        
        btn_box = QHBoxLayout()
        save_btn = QPushButton("Create project")
        save_btn.setStyleSheet("background-color: #E5E3DB; color: #242424; padding: 10px; border-radius: 6px;")
        save_btn.clicked.connect(dialog.accept)
        btn_box.addStretch()
        btn_box.addWidget(save_btn)
        layout.addRow(btn_box)

        if dialog.exec_():
            pid = str(uuid.uuid4())
            self.projects[pid] = {
                "name": name_input.text(),
                "goal": goal_input.toPlainText(),
                "instructions": "", # THE FIX: This now starts completely blank!
                "threads": {}, 
                "files": []
            }
            self.save_projects()
            self.refresh_dashboard()

    def build_project_hub_screen(self):
        self.hub_widget = QWidget()
        layout = QVBoxLayout(self.hub_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        top_bar = QHBoxLayout()
        back_btn = QPushButton("← All projects")
        back_btn.setFlat(True)
        back_btn.setStyleSheet("color: #A0A0A0; font-size: 14px;")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        top_bar.addWidget(back_btn)
        
        # Added a delete button here for easy management
        del_btn = QPushButton("🗑️ Delete Project")
        del_btn.setFlat(True)
        del_btn.setStyleSheet("color: #f38ba8; font-size: 14px;")
        del_btn.setCursor(QCursor(Qt.PointingHandCursor))
        del_btn.clicked.connect(self.delete_current_project)
        top_bar.addStretch()
        top_bar.addWidget(del_btn)
        
        layout.addLayout(top_bar)

        self.hub_title = QLabel("PROJECT TITLE")
        self.hub_title.setFont(QFont("Georgia", 22))
        self.hub_desc = QLabel("Project Description")
        self.hub_desc.setStyleSheet("color: #A0A0A0;")
        self.hub_desc.setWordWrap(True)
        layout.addWidget(self.hub_title)
        layout.addWidget(self.hub_desc)
        layout.addSpacing(20)

        split_layout = QHBoxLayout()

        left_panel = QVBoxLayout()
        
        input_container = QFrame()
        input_container.setStyleSheet("background-color: #2D2D2D; border: 1px solid #3E3E3E; border-radius: 12px; padding: 5px;")
        inp_layout = QHBoxLayout(input_container)
        self.new_chat_input = QLineEdit()
        self.new_chat_input.setPlaceholderText("How can I help you today?")
        self.new_chat_input.setStyleSheet("background-color: transparent; border: none; font-size: 14px;")
        self.new_chat_input.returnPressed.connect(self.start_new_thread)
        inp_layout.addWidget(self.new_chat_input)
        left_panel.addWidget(input_container)
        left_panel.addSpacing(20)

        self.threads_list = QListWidget()
        self.threads_list.setStyleSheet("QListWidget { background-color: transparent; border: none; } QListWidget::item { padding: 15px; border-bottom: 1px solid #3E3E3E; } QListWidget::item:hover { background-color: #2D2D2D; border-radius: 8px;}")
        self.threads_list.itemClicked.connect(self.open_thread)
        left_panel.addWidget(self.threads_list)
        
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(20, 0, 0, 0)
        
        inst_label = QLabel("Instructions (System Prompt)")
        inst_label.setStyleSheet("color: #A0A0A0; font-weight: bold;")
        self.inst_box = QTextEdit()
        self.inst_box.setPlaceholderText("Add specific rules, brand guidelines, or client psychology for this project here...")
        self.inst_box.setStyleSheet("background-color: #2D2D2D; border: 1px solid #3E3E3E; border-radius: 8px; padding: 10px;")
        self.inst_box.textChanged.connect(self.save_instructions)
        
        db_label = QLabel("Live Database View")
        db_label.setStyleSheet("color: #a6e3a1; font-weight: bold; margin-top: 15px;")
        self.hub_db_viewer = QTextBrowser()
        self.hub_db_viewer.setFont(QFont("Consolas", 9))
        self.hub_db_viewer.setStyleSheet("background-color: #11111b; border: 1px solid #313244; border-radius: 8px; padding: 10px; color: #f38ba8;")
        self.hub_db_viewer.setText("> Awaiting database query...")

        right_panel.addWidget(inst_label)
        right_panel.addWidget(self.inst_box, stretch=1)
        right_panel.addWidget(db_label)
        right_panel.addWidget(self.hub_db_viewer, stretch=2)

        split_layout.addLayout(left_panel, stretch=7)
        split_layout.addLayout(right_panel, stretch=3)
        layout.addLayout(split_layout)
        self.stacked_widget.addWidget(self.hub_widget)

    def delete_current_project(self):
        reply = QMessageBox.question(self, 'Delete Project', f"Are you sure you want to delete this project?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.current_project_id in self.projects:
                del self.projects[self.current_project_id]
                self.save_projects()
                self.refresh_dashboard()
                self.stacked_widget.setCurrentIndex(0)

    def open_project_hub(self, pid):
        self.current_project_id = pid
        pdata = self.projects[pid]
        
        self.hub_title.setText(pdata["name"])
        self.hub_desc.setText(pdata["goal"])
        self.inst_box.setText(pdata.get("instructions", ""))
        self.hub_db_viewer.setText(f"> Accessing Database Silo:\n{pdata['name']}")
        
        self.threads_list.clear()
        for tid, tdata in pdata.get("threads", {}).items():
            self.threads_list.addItem(tdata["name"])
            self.threads_list.item(self.threads_list.count()-1).setData(Qt.UserRole, tid)
            
        self.stacked_widget.setCurrentIndex(1)

    def save_instructions(self):
        if self.current_project_id:
            self.projects[self.current_project_id]["instructions"] = self.inst_box.toPlainText()
            self.save_projects()

    def start_new_thread(self):
        user_text = self.new_chat_input.text().strip()
        if not user_text: return
        
        tid = str(uuid.uuid4())
        tname = user_text[:30] + "..." if len(user_text) > 30 else user_text
        
        self.projects[self.current_project_id]["threads"][tid] = {"name": tname, "messages": []}
        self.save_projects()
        
        self.new_chat_input.clear()
        self.load_chat_screen(tid, initial_prompt=user_text)

    def open_thread(self, item):
        tid = item.data(Qt.UserRole)
        self.load_chat_screen(tid)

    def build_chat_screen(self):
        self.chat_widget = QWidget()
        layout = QVBoxLayout(self.chat_widget)
        layout.setContentsMargins(40, 20, 40, 20)

        top_layout = QHBoxLayout()
        back_btn = QPushButton("← Back to Project Hub")
        back_btn.setFlat(True)
        back_btn.setStyleSheet("color: #A0A0A0; font-size: 14px; text-align: left;")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.clicked.connect(lambda: self.open_project_hub(self.current_project_id))
        
        self.agent_selector = QComboBox()
        self.agent_selector.addItems(["Auto", "General", "Coding", "Client", "Creative", "Finance", "Automation"])
        self.agent_selector.setStyleSheet("background-color: #2D2D2D; color: #cdd6f4; padding: 5px; border-radius: 6px;")
        
        top_layout.addWidget(back_btn)
        top_layout.addStretch()
        top_layout.addWidget(QLabel("Force Agent:"))
        top_layout.addWidget(self.agent_selector)
        layout.addLayout(top_layout)

        chat_split = QHBoxLayout()

        chat_left = QVBoxLayout()
        self.chat_display = QTextBrowser()
        self.chat_display.setFont(QFont("Segoe UI", 11))
        self.chat_display.setStyleSheet("background-color: transparent; border: none;")
        chat_left.addWidget(self.chat_display)
        
        self.feedback_container = QHBoxLayout()
        self.feedback_label = QLabel("Was this helpful?")
        self.feedback_label.setStyleSheet("color: #A0A0A0; font-size: 12px;")
        self.btn_up = QPushButton("👍")
        self.btn_up.setStyleSheet("background: none; border: none; color: #a6e3a1; font-size: 16px;")
        self.btn_down = QPushButton("👎")
        self.btn_down.setStyleSheet("background: none; border: none; color: #f38ba8; font-size: 16px;")
        self.btn_up.clicked.connect(lambda: self.submit_feedback("up"))
        self.btn_down.clicked.connect(lambda: self.submit_feedback("down"))
        self.feedback_container.addWidget(self.feedback_label)
        self.feedback_container.addWidget(self.btn_up)
        self.feedback_container.addWidget(self.btn_down)
        self.feedback_container.addStretch()
        self.feedback_container.setVisible(False)
        chat_left.addLayout(self.feedback_container)

        input_container = QFrame()
        input_container.setStyleSheet("background-color: #2D2D2D; border: 1px solid #3E3E3E; border-radius: 12px; padding: 5px;")
        inp_layout = QHBoxLayout(input_container)
        self.chat_input_field = QLineEdit()
        self.chat_input_field.setPlaceholderText("Reply...")
        self.chat_input_field.setStyleSheet("background-color: transparent; border: none; font-size: 14px;")
        self.chat_input_field.returnPressed.connect(self.send_chat_message)
        inp_layout.addWidget(self.chat_input_field)
        chat_left.addWidget(input_container)

        chat_right = QVBoxLayout()
        chat_right.setContentsMargins(20, 0, 0, 0)
        
        db_label_chat = QLabel("Live Database View")
        db_label_chat.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        self.chat_db_viewer = QTextBrowser()
        self.chat_db_viewer.setFont(QFont("Consolas", 9))
        self.chat_db_viewer.setStyleSheet("background-color: #11111b; border: 1px solid #313244; border-radius: 8px; padding: 10px; color: #f38ba8;")
        
        chat_right.addWidget(db_label_chat)
        chat_right.addWidget(self.chat_db_viewer)

        chat_split.addLayout(chat_left, stretch=7)
        chat_split.addLayout(chat_right, stretch=3)
        layout.addLayout(chat_split)

        self.stacked_widget.addWidget(self.chat_widget)

    def load_chat_screen(self, tid, initial_prompt=None):
        self.current_thread_id = tid
        self.chat_display.clear()
        self.chat_db_viewer.setText("> Awaiting database query...")
        self.stacked_widget.setCurrentIndex(2)
        
        history = self.projects[self.current_project_id]["threads"][tid]["messages"]
        for msg in history:
            self._render_chat(msg["sender"], msg["text"], msg["color"])
        
        if initial_prompt:
            self.chat_input_field.setText(initial_prompt)
            self.send_chat_message()

    def _render_chat(self, sender, text, color):
        self.chat_display.append(f'<b><span style="color:{color};">{sender}:</span></b><br>{text}<br><br>')
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_chat(self, sender, text, color):
        self._render_chat(sender, text, color)
        self.projects[self.current_project_id]["threads"][self.current_thread_id]["messages"].append({
            "sender": sender,
            "text": text,
            "color": color
        })
        self.save_projects()

    def send_chat_message(self):
        user_text = self.chat_input_field.text().strip()
        if not user_text: return
        
        self.feedback_container.setVisible(False)
        
        self.append_chat("You", user_text, "#E5E3DB")
        
        self.chat_input_field.clear()
        self.chat_input_field.setPlaceholderText("⏳ Shali is typing...")
        self.chat_input_field.setEnabled(False)
        self.chat_db_viewer.setText("> Searching Database...")
        
        inst = self.projects[self.current_project_id]["instructions"]
        forced_agent = self.agent_selector.currentText()
        
        self.worker = AIWorker(self.orchestrator, user_text, self.projects[self.current_project_id]["name"], inst, forced_agent, self.current_thread_id)
        self.worker.finished.connect(self.handle_ai_response)
        self.worker.start()

    def submit_feedback(self, feedback_type):
        last_msg = self.projects[self.current_project_id]["threads"][self.current_thread_id]["messages"][-1] if self.current_thread_id else None
        if last_msg and hasattr(self, 'last_response'):
            from core.memory import store_feedback
            store_feedback(last_msg.get("text", ""), self.last_response.get("text", ""), feedback_type, self.projects[self.current_project_id]["name"])

    def handle_ai_response(self, result):
        self.last_response = result
        self.append_chat("Shali", result["text"].replace('\n', '<br>'), "#fab387")
        
        self.feedback_container.setVisible(True)
        
        if result["memory_pulled"].strip():
            self.chat_db_viewer.setText(f"MEMORY FOUND:\n-------------------\n{result['memory_pulled']}")
        else:
            self.chat_db_viewer.setText("No relevant database entries found.")
            
        self.chat_input_field.setPlaceholderText("Reply...")
        self.chat_input_field.setEnabled(True)
        self.chat_input_field.setFocus()
