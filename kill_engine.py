"""
kill_engine.py
==============
Ransomware Defense Kill Engine — Hackathon EDR/XDR Response Module

Triggered by a watchdog daemon when canary file access is detected.
Immediately terminates the ransomware process, measures detection latency,
scans the environment for damage, logs incident data, and renders a
cinematic terminal alert suite.

Author  : Ransomware Defense Hackathon Team
License : MIT
Python  : 3.8+
"""

# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Force UTF-8 encoding for stdout on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

import psutil
from colorama import Fore, Style, init as colorama_init

# ─────────────────────────────────────────────────────────────────────────────
# Colorama bootstrap  (autoreset keeps every print clean)
# ─────────────────────────────────────────────────────────────────────────────
colorama_init(autoreset=True)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration / Constants
# ─────────────────────────────────────────────────────────────────────────────
from config import (
    TEST_DIR,
    PID_FILE,
    ALERT_FILE,
    INCIDENT_LOG,
)

SCAN_DIR = Path(TEST_DIR)
PID_FILE = Path(PID_FILE)
ALERT_FILE = Path(ALERT_FILE)
INCIDENT_LOG = Path(INCIDENT_LOG)
ENCRYPTED_EXT = ".locked"
# Files that should never be counted as ransomware targets
PROTECTED_FILES = {
    "alert.json",
    "incident_log.txt",
    "canary_registry.json",
    "ransomware.pid",
    "kill_engine.py",
    "README_DECRYPT.txt",
    "encryption.key",
}

# Severity thresholds (fraction of files encrypted)
SEV_HIGH        = 0.10   # ≥ 10 % encrypted → HIGH
SEV_MEDIUM      = 0.03   # ≥  3 % encrypted → MEDIUM
# below that         → LOW

SEPARATOR       = "=" * 60
THIN_SEP        = "─" * 60


# ─────────────────────────────────────────────────────────────────────────────
# ASCII Banner
# ─────────────────────────────────────────────────────────────────────────────
BANNER = r"""
██████╗  ██████╗ ██████╗
██╔══██╗██╔═══██╗██╔══██╗
██████╔╝██║   ██║██████╔╝
██╔══██╗██║   ██║██╔═══╝
██║  ██║╚██████╔╝██║
╚═╝  ╚═╝ ╚═════╝ ╚═╝
   R A N S O M W A R E   D E F E N S E   E N G I N E
"""


# ─────────────────────────────────────────────────────────────────────────────
# Low-level print helpers
# ─────────────────────────────────────────────────────────────────────────────

def _tag(color: str, label: str, message: str) -> None:
    """Print a coloured tag line: [LABEL] message."""
    print(f"{color}[{label}]{Style.RESET_ALL} {message}")


def info(msg: str)    -> None: _tag(Fore.CYAN,    "INFO",    msg)
def success(msg: str) -> None: _tag(Fore.GREEN,   "SUCCESS", msg)
def warn(msg: str)    -> None: _tag(Fore.YELLOW,  "WARNING", msg)
def error(msg: str)   -> None: _tag(Fore.RED,     "ERROR",   msg)
def action(msg: str)  -> None: _tag(Fore.MAGENTA, "ACTION",  msg)


def banner(title: str, color: str = Fore.RED) -> None:
    """Print a full-width coloured section banner."""
    print(f"\n{color}{SEPARATOR}")
    print(f" {title}")
    print(f"{SEPARATOR}{Style.RESET_ALL}")


def thin_sep() -> None:
    print(Fore.WHITE + THIN_SEP + Style.RESET_ALL)


# ─────────────────────────────────────────────────────────────────────────────
# I/O Helpers
# ─────────────────────────────────────────────────────────────────────────────

def read_pid() -> int | None:
    """
    Read the ransomware PID from PID_FILE.

    Returns the integer PID, or None on any failure.
    """
    if not PID_FILE.exists():
        error(f"PID file not found: {PID_FILE}")
        return None
    try:
        raw = PID_FILE.read_text().strip()
        pid = int(raw)
        return pid
    except ValueError:
        error(f"Invalid PID value in {PID_FILE}: '{raw}'")
        return None
    except OSError as exc:
        error(f"Cannot read {PID_FILE}: {exc}")
        return None


def read_alert_timestamp() -> float | None:
    """
    Parse T1 (canary-detection timestamp) from ALERT_FILE.

    Returns a float UNIX timestamp, or None on any failure.
    """
    if not ALERT_FILE.exists():
        warn(f"Alert file not found: {ALERT_FILE}  —  latency unavailable")
        return None
    try:
        data = json.loads(ALERT_FILE.read_text())
        t1 = float(data["T1"])
        return t1
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        warn(f"Malformed {ALERT_FILE}: {exc}  —  latency unavailable")
        return None
    except OSError as exc:
        warn(f"Cannot read {ALERT_FILE}: {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Process Control
# ─────────────────────────────────────────────────────────────────────────────

def validate_process(pid: int) -> psutil.Process | None:
    """
    Confirm that *pid* belongs to a living process.

    Returns a psutil.Process object, or None if the process does not exist
    or is inaccessible.
    """
    try:
        proc = psutil.Process(pid)
        if not proc.is_running():
            warn(f"PID {pid} exists but is no longer running.")
            return None
        return proc
    except psutil.NoSuchProcess:
        warn(f"PID {pid} does not exist — process may have already exited.")
        return None
    except psutil.AccessDenied:
        error(f"Access denied when inspecting PID {pid}.")
        return None


def kill_process(proc: psutil.Process) -> bool:
    """
    Attempt to terminate *proc* gracefully with SIGTERM.
    Wait up to 3 seconds. If it ignores the signal, escalate to SIGKILL.

    Returns True on success, False otherwise.
    """
    pid = proc.pid
    try:
        action(f"Sending SIGTERM to PID {pid} …")
        proc.terminate()
        try:
            proc.wait(timeout=3)
            return True
        except psutil.TimeoutExpired:
            warn(f"Process {pid} did not exit gracefully within 3 seconds. Escalating to SIGKILL.")
            proc.kill()
            proc.wait(timeout=1)
            return True
    except psutil.NoSuchProcess:
        # Already dead — counts as a win.
        return True
    except psutil.AccessDenied:
        error(f"Permission denied — cannot kill PID {pid}.")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# File-System Scanning Engine
# ─────────────────────────────────────────────────────────────────────────────

def scan_environment(root: Path) -> dict:
    """
    Recursively walk *root* and tally encrypted vs. safe files.

    Rules
    -----
    - Files ending with ENCRYPTED_EXT (.locked) → encrypted
    - All other non-hidden files                → safe
    - Hidden files (name starts with '.')       → ignored

    Returns
    -------
    dict with keys: encrypted, safe, total, encrypted_paths
    """
    encrypted_paths: list[str] = []
    safe_count      = 0

    if not root.exists():
        warn(f"Scan directory not found: {root}")
        return {"encrypted": 0, "safe": 0, "total": 0, "encrypted_paths": []}

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden directories in-place
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for fname in filenames:
            if fname.startswith("."):
                continue                          # ignore hidden files
            if fname in PROTECTED_FILES:
                continue                          # ignore protected files
            fpath = os.path.join(dirpath, fname)
            if fname.endswith(ENCRYPTED_EXT):
                encrypted_paths.append(fpath)
            else:
                safe_count += 1

    encrypted_count = len(encrypted_paths)
    total           = encrypted_count + safe_count

    return {
        "encrypted":       encrypted_count,
        "safe":            safe_count,
        "total":           total,
        "encrypted_paths": encrypted_paths,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Threat Severity & Status Helpers
# ─────────────────────────────────────────────────────────────────────────────

def classify_severity(encrypted: int, total: int) -> str:
    """Return a human-readable severity label based on encryption ratio."""
    if total == 0:
        return "UNKNOWN"
    ratio = encrypted / total
    if ratio >= SEV_HIGH:
        return "HIGH"
    if ratio >= SEV_MEDIUM:
        return "MEDIUM"
    return "LOW"


def classify_status(kill_ok: bool, encrypted: int) -> str:
    """
    Derive containment status from kill success and damage observed.

    CONTAINED         — process killed, zero files encrypted
    PARTIAL CONTAINMENT — process killed, some files encrypted
    FAILED            — process could not be killed
    """
    if not kill_ok:
        return "FAILED"
    if encrypted == 0:
        return "CONTAINED"
    return "PARTIAL CONTAINMENT"


def severity_color(severity: str) -> str:
    """Map severity string to a colorama colour code."""
    return {
        "HIGH":    Fore.RED,
        "MEDIUM":  Fore.YELLOW,
        "LOW":     Fore.GREEN,
        "UNKNOWN": Fore.WHITE,
    }.get(severity, Fore.WHITE)


def status_color(status: str) -> str:
    """Map status string to a colorama colour code."""
    return {
        "CONTAINED":            Fore.GREEN,
        "PARTIAL CONTAINMENT":  Fore.YELLOW,
        "FAILED":               Fore.RED,
    }.get(status, Fore.WHITE)


# ─────────────────────────────────────────────────────────────────────────────
# Terminal Display Engine
# ─────────────────────────────────────────────────────────────────────────────

def display_ascii_banner() -> None:
    """Print the startup ASCII-art security banner."""
    print(Fore.CYAN + BANNER + Style.RESET_ALL)


def display_alert_header(pid: int) -> None:
    """Print the dramatic RANSOMWARE DETECTED header block."""
    banner("⚠  RANSOMWARE DETECTED  ⚠", color=Fore.RED)
    print('\a')   # terminal bell — audible alert on supported terminals
    info("Canary file access confirmed by watchdog daemon.")
    info(f"Malicious process identified — PID: {Fore.RED}{pid}{Style.RESET_ALL}")


def display_incident_report(
    pid       : int,
    latency   : float | None,
    scan_data : dict,
    status    : str,
    severity  : str,
    success_pct: float,
) -> None:
    """Render the full incident report block to stdout."""
    banner("INCIDENT REPORT", color=Fore.CYAN)

    lat_str = f"{latency:.4f} sec" if latency is not None else "N/A"
    sev_col = severity_color(severity)
    sta_col = status_color(status)

    col_w = 22   # label column width

    print(f"  {'Detection latency':<{col_w}}: {Fore.CYAN}{lat_str}{Style.RESET_ALL}")
    print(f"  {'Encrypted files':<{col_w}}: {Fore.RED}{scan_data['encrypted']}{Style.RESET_ALL}")
    print(f"  {'Protected files':<{col_w}}: {Fore.GREEN}{scan_data['safe']}{Style.RESET_ALL}")
    print(f"  {'Total files scanned':<{col_w}}: {scan_data['total']}")
    print(f"  {'Protection rate':<{col_w}}: {Fore.GREEN}{success_pct:.1f}%{Style.RESET_ALL}")
    print(f"  {'Threat severity':<{col_w}}: {sev_col}{severity}{Style.RESET_ALL}")
    print(f"  {'Threat status':<{col_w}}: {sta_col}{status}{Style.RESET_ALL}")
    print(f"  {'PID terminated':<{col_w}}: {pid}")

    if scan_data["encrypted_paths"]:
        thin_sep()
        print(f"  {Fore.RED}Encrypted file paths:{Style.RESET_ALL}")
        for p in scan_data["encrypted_paths"]:
            print(f"    {Fore.RED}✗  {p}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}{SEPARATOR}{Style.RESET_ALL}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Incident Logging
# ─────────────────────────────────────────────────────────────────────────────

def write_incident_log(
    pid         : int,
    latency     : float | None,
    scan_data   : dict,
    status      : str,
    severity    : str,
    success_pct : float,
) -> None:
    """
    Append a human-readable incident record to INCIDENT_LOG.

    Each run adds a timestamped block; the file grows over time so that
    multiple demo runs are preserved.
    """
    ts      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lat_str = f"{latency:.4f} sec" if latency is not None else "N/A"

    record = (
        f"[{ts}]\n"
        f"  PID Killed       : {pid}\n"
        f"  Latency          : {lat_str}\n"
        f"  Encrypted Files  : {scan_data['encrypted']}\n"
        f"  Safe Files       : {scan_data['safe']}\n"
        f"  Total Files      : {scan_data['total']}\n"
        f"  Protection Rate  : {success_pct:.1f}%\n"
        f"  Threat Severity  : {severity}\n"
        f"  Status           : {status}\n"
        f"{'─' * 40}\n"
    )

    try:
        with INCIDENT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(record)
        success(f"Incident logged → {INCIDENT_LOG}")
    except OSError as exc:
        warn(f"Could not write incident log: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Kill-Engine Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def trigger_kill() -> dict:
    """
    Primary entry point invoked by the watchdog daemon (or directly).

    Execution flow
    ──────────────
    1. Display ASCII banner
    2. Read PID from ransomware.pid
    3. Read T1 from alert.json
    4. Validate process existence
    5. Display alert header
    6. Capture T2 and kill process
    7. Calculate latency (T2 − T1)
    8. Scan test_env/ for damage assessment
    9. Compute severity / status / protection rate
    10. Display incident report
    11. Write to incident_log.txt

    Returns
    -------
    dict summarising the incident (useful when called programmatically).
    """
    # ── Startup ────────────────────────────────────────────────────────────
    display_ascii_banner()

    # ── Step 1 · Read PID ──────────────────────────────────────────────────
    pid = read_pid()
    if pid is None:
        error("Cannot proceed without a valid PID.  Aborting kill engine.")
        sys.exit(1)

    # ── Step 2 · Read canary-detection timestamp ────────────────────────────
    t1 = read_alert_timestamp()

    # ── Step 3 · Validate process ───────────────────────────────────────────
    proc = validate_process(pid)

    # ── Step 4 · Alert header ───────────────────────────────────────────────
    display_alert_header(pid)

    # ── Step 5 · Kill  (T2 captured immediately before the kill call) ───────
    t2      = time.time()
    kill_ok = False

    if proc is not None:
        kill_ok = kill_process(proc)
        if kill_ok:
            success(f"Process {pid} terminated successfully.")
        else:
            error(f"Failed to terminate process {pid}.")
    else:
        warn("Target process was not running — assuming prior termination.")
        kill_ok = True   # nothing to kill → treat as contained

    # ── Step 6 · Latency calculation ────────────────────────────────────────
    latency = (t2 - t1) if t1 is not None else None
    if latency is not None:
        info(f"Detection latency: {Fore.CYAN}{latency:.4f} sec{Style.RESET_ALL}")
    else:
        warn("Detection latency unavailable (T1 not loaded).")

    # ── Step 7 · Scan environment ───────────────────────────────────────────
    action(f"Scanning {SCAN_DIR} for file-system damage …")
    scan_data = scan_environment(SCAN_DIR)
    info(
        f"Scan complete — "
        f"{Fore.RED}{scan_data['encrypted']} encrypted{Style.RESET_ALL}, "
        f"{Fore.GREEN}{scan_data['safe']} safe{Style.RESET_ALL} "
        f"({scan_data['total']} total)"
    )

    # ── Step 8 · Derived metrics ────────────────────────────────────────────
    total        = scan_data["total"]
    success_pct  = (scan_data["safe"] / total * 100) if total > 0 else 100.0
    severity     = classify_severity(scan_data["encrypted"], total)
    status       = classify_status(kill_ok, scan_data["encrypted"])

    # ── Step 9 · Incident report ────────────────────────────────────────────
    display_incident_report(
        pid         = pid,
        latency     = latency,
        scan_data   = scan_data,
        status      = status,
        severity    = severity,
        success_pct = success_pct,
    )

    # ── Step 10 · Persist incident log ─────────────────────────────────────
    write_incident_log(
        pid         = pid,
        latency     = latency,
        scan_data   = scan_data,
        status      = status,
        severity    = severity,
        success_pct = success_pct,
    )

    # ── Return structured result for programmatic callers ──────────────────
    return {
        "pid":            pid,
        "killed":         kill_ok,
        "latency_sec":    latency,
        "encrypted":      scan_data["encrypted"],
        "safe":           scan_data["safe"],
        "total":          scan_data["total"],
        "protection_pct": success_pct,
        "severity":       severity,
        "status":         status,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    trigger_kill()