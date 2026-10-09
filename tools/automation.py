import os
import json
import datetime
import subprocess

# ==========================================
# 1. SAFE WORKSPACE SETUP
# ==========================================
# Get the folder this file is in (tools/), then go up one level, then into data/workspace
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "data", "workspace"))

# Ensure the directory exists so the system doesn't crash
os.makedirs(BASE_DIR, exist_ok=True)

def safe_path(filename):
    """
    Security feature: Prevents the AI from escaping the workspace.
    Even if it tries to open '../windows/system32', os.path.basename strips it.
    """
    safe_filename = os.path.basename(filename)
    return os.path.join(BASE_DIR, safe_filename)

# ==========================================
# 2. CORE FILE OPERATIONS
# ==========================================
def create_file(filename, content=""):
    path = safe_path(filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: File created at {path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"

def append_file(filename, content):
    path = safe_path(filename)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n" + content)
        return f"Success: Appended to {filename}"
    except Exception as e:
        return f"Error appending to file: {str(e)}"

def read_file(filename):
    path = safe_path(filename)
    if not os.path.exists(path):
        return f"Error: {filename} not found."
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def delete_file(filename):
    path = safe_path(filename)
    if os.path.exists(path):
        os.remove(path)
        return f"Success: Deleted {filename}"
    return f"Error: {filename} not found."

def list_files():
    try:
        files = os.listdir(BASE_DIR)
        if not files:
            return "Workspace is empty."
        return "Files in workspace:\n" + "\n".join(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"

# ==========================================
# 3. SPECIALIZED TOOLS
# ==========================================
def save_note(title, content):
    data = {
        "title": title,
        "content": content,
        "time": str(datetime.datetime.now())
    }
    filename = f"note_{title.replace(' ', '_')}.json"
    path = safe_path(filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return f"Success: Note saved as {filename}"
    except Exception as e:
        return f"Error saving note: {str(e)}"

def run_python_script(filename):
    path = safe_path(filename)
    if not os.path.exists(path):
        return "Error: Script not found."
    try:
        # Runs the script using standard Python and captures the output
        result = subprocess.run(
            ["python", path], 
            capture_output=True, 
            text=True,
            timeout=15 # Prevents infinite loops
        )
        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"
        return output if output.strip() else "Script executed successfully with no output."
    except subprocess.TimeoutExpired:
        return "Error: Script took too long to run and was stopped."
    except Exception as e:
        return f"System error running script: {str(e)}"

# ==========================================
# 4. AUTOMATION ROUTER (ENTRY POINT)
# ==========================================
def run_task(task_command, filename="output.txt", content=""):
    """
    The orchestrator calls this function to execute a specific tool.
    """
    cmd = task_command.lower()

    if "create" in cmd or "write" in cmd or "make" in cmd:
        return create_file(filename, content)
    
    elif "append" in cmd:
        return append_file(filename, content)
    
    elif "read" in cmd:
        return read_file(filename)
    
    elif "delete" in cmd:
        return delete_file(filename)
    
    elif "list" in cmd:
        return list_files()
    
    elif "save note" in cmd:
        return save_note(filename, content)  # filename acts as title here
    
    elif "run script" in cmd:
        return run_python_script(filename)
    
    else:
        return f"Error: Automation command '{task_command}' not recognized."
