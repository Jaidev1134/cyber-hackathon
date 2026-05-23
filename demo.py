import subprocess
import sys
import os

# Ensure we are in the correct directory regardless of where the script is called from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

print("[DEMO] Starting Ransomware Canary Detection System...")
subprocess.run([sys.executable, "reset_env.py"], check=True)
subprocess.run([sys.executable, "main.py"], check=True)
