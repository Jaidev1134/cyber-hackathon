from flask import Flask, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import glob
from config import TEST_DIR, PID_FILE, INCIDENT_LOG

app = Flask(__name__)
CORS(app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_LOG = os.path.join(BASE_DIR, "demo_run.log")

demo_process = None

@app.route('/')
def index():
    return send_file('dashboard.html')

@app.route('/launch', methods=['POST'])
def launch():
    global demo_process
    
    # Ensure any old log is removed before starting
    if os.path.exists(DEMO_LOG):
        try:
            os.remove(DEMO_LOG)
        except OSError:
            pass
            
    # We use python executable from the current environment
    import sys
    with open(DEMO_LOG, 'w', encoding='utf-8') as f:
        demo_process = subprocess.Popen(
            [sys.executable, "demo.py"],
            cwd=BASE_DIR,
            stdout=f,
            stderr=subprocess.STDOUT
        )
    return jsonify({'status': 'launched'})

@app.route('/reset', methods=['POST'])
def reset_demo():
    import sys
    subprocess.run([sys.executable, 'reset_env.py'])
    subprocess.run([sys.executable, 'system2_seeder.py'])
    return jsonify({'status': 'reset'})

@app.route('/file/<path:filepath>')
def serve_file(filepath):
    # Ensure safe path traversal
    safe_path = os.path.abspath(os.path.join(TEST_DIR, filepath))
    if not safe_path.startswith(os.path.abspath(TEST_DIR)):
        return "Access denied", 403
    if os.path.exists(safe_path):
        return send_file(safe_path, mimetype='text/plain')
    return "File not found", 404

@app.route('/status')
def status():
    # 1. Determine state
    state = "idle"
    if os.path.exists(INCIDENT_LOG):
        state = "done"
    elif os.path.exists(PID_FILE):
        state = "running"
    elif os.path.exists(DEMO_LOG):
        state = "starting"

    # 2. Get file statuses
    files_state = []
    if os.path.exists(TEST_DIR):
        for root, dirs, files in os.walk(TEST_DIR):
            dirs.sort()  # ensure deterministic sort
            for f in sorted(files):
                # Ignore internal protection/keys just in case, though they shouldn't be here
                if f in ["alert.json", "incident_log.txt", "canary_registry.json", "ransomware.pid", "encryption.key"]:
                    continue
                
                rel_path = os.path.relpath(os.path.join(root, f), TEST_DIR).replace("\\", "/")
                is_locked = f.endswith(".locked")
                display_name = rel_path.replace(".locked", "")
                
                files_state.append({
                    "name": display_name,
                    "status": "encrypted" if is_locked else "safe"
                })

    # Sort files matching the exact directory walk output order
    # (Since we built it sequentially from the sorted os.walk, it's already in perfect order)

    # 3. Read log lines from the live terminal feed
    log_lines = []
    if os.path.exists(DEMO_LOG):
        try:
            with open(DEMO_LOG, 'r', encoding='utf-8') as f:
                log_lines = [line.strip() for line in f.readlines() if line.strip()]
        except Exception:
            pass

    # 4. Read final stats if done
    stats = {
        "latency": 0.0,
        "encrypted": 0,
        "saved": 0,
        "protection_rate": 0.0
    }
    
    if state == "done" and os.path.exists(INCIDENT_LOG):
        try:
            with open(INCIDENT_LOG, 'r', encoding='utf-8') as f:
                content = f.read()
                # Parse the incident log block
                for line in content.split("\n"):
                    if "Latency" in line:
                        val = line.split(":")[1].replace("sec", "").strip()
                        stats["latency"] = float(val)
                    elif "Encrypted Files" in line:
                        stats["encrypted"] = int(line.split(":")[1].strip())
                    elif "Safe Files" in line:
                        stats["saved"] = int(line.split(":")[1].strip())
                    elif "Protection Rate" in line:
                        val = line.split(":")[1].replace("%", "").strip()
                        stats["protection_rate"] = float(val)
        except Exception:
            pass

    return jsonify({
        "state": state,
        "files": files_state,
        "log_lines": log_lines,
        "stats": stats
    })

if __name__ == '__main__':
    app.run(port=5001, debug=False)
