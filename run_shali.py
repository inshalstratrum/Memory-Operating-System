import subprocess
import sys
import os
import shutil

# Change to the correct directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Prefer current python or find py / python3.11 / python launcher
python_exe = sys.executable
if sys.version_info < (3, 10):
    python_exe = shutil.which("py") or shutil.which("python3.11") or shutil.which("python") or sys.executable

sys.exit(subprocess.call([python_exe, "main.py"] + sys.argv[1:]))