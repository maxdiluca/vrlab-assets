#!/usr/bin/env python3
"""Install, inspect or remove the VR Lab weekly Assetbots LaunchAgent."""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path


LABEL = "uk.ac.bham.vrlab.assetbots-backup"


def launchctl(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/launchctl", *arguments], text=True, check=check, capture_output=True
    )


def default_output_root(repo_root: Path) -> Path:
    return repo_root.parent / "Equipment queries" / "Assetbots Backups"


def plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def domain() -> str:
    return f"gui/{os.getuid()}"


def install(output_root: Path, repo_root: Path, *, skip_key_check: bool = False) -> None:
    backup_script = repo_root / "scripts" / "assetbots_backup.py"
    if not backup_script.is_file():
        raise SystemExit(f"Backup script not found: {backup_script}")
    system_python = Path("/usr/bin/python3")
    python = system_python if system_python.is_file() else Path(sys.executable).resolve()
    output_root = output_root.expanduser().resolve()
    logs = output_root / "_logs"
    logs.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.chmod(0o700)
    logs.chmod(0o700)

    if not skip_key_check:
        result = subprocess.run(
            [
                str(python),
                str(backup_script),
                "--output-root",
                str(output_root),
                "--dry-run",
            ],
            text=True,
            check=False,
        )
        if result.returncode:
            raise SystemExit("API-key validation failed; the weekly task was not installed.")

    plist = {
        "Label": LABEL,
        "ProgramArguments": [
            str(python),
            str(backup_script),
            "--output-root",
            str(output_root),
        ],
        "WorkingDirectory": str(repo_root),
        "StartCalendarInterval": {"Weekday": 2, "Hour": 7, "Minute": 0},
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "StandardOutPath": str(logs / "weekly-backup.log"),
        "StandardErrorPath": str(logs / "weekly-backup-error.log"),
    }

    destination = plist_path()
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = destination.with_suffix(".plist.tmp")
    with temporary.open("wb") as handle:
        plistlib.dump(plist, handle, sort_keys=True)
    temporary.chmod(0o600)
    temporary.replace(destination)

    launchctl("bootout", domain(), str(destination), check=False)
    launchctl("bootstrap", domain(), str(destination))
    launchctl("enable", f"{domain()}/{LABEL}")
    print(f"Installed {LABEL}: Mondays at 07:00 local time.")
    print(f"Backup destination: {output_root}")


def uninstall() -> None:
    destination = plist_path()
    launchctl("bootout", domain(), str(destination), check=False)
    if destination.exists():
        destination.unlink()
    print(f"Removed {LABEL}. Existing backups were retained.")


def status() -> int:
    result = launchctl("print", f"{domain()}/{LABEL}", check=False)
    if result.returncode:
        print(f"{LABEL} is not installed.")
        return 1
    print(result.stdout)
    return 0


def run_now(repo_root: Path, output_root: Path) -> int:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "assetbots_backup.py"),
        "--output-root",
        str(output_root.expanduser().resolve()),
    ]
    return subprocess.run(command, check=False).returncode


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall", "status", "run-now"))
    parser.add_argument(
        "--output-root",
        type=Path,
        default=default_output_root(repo_root),
        help="Default: the lab shared library's Equipment queries/Assetbots Backups",
    )
    parser.add_argument(
        "--skip-key-check",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    if args.action == "install":
        install(args.output_root, repo_root, skip_key_check=args.skip_key_check)
        return 0
    if args.action == "uninstall":
        uninstall()
        return 0
    if args.action == "status":
        return status()
    return run_now(repo_root, args.output_root)


if __name__ == "__main__":
    raise SystemExit(main())
