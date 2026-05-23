# Ransomware Canary Detection — Integration Protocol

**Role:** Final Integrator  
**Objective:** Verify each component independently, wire them together via `main.py`, and validate the full end-to-end demo.

---

## PART 1 — Individual Component Verification

Before touching integration, verify each teammate's component in isolation. Do NOT run everything together yet.

---

### Person 1 — `ransomware_sim.py` (Ransomware Simulator)

**Already verified and production-ready per project context. Run a quick sanity check anyway.**

#### Checklist

```bash
# 1. Run the test suite
python -m pytest test_ransomware.py -v
# Expected: 7/7 PASSED

# 2. Run the simulator manually with a delay
python ransomware_sim.py --delay 300

# 3. Verify PID file was created
cat test_env/ransomware.pid

# 4. Verify files are being renamed to .locked
ls test_env/files/

# 5. Verify clean exit — send SIGTERM manually
kill -SIGTERM $(cat test_env/ransomware.pid)
# Expected output: [RANSOMWARE] Process terminated by defence system.

# 6. Verify PID file was removed after SIGTERM
ls test_env/ransomware.pid   # Should NOT exist
```

#### Pass Criteria
- [ ] 7/7 tests pass
- [ ] `ransomware.pid` created on launch
- [ ] Files get `.locked` extension
- [ ] Process exits cleanly on SIGTERM
- [ ] PID file removed after SIGTERM
- [ ] Reset works: `python reset_env.py` removes all `.locked` files

---

### Person 2 — Canary Seeder / File Setup

**What this component must deliver:**
- Place canary files in `test_env/files/` with predictable, early-in-sort-order names (e.g. `00_canary_alpha.txt`)
- Write `test_env/canary_registry.json` listing canary file paths

#### Checklist

```bash
# 1. Run Person 2's seeder script
python canary_seeder.py   # (or whatever they named it)

# 2. Verify canary files exist in the files directory
ls test_env/files/ | grep canary
# Expected: at least one file like 00_canary_alpha.txt

# 3. Verify the registry was written
cat test_env/canary_registry.json
```

#### Expected `canary_registry.json` format
```json
{
  "canaries": [
    "C:/absolute/path/to/test_env/files/00_canary_alpha.txt"
  ]
}
```

> **Critical:** Paths in `canary_registry.json` must be **absolute paths**, not relative. If they are relative, flag this immediately — the watchdog daemon (Person 3) depends on this file.

#### Pass Criteria
- [ ] Canary files physically exist in `test_env/files/`
- [ ] File names sort before regular files (prefix `00_` or similar)
- [ ] `canary_registry.json` exists and is valid JSON
- [ ] All paths in registry are absolute
- [ ] Running seeder twice does not crash or duplicate entries

---

### Person 3 — Watchdog Monitor Daemon

**What this component must deliver:**
- Monitor `test_env/files/` for filesystem events
- Detect when a canary file is accessed or modified
- Write `test_env/alert.json` immediately upon canary hit
- Must react within ~2 seconds

#### Checklist

```bash
# Terminal 1 — Start the watchdog
python watchdog_monitor.py   # (or their script name)

# Terminal 2 — Simulate a canary touch manually
touch test_env/files/00_canary_alpha.txt   # Linux/Mac
# On Windows:
python -c "open('test_env/files/00_canary_alpha.txt', 'a').close()"

# Back in Terminal 1 — Verify detection was logged
# Expected output: something like [ALERT] Canary touched: 00_canary_alpha.txt

# Check alert file was written
cat test_env/alert.json
```

#### Expected `alert.json` format
```json
{
  "canary_hit": true,
  "file": "C:/absolute/path/to/test_env/files/00_canary_alpha.txt",
  "pid_file": "C:/absolute/path/to/test_env/ransomware.pid",
  "timestamp": "2025-01-01T00:00:00"
}
```

> **Critical:** The `pid_file` field must point to the correct PID file location so Person 4's kill engine can find it.

#### Pass Criteria
- [ ] Daemon starts without errors
- [ ] Manual canary touch triggers console alert
- [ ] `alert.json` is written within 2 seconds of touch
- [ ] `alert.json` is valid JSON with correct structure
- [ ] No crash on non-canary file events
- [ ] Daemon reads `canary_registry.json` (not hardcoded paths)

---

### Person 4 — Kill Engine + Alert System

**What this component must deliver:**
- Watch for `alert.json` to appear or update
- Read PID from `test_env/ransomware.pid`
- Send SIGTERM to that PID
- Log incident to `test_env/incident_log.txt`

#### Checklist

```bash
# Terminal 1 — Start a dummy process and note its PID
python -c "import time; open('test_env/ransomware.pid','w').write(str(__import__('os').getpid())); time.sleep(60)"

# Note the PID printed, then manually write alert.json
python -c "
import json
with open('test_env/alert.json', 'w') as f:
    json.dump({'canary_hit': True, 'pid_file': 'test_env/ransomware.pid'}, f)
"

# Terminal 2 — Start the kill engine
python kill_engine.py   # (or their script name)

# Expected: kill engine reads alert.json, sends SIGTERM to the dummy PID
# Dummy process in Terminal 1 should exit

# Verify incident log was written
cat test_env/incident_log.txt
```

#### Pass Criteria
- [ ] Kill engine detects `alert.json` creation/change
- [ ] Sends SIGTERM (not SIGKILL) to PID
- [ ] Target process exits
- [ ] Incident log is written with timestamp and PID
- [ ] No crash if PID file doesn't exist (graceful error handling)
- [ ] No crash if alert.json is malformed

---

## PART 2 — Integration

Once all 4 components pass their individual checks, wire them together.

### Step 1 — Verify `config.py` is the single source of truth

Open `config.py` and confirm ALL of the following paths are defined there using `os.path.abspath`:

```python
import os
_BASE = os.path.dirname(os.path.abspath(__file__))

TEST_DIR           = os.path.join(_BASE, "test_env", "files")
PID_FILE           = os.path.join(_BASE, "test_env", "ransomware.pid")
CANARY_REGISTRY    = os.path.join(_BASE, "test_env", "canary_registry.json")
ALERT_FILE         = os.path.join(_BASE, "test_env", "alert.json")
INCIDENT_LOG       = os.path.join(_BASE, "test_env", "incident_log.txt")
ENCRYPTION_KEY     = os.path.join(_BASE, "test_env", "encryption.key")
```

> If any teammate has hardcoded paths in their script, replace them with the `config.py` constant before proceeding.

---

### Step 2 — Write `main.py`

`main.py` must:
1. Call `setup_env.py` / `reset_env.py` to prepare a clean environment
2. Seed canary files (Person 2)
3. Launch the watchdog daemon as a subprocess (Person 3)
4. Launch the kill engine as a subprocess (Person 4)
5. Launch the ransomware simulator as a subprocess with delay (Person 1)
6. Wait for termination and print outcome

#### Suggested `main.py` structure

```python
import subprocess
import time
import os
import sys
from config import PID_FILE, INCIDENT_LOG

def main():
    print("[MAIN] Resetting environment...")
    subprocess.run([sys.executable, "reset_env.py"], check=True)
    subprocess.run([sys.executable, "setup_env.py"], check=True)

    print("[MAIN] Seeding canary files...")
    subprocess.run([sys.executable, "canary_seeder.py"], check=True)

    print("[MAIN] Starting watchdog monitor...")
    watchdog = subprocess.Popen([sys.executable, "watchdog_monitor.py"])

    print("[MAIN] Starting kill engine...")
    kill_engine = subprocess.Popen([sys.executable, "kill_engine.py"])

    # Small delay to let daemons initialize before attacker starts
    time.sleep(1)

    print("[MAIN] Launching ransomware simulator...")
    ransomware = subprocess.Popen(
        [sys.executable, "ransomware_sim.py", "--delay", "300"]
    )

    # Wait for ransomware to be killed or finish
    ransomware.wait()

    print("\n[MAIN] === OUTCOME ===")
    if os.path.exists(INCIDENT_LOG):
        with open(INCIDENT_LOG) as f:
            print(f.read())

    # Count saved vs encrypted files
    from config import TEST_DIR
    import glob
    locked = glob.glob(os.path.join(TEST_DIR, "**", "*.locked"), recursive=True)
    total  = glob.glob(os.path.join(TEST_DIR, "**", "*"), recursive=True)
    total  = [f for f in total if os.path.isfile(f)]
    print(f"[MAIN] Files encrypted : {len(locked)}")
    print(f"[MAIN] Files saved     : {len(total) - len(locked)}")

    # Cleanup background processes
    watchdog.terminate()
    kill_engine.terminate()

if __name__ == "__main__":
    main()
```

---

### Step 3 — Pre-integration checklist

Before running `main.py`, confirm:

- [ ] All 4 components use `config.py` for paths — no hardcoded strings
- [ ] `setup_env.py` creates all required subdirectories
- [ ] `reset_env.py` removes `.locked` files, PID file, and `alert.json`
- [ ] No two scripts write to the same file without coordination
- [ ] `canary_registry.json` is written before watchdog starts
- [ ] Watchdog starts before ransomware simulator

---

## PART 3 — End-to-End Testing

### Test 1 — Happy Path (Full Race)

```bash
python main.py --delay 300
```

**Expected output sequence:**
```
[MAIN] Resetting environment...
[MAIN] Seeding canary files...
[MAIN] Starting watchdog monitor...
[MAIN] Starting kill engine...
[MAIN] Launching ransomware simulator...
[RANSOMWARE] Started. PID: XXXX
[RANSOMWARE] Encrypted: 00_canary_alpha.txt -> 00_canary_alpha.txt.locked
[WATCHDOG] CANARY HIT: 00_canary_alpha.txt
[KILL] Sending SIGTERM to PID XXXX
[RANSOMWARE] Process terminated by defence system.
[MAIN] Files encrypted : 1
[MAIN] Files saved     : 5
```

**Pass criteria:**
- [ ] Only 1–2 files encrypted before kill
- [ ] Process exits with clean SIGTERM message
- [ ] PID file removed after kill
- [ ] `incident_log.txt` written with timestamp and PID
- [ ] All 5+ regular files remain unencrypted

---

### Test 2 — Timing Stress Test

Run with faster delay to confirm kill is robust:

```bash
python ransomware_sim.py --delay 100
```

- [ ] Canary still detected and process killed even at 100ms delay
- [ ] Some files may be encrypted but majority should be saved

---

### Test 3 — Clean Reset and Rerun

```bash
python reset_env.py
python main.py --delay 300
```

- [ ] No stale `.locked` files from previous run
- [ ] No stale PID from previous run
- [ ] Full cycle works cleanly on second run
- [ ] Idempotent — can run 3 times in a row without manual cleanup

---

### Test 4 — Subprocess Isolation Test

Run from a *different* directory to confirm no relative path bugs remain:

```bash
cd ..
python cyber_hackathon/main.py --delay 300
```

- [ ] All paths resolve correctly
- [ ] No `FileNotFoundError` from any component

---

### Test 5 — Kill Latency Measurement

Add timing instrumentation to measure detection-to-kill latency:

```python
# In watchdog_monitor.py — log timestamp when canary hit detected
import datetime
print(f"[WATCHDOG] Hit at: {datetime.datetime.now().isoformat()}")

# In ransomware_sim.py — log timestamp when SIGTERM received
import datetime
print(f"[RANSOMWARE] Killed at: {datetime.datetime.now().isoformat()}")
```

**Target:** Kill latency < 2 seconds from canary touch.

---

## PART 4 — Demo Preparation

### Final pre-demo checklist

- [ ] All 7 Person 1 unit tests pass
- [ ] All 4 individual component checks pass
- [ ] `main.py` runs end-to-end cleanly 3 times in a row
- [ ] Kill latency is under 2 seconds
- [ ] Windows Defender exclusion added for project folder (if on Windows)
- [ ] Demo runs from correct working directory
- [ ] Reset has been run immediately before the demo dry-run

### Demo run order

```
1. python reset_env.py          # Clean slate
2. python setup_env.py          # Create test files
3. python main.py --delay 300   # Full demo
```

### Talking points during demo

| Moment | What to say |
|--------|-------------|
| Simulator starts | "This simulates a ransomware process encrypting files with AES." |
| First `.locked` file | "The first file it touches is our canary — a decoy placed early in the directory." |
| Watchdog alert | "Our inotify/watchdog daemon detects the access in real time." |
| Kill signal | "We send SIGTERM to the PID — the process is terminated cleanly." |
| Saved files count | "Only 1 file was encrypted. All others were saved." |

---

## Integration Risk Register

| Risk | Likelihood | Fix |
|------|-----------|-----|
| Relative paths in teammate code | High | Enforce `config.py` import before integration |
| Watchdog starts after ransomware | Medium | Add `time.sleep(1)` before launching simulator |
| `alert.json` format mismatch | Medium | Agree on schema and validate in Person 4's code |
| Windows SIGTERM not handled | Low | Already fixed in Person 1; verify Person 4 uses `os.kill` correctly |
| Canary name doesn't sort first | Medium | Confirm `00_` prefix or equivalent in Person 2's output |
| PID file stale from crashed run | Low | `reset_env.py` must delete it; verify this |
