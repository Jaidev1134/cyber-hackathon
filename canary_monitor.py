"""Watchdog-based canary file monitor.

System 3 owns this module. It detects suspicious access or mutation of known
canary files and emits structured alert JSON for the kill/alert/recovery layer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import signal
import socket
import sys
import time
from kill_engine import trigger_kill
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    import psutil
except ImportError:  # pragma: no cover - handled at runtime for friendlier CLI.
    psutil = None  # type: ignore[assignment]

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:  # pragma: no cover - handled at runtime for friendlier CLI.
    FileSystemEvent = object  # type: ignore[misc,assignment]
    FileSystemEventHandler = object  # type: ignore[misc,assignment]
    Observer = None  # type: ignore[assignment]


LOGGER = logging.getLogger("canary-monitor")
DEFAULT_MANIFESTS = (
    "canary_config.json",
    "canaries.json",
    "canary_manifest.json",
    "config/canaries.json",
    "configs/canaries.json",
)
MANIFEST_KEYS = ("canary_paths", "canary_files", "files", "paths", "canaries")


@dataclass(frozen=True)
class MonitorConfig:
    canary_paths: tuple[Path, ...]
    canary_metadata: dict[Path, dict[str, Any]]
    alert_dir: Path
    debounce_seconds: float
    heartbeat_seconds: float
    process_scan_timeout_seconds: float
    stdout_alerts: bool


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def resolve_path(path: str | Path, base_dir: Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def sha256_of_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def load_manifest(manifest_path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {str(item): {} for item in data}

    if not isinstance(data, dict):
        raise ValueError(f"{manifest_path} must contain a JSON list or object")

    system2_canaries = data.get("canary_files")
    if isinstance(system2_canaries, dict):
        canaries: dict[str, dict[str, Any]] = {}
        for registry_key, metadata in system2_canaries.items():
            if isinstance(metadata, dict):
                file_path = metadata.get("path") or metadata.get("file") or metadata.get("filepath")
                if file_path:
                    canaries[str(file_path)] = {
                        "registry_key": registry_key,
                        "expected_sha256": metadata.get("sha256"),
                        "source_manifest": str(manifest_path),
                        "target_directory": data.get("target_directory"),
                    }
            elif isinstance(metadata, str):
                canaries[metadata] = {
                    "registry_key": registry_key,
                    "source_manifest": str(manifest_path),
                    "target_directory": data.get("target_directory"),
                }
        if canaries:
            return canaries

    for key in MANIFEST_KEYS:
        value = data.get(key)
        if isinstance(value, list):
            paths: dict[str, dict[str, Any]] = {}
            for item in value:
                if isinstance(item, str):
                    paths[item] = {"source_manifest": str(manifest_path)}
                elif isinstance(item, dict):
                    file_path = item.get("path") or item.get("file") or item.get("filepath")
                    if file_path:
                        paths[str(file_path)] = {
                            "registry_key": item.get("name") or item.get("id"),
                            "expected_sha256": item.get("sha256"),
                            "source_manifest": str(manifest_path),
                        }
            return paths

    raise ValueError(
        f"{manifest_path} does not contain any supported key: {', '.join(MANIFEST_KEYS)}"
    )


def find_default_manifest(base_dir: Path) -> Path | None:
    for relative_path in DEFAULT_MANIFESTS:
        candidate = base_dir / relative_path
        if candidate.exists():
            return candidate
    return None


def normalize_canary_paths(paths: Iterable[str], base_dir: Path) -> tuple[Path, ...]:
    normalized = tuple(dict.fromkeys(resolve_path(path, base_dir) for path in paths if path))
    if not normalized:
        raise ValueError("at least one canary file path is required")
    return normalized


def normalize_canary_metadata(
    manifest_canaries: dict[str, dict[str, Any]],
    cli_canary_paths: Iterable[str],
    base_dir: Path,
) -> tuple[tuple[Path, ...], dict[Path, dict[str, Any]]]:
    canary_paths = normalize_canary_paths([*manifest_canaries.keys(), *cli_canary_paths], base_dir)
    metadata_by_path: dict[Path, dict[str, Any]] = {}

    for raw_path, metadata in manifest_canaries.items():
        resolved = resolve_path(raw_path, base_dir)
        metadata_by_path[resolved] = dict(metadata)

    for raw_path in cli_canary_paths:
        resolved = resolve_path(raw_path, base_dir)
        metadata_by_path.setdefault(resolved, {"source": "cli"})

    return canary_paths, metadata_by_path


def is_canary_event(event_path: Path, canary_paths: set[Path]) -> bool:
    try:
        resolved = event_path.resolve()
    except OSError:
        resolved = event_path.absolute()
    return resolved in canary_paths


def collect_suspect_processes(
    event_path: Path,
    watched_dirs: set[Path],
    timeout_seconds: float,
) -> tuple[list[dict[str, Any]], bool]:
    """Best-effort process enrichment.

    Watchdog does not expose the PID that caused an event. This scans open files
    so System 4 can prioritize kill decisions when the offender still has files
    open in the monitored tree.
    """

    if psutil is None:
        return [], False

    suspects: list[dict[str, Any]] = []
    current_pid = os.getpid()
    deadline = time.monotonic() + timeout_seconds
    timed_out = False

    for process in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"]):
        if time.monotonic() > deadline:
            timed_out = True
            break
        if process.info.get("pid") == current_pid:
            continue
        try:
            open_files = process.open_files()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            continue

        matched_files: list[str] = []
        for open_file in open_files:
            try:
                open_path = Path(open_file.path).resolve()
            except OSError:
                continue
            if open_path == event_path or any(is_relative_to(open_path, directory) for directory in watched_dirs):
                matched_files.append(str(open_path))

        if matched_files:
            info = dict(process.info)
            info["matched_open_files"] = matched_files[:10]
            suspects.append(info)

    return suspects, timed_out


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


class CanaryAlertWriter:
    def __init__(self, alert_dir: Path, stdout_alerts: bool) -> None:
        self.alert_dir = alert_dir
        self.stdout_alerts = stdout_alerts
        self.alert_dir.mkdir(parents=True, exist_ok=True)

    def write_alert(self, alert: dict[str, Any]) -> Path:
        
        final_path = self.alert_dir / "alert.json"
        temp_path = final_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(alert, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(final_path)

        if self.stdout_alerts:
            print(json.dumps(alert, sort_keys=True), flush=True)
        return final_path


class CanaryEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        canary_paths: set[Path],
        canary_metadata: dict[Path, dict[str, Any]],
        watched_dirs: set[Path],
        alert_writer: CanaryAlertWriter,
        debounce_seconds: float,
        process_scan_timeout_seconds: float,
    ) -> None:
        super().__init__()
        self.canary_paths = canary_paths
        self.canary_metadata = canary_metadata
        self.watched_dirs = watched_dirs
        self.alert_writer = alert_writer
        self.debounce_seconds = debounce_seconds
        self.process_scan_timeout_seconds = process_scan_timeout_seconds
        self.last_alert_by_path: dict[str, float] = {}

    def on_any_event(self, event: FileSystemEvent) -> None:
        if getattr(event, "is_directory", False):
            return

        event_type = getattr(event, "event_type", "unknown")
        src_path = Path(getattr(event, "src_path", ""))
        dest_path_raw = getattr(event, "dest_path", None)
        event_paths = [src_path]
        if dest_path_raw:
            event_paths.append(Path(dest_path_raw))

        canary_hit = next(
            (path for path in event_paths if path and is_canary_event(path, self.canary_paths)),
            None,
        )
        if canary_hit is None:
            return

        now = time.time()
        monotonic_now = time.monotonic()
        debounce_key = str(canary_hit)
        if monotonic_now - self.last_alert_by_path.get(debounce_key, 0.0) < self.debounce_seconds:
            return
        self.last_alert_by_path[debounce_key] = monotonic_now

        event_time_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        resolved_canary = canary_hit.resolve()
        metadata = self.canary_metadata.get(resolved_canary, {})
        expected_sha256 = metadata.get("expected_sha256")
        current_sha256 = sha256_of_file(resolved_canary)
        detection_started = time.perf_counter()
        suspects, process_scan_timed_out = collect_suspect_processes(
            resolved_canary,
            self.watched_dirs,
            self.process_scan_timeout_seconds,
        )
        detection_latency_ms = round((time.perf_counter() - detection_started) * 1000, 3)

        alert = {
            "alert_id": str(uuid4()),
            "alert_type": "canary_file_touched",
            "severity": "critical",
            "event_time_utc": event_time_utc,
            "event_type": event_type,
            "canary_path": str(resolved_canary),
            "registry_key": metadata.get("registry_key"),
            "source_manifest": metadata.get("source_manifest"),
            "target_directory": metadata.get("target_directory"),
            "expected_sha256": expected_sha256,
            "current_sha256": current_sha256,
            "hash_matches_manifest": (
                current_sha256 == expected_sha256 if current_sha256 and expected_sha256 else None
            ),
            "source_path": str(src_path.resolve()) if src_path else None,
            "destination_path": str(Path(dest_path_raw).resolve()) if dest_path_raw else None,
            "host": socket.gethostname(),
            "platform": platform.platform(),
            "monitor_pid": os.getpid(),
            "suspect_processes": suspects,
            "suspect_pid_available": bool(suspects),
            "process_scan_timed_out": process_scan_timed_out,
            "detection_latency_ms": detection_latency_ms,
            "recommended_action": "kill_suspect_processes_and_pause_encryption_workflow",
            "T1": now,
        }

        alert_path = self.alert_writer.write_alert(alert)
        print("\n[DEFENDER] Triggering automated ransomware kill sequence...\n")
        try:
            trigger_kill()
        except Exception as e:
            LOGGER.error("Failed to trigger kill engine: %s", e)
    
        LOGGER.critical(
            "Canary event detected: %s on %s, alert=%s, suspects=%s",
            event_type,
            canary_hit,
            alert_path,
            len(suspects),
        )


def build_config(args: argparse.Namespace, base_dir: Path) -> MonitorConfig:
    manifest = resolve_path(args.manifest, base_dir) if args.manifest else find_default_manifest(base_dir)
    cli_canary_paths = args.canary or []
    manifest_canaries: dict[str, dict[str, Any]] = {}

    if manifest:
        LOGGER.info("Loading canary manifest: %s", manifest)
        manifest_canaries = load_manifest(manifest)

    canary_paths, canary_metadata = normalize_canary_metadata(
        manifest_canaries,
        cli_canary_paths,
        base_dir,
    )
    alert_dir = resolve_path(args.alert_dir, base_dir)

    missing_paths = [path for path in canary_paths if not path.exists()]
    if missing_paths and not args.allow_missing:
        missing = "\n".join(f"  - {path}" for path in missing_paths)
        raise FileNotFoundError(
            "The following canary files do not exist. Run the canary seeder first "
            f"or pass --allow-missing:\n{missing}"
        )

    return MonitorConfig(
        canary_paths=canary_paths,
        canary_metadata=canary_metadata,
        alert_dir=alert_dir,
        debounce_seconds=args.debounce_seconds,
        heartbeat_seconds=args.heartbeat_seconds,
        process_scan_timeout_seconds=args.process_scan_timeout_seconds,
        stdout_alerts=args.stdout_alerts,
    )


def require_dependencies() -> None:
    missing = []
    if Observer is None:
        missing.append("watchdog")
    if psutil is None:
        missing.append("psutil")
    if missing:
        raise RuntimeError(
            "Missing required packages: "
            + ", ".join(missing)
            + ". Install them with: pip install -r requirements.txt"
        )


def run_monitor(config: MonitorConfig) -> int:
    require_dependencies()

    canary_paths = {path.resolve() for path in config.canary_paths}
    canary_metadata = {path.resolve(): metadata for path, metadata in config.canary_metadata.items()}
    watched_dirs = {path.parent.resolve() for path in canary_paths}
    alert_writer = CanaryAlertWriter(config.alert_dir, config.stdout_alerts)
    handler = CanaryEventHandler(
        canary_paths=canary_paths,
        canary_metadata=canary_metadata,
        watched_dirs=watched_dirs,
        alert_writer=alert_writer,
        debounce_seconds=config.debounce_seconds,
        process_scan_timeout_seconds=config.process_scan_timeout_seconds,
    )

    observer = Observer()
    for directory in sorted(watched_dirs):
        directory.mkdir(parents=True, exist_ok=True)
        observer.schedule(handler, str(directory), recursive=False)
        LOGGER.info("Watching canary directory: %s", directory)

    LOGGER.info("Monitoring %s canary file(s)", len(canary_paths))
    for canary_path in sorted(canary_paths):
        LOGGER.info("Canary armed: %s", canary_path)

    stop_requested = False

    def handle_stop(signum: int, _frame: Any) -> None:
        nonlocal stop_requested
        LOGGER.info("Received signal %s, stopping canary monitor", signum)
        stop_requested = True
        observer.stop()

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    observer.start()
    
    # Signal readiness via file
    with open("canary.ready", "w") as f:
        f.write("ready")
        
    try:
        while observer.is_alive() and not stop_requested:
            time.sleep(config.heartbeat_seconds)
            LOGGER.debug("Canary monitor heartbeat; watching %s files", len(canary_paths))
    finally:
        observer.stop()
        observer.join(timeout=5)
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor canary files and emit critical ransomware early-warning alerts."
    )
    parser.add_argument(
        "--manifest",
        help="Path to canary manifest JSON. Defaults to canary_config.json if present.",
    )
    parser.add_argument(
        "--canary",
        action="append",
        help="Canary file path to watch. May be provided multiple times.",
    )
    parser.add_argument(
        "--alert-dir",
        default="test_env",
        help="Directory where alert JSON files are written. Default: test_env",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Start even if canary files are not present yet.",
    )
    parser.add_argument(
        "--debounce-seconds",
        type=float,
        default=0.25,
        help="Suppress duplicate alerts for the same canary within this window. Default: 0.25",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=float,
        default=5.0,
        help="Internal heartbeat interval for debug logging. Default: 5.0",
    )
    parser.add_argument(
        "--process-scan-timeout-seconds",
        type=float,
        default=0.4,
        help="Best-effort psutil scan budget before writing the alert. Default: 0.4",
    )
    parser.add_argument(
        "--stdout-alerts",
        action="store_true",
        help="Also print alert JSON to stdout for demos or process supervisors.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    configure_logging(args.verbose)
    base_dir = Path.cwd()

    try:
        config = build_config(args, base_dir)
        return run_monitor(config)
    except Exception as exc:
        LOGGER.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
