# ==========================================
# SHALI - God-Control Architecture UI
# ==========================================
import sys
import os

# Ensure Python 3.11 is used
if sys.version_info >= (3, 12):
    print("WARNING: Using Python 3.11 is recommended. Current:", sys.version)

from core.orchestrator import Orchestrator
from project_isolation.manager import ProjectManager
from ui.app import ShaliApp


def boot_system():
    print("[SHALI] Booting God-Control Architecture UI...")
    
    # 1. Initialize safe directories
    os.makedirs(os.path.abspath("./data/workspace"), exist_ok=True)
    os.makedirs(os.path.abspath("./data/logs"), exist_ok=True)
    os.makedirs(os.path.abspath("./data/chroma_db"), exist_ok=True)
    
    # 2. Initialize project manager
    try:
        project_mgr = ProjectManager()
        print("[SHALI] Project Manager Online.")
    except Exception as e:
        print(f"[FATAL ERROR] Project Manager failed to initialize:\n{e}")
        sys.exit(1)
    
    # 3. Boot the core brain
    try:
        brain = Orchestrator()
        print("[SHALI] Core Orchestrator Online.")
    except Exception as e:
        print(f"[FATAL ERROR] Orchestrator failed to initialize:\n{e}")
        sys.exit(1)
    
    return brain, project_mgr


def main():
    brain, project_mgr = boot_system()
    
    # Launch the God-Control TUI
    app = ShaliApp(orchestrator=brain)
    app.run()


if __name__ == "__main__":
    main()
