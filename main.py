import subprocess
import time
import os
import sys
from config import PID_FILE, INCIDENT_LOG

def main():
    print("[MAIN] Resetting environment...")
    subprocess.run([sys.executable, "reset_env.py"], check=True)
    
    # We use system2_seeder.py instead of setup_env.py
    print("[MAIN] Seeding canary files...")
    subprocess.run([sys.executable, "system2_seeder.py"], check=True)

    print("[MAIN] Starting watchdog monitor...")
    
    # Remove old ready file if exists
    if os.path.exists("canary.ready"):
        os.remove("canary.ready")
        
    # We need to explicitly pass the canary_registry.json since it's not a default name
    watchdog = subprocess.Popen(
        [sys.executable, "canary_monitor.py", "--manifest", "test_env/canary_registry.json"]
    )

    # Wait for ready signal via file
    while not os.path.exists("canary.ready"):
        time.sleep(0.1)

    print("[MAIN] Monitor is armed. Launching ransomware...")
    ransomware = subprocess.Popen(
        [sys.executable, "ransomware_sim.py", "--delay", "20"]
    )

    # Wait for ransomware to be killed or finish
    ransomware.wait()

    # Count saved vs encrypted files
    from config import TEST_DIR
    import glob
    locked = glob.glob(os.path.join(TEST_DIR, "**", "*.locked"), recursive=True)
    total  = glob.glob(os.path.join(TEST_DIR, "**", "*"), recursive=True)
    total  = [f for f in total if os.path.isfile(f)]
    
    files_encrypted = len(locked)
    files_saved = len(total) - len(locked)
    protection_rate = (files_saved / len(total) * 100) if total else 100.0

    print("\n" + "="*50)
    print("        INCIDENT REPORT")
    print("="*50)
    if os.path.exists(INCIDENT_LOG):
        # We don't print the whole incident log as it contains multiple runs now
        pass
    print(f"  Files Encrypted   : {files_encrypted}")
    print(f"  Files Saved       : {files_saved}")
    print(f"  Protection Rate   : {protection_rate:.1f}%")
    print("="*50)

    # Cleanup background processes
    watchdog.terminate()

if __name__ == "__main__":
    main()
