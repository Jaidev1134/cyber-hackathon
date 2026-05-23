import os
import glob
from config import TEST_DIR, PID_FILE, KEY_FILE, ALERT_FILE, INCIDENT_LOG

def reset_environment():
    # Remove all locked files
    locked_files = glob.glob(f"{TEST_DIR}/**/*.locked", recursive=True)
    for f in locked_files:
        try:
            os.remove(f)
        except OSError:
            pass

    # Remove PID, KEY, and alert files
    demo_log = os.path.join(os.path.dirname(TEST_DIR), "..", "demo_run.log")
    for f in [PID_FILE, KEY_FILE, ALERT_FILE, INCIDENT_LOG, demo_log]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass

    # Remove all ransom notes
    ransom_notes = glob.glob(f"{TEST_DIR}/**/README_DECRYPT.txt", recursive=True)
    for f in ransom_notes:
        try:
            os.remove(f)
        except OSError:
            pass

    # after deleting everything, verify nothing slipped through
    remaining = glob.glob(f"{TEST_DIR}/**/*.locked", recursive=True)
    if remaining:
        print(f"[RESET WARNING] {len(remaining)} .locked files could not be deleted:")
        for f in remaining:
            print(f"  {f}")
        print("[RESET] Key was still deleted — remaining files are unrecoverable.")
    else:
        print("[RESET] Clean. All .locked files removed.")

if __name__ == "__main__":
    reset_environment()
