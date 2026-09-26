#!/usr/bin/env python3
"""Find a mounted iPod and exercise backup, compare, and organize in venv/Docker."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

import ipod_backup

REPOSITORY = Path(__file__).resolve().parent
DOCKER_IMAGE = "ipod-backup:device-test"


def windows_drive_roots() -> list[Path]:
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_drive_strings = kernel32.GetLogicalDriveStringsW
    get_drive_strings.argtypes = [ctypes.c_uint, ctypes.c_wchar_p]
    get_drive_strings.restype = ctypes.c_uint
    required = get_drive_strings(0, None)
    if not required:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_unicode_buffer(required)
    written = get_drive_strings(required, buffer)
    if not written or written >= required:
        raise ctypes.WinError(ctypes.get_last_error())
    return [Path(value) for value in buffer[:written].split("\0") if value]


def linux_mount_roots() -> list[Path]:
    roots: set[Path] = set()
    mountinfo = Path("/proc/self/mountinfo")
    if mountinfo.exists():
        for line in mountinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            fields = line.split()
            if len(fields) > 4:
                decoded = fields[4].replace("\\040", " ").replace("\\011", "\t")
                decoded = decoded.replace("\\012", "\n").replace("\\134", "\\")
                roots.add(Path(decoded))
    user = os.environ.get("USER") or os.environ.get("LOGNAME")
    if user:
        roots.update((Path("/media") / user, Path("/run/media") / user))
    roots.add(Path("/mnt"))
    return sorted(roots)


def mounted_volume_roots(system: str | None = None) -> list[Path]:
    system = system or platform.system()
    if system == "Windows":
        return windows_drive_roots()
    if system == "Darwin":
        volumes = Path("/Volumes")
        return sorted(volumes.iterdir()) if volumes.is_dir() else []
    return linux_mount_roots()


def find_ipod_volumes(roots: list[Path]) -> list[Path]:
    candidates: set[Path] = set()
    for root in roots:
        try:
            if not root.is_dir():
                continue
            if root.name.casefold() == "ipod_control":
                candidates.add(root.resolve())
                continue
            if any(
                entry.is_dir() and entry.name.casefold() == "ipod_control"
                for entry in root.iterdir()
            ):
                candidates.add(root.resolve())
        except OSError:
            continue
    return sorted(candidates, key=lambda item: str(item).casefold())


def choose_source(explicit: str, candidates: list[Path]) -> Path:
    if explicit.casefold() != "auto":
        source = ipod_backup.resolve_source(Path(explicit))
        return source.parent if source.name.casefold() == "ipod_control" else source
    if not candidates:
        raise RuntimeError(
            "No mounted volume containing iPod_Control was found. Connect and "
            "mount the iPod, then retry with --source MOUNT_PATH if needed."
        )
    if len(candidates) == 1:
        return candidates[0]
    if not sys.stdin.isatty():
        raise RuntimeError(
            "More than one iPod-like volume was found. Specify one with --source."
        )
    print("Found multiple volumes containing iPod_Control:")
    for index, candidate in enumerate(candidates, start=1):
        print(f"  {index}. {candidate}")
    while True:
        answer = input("Select the iPod volume number: ").strip()
        try:
            selection = int(answer)
        except ValueError:
            selection = 0
        if 1 <= selection <= len(candidates):
            return candidates[selection - 1]
        print(f"Enter a number from 1 to {len(candidates)}.")


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", subprocess.list2cmdline(command) if os.name == "nt" else " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def run_suite(
    python: Path,
    source: Path,
    destination: Path,
    limit: int | None,
) -> None:
    tool = REPOSITORY / "ipod_backup.py"
    limit_option = ["--limit", str(limit)] if limit is not None else []
    run([
        str(python), str(tool), "backup", str(source), str(destination), *limit_option
    ])
    run([
        str(python), str(tool), "compare", str(source), str(destination),
        "--hash", *limit_option,
    ])
    run([
        str(python), str(tool), "organize", str(destination), *limit_option
    ])
    run([
        str(python), str(tool), "compare", str(source), str(destination),
        "--hash", *limit_option,
    ])


def docker_path(path: Path) -> str:
    value = path.resolve().as_posix()
    if "," in value:
        raise ValueError(f"Docker bind mount paths cannot contain commas: {path}")
    return value


def docker_run(
    command: list[str],
    source: Path,
    destination: Path,
    limit: int | None,
) -> None:
    limit_option = ["--limit", str(limit)] if limit is not None else []
    run(
        [
            "docker", "run", "--rm",
            "--mount", f"type=bind,source={docker_path(source)},target=/ipod,readonly",
            "--mount", f"type=bind,source={docker_path(destination)},target=/backup",
            "-e", "IPOD_SOURCE=/ipod",
            "-e", "IPOD_BACKUP=/backup",
            DOCKER_IMAGE, *command, *limit_option,
        ]
    )


def run_docker_suite(source: Path, destination: Path, limit: int | None) -> None:
    run(["docker", "build", "-t", DOCKER_IMAGE, str(REPOSITORY)])
    docker_run(["backup"], source, destination, limit)
    docker_run(["compare", "--hash"], source, destination, limit)
    docker_run(["organize"], source, destination, limit)
    docker_run(["compare", "--hash"], source, destination, limit)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Find a mounted iPod and test real-device backup, comparison, and "
            "organizing in a temporary venv and/or Docker."
        )
    )
    parser.add_argument(
        "--source",
        default="auto",
        metavar="PATH|auto",
        help="mounted volume path, or auto to inspect mounted volumes (default: auto)",
    )
    parser.add_argument(
        "--mode",
        choices=("both", "venv", "docker"),
        default="both",
        help="test environment(s), default: both",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(tempfile.gettempdir()),
        help="directory for temporary backup copies (must fit the selected files)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="maximum files per operation; audio files first, default: 5; use 0 for unlimited",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip confirmation before reading the selected files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.limit < 0:
            raise ValueError("--limit cannot be negative; use 0 for unlimited")
        limit = args.limit or None
        candidates = (
            find_ipod_volumes(mounted_volume_roots())
            if args.source.casefold() == "auto"
            else []
        )
        source = choose_source(args.source, candidates)
        files = ipod_backup.limit_files(
            ipod_backup.scan_files(ipod_backup.resolve_source(source)),
            limit,
        )
        total_bytes = sum(info.size for info in files.values())
        work_dir = args.work_dir.expanduser().resolve(strict=True)
        if not work_dir.is_dir():
            raise ValueError(f"Work directory is not a directory: {work_dir}")
        free_bytes = shutil.disk_usage(work_dir).free
        if free_bytes < total_bytes:
            raise RuntimeError(
                f"Not enough free space in {work_dir}: the iPod contains about "
                f"{total_bytes:,} bytes, but only {free_bytes:,} bytes are free."
            )

        print(f"Detected iPod volume: {source}")
        print(
            f"Files per operation: {limit if limit is not None else 'unlimited'} "
            f"(selected {len(files):,}; {total_bytes:,} bytes)"
        )
        print(f"Temporary destination: {work_dir}")
        print("The device will be read only; test copies are temporary and removed.")
        if not args.yes:
            if not sys.stdin.isatty():
                raise RuntimeError(
                    "This test reads the entire device. Run interactively or pass --yes."
                )
            answer = input("Continue with the real-device test? [y/N] ").strip().casefold()
            if answer not in {"y", "yes"}:
                print("Cancelled.")
                return 1

        if args.mode in {"both", "venv"}:
            print("\n=== Virtual environment test ===")
            with tempfile.TemporaryDirectory(
                prefix="ipod-venv-test-", dir=work_dir
            ) as temporary:
                temporary_root = Path(temporary)
                environment = temporary_root / ".venv"
                venv.EnvBuilder(with_pip=False).create(environment)
                python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                run_suite(python, source, temporary_root / "backup", limit)
            print("Virtual environment test passed.")

        if args.mode in {"both", "docker"}:
            if shutil.which("docker") is None:
                raise RuntimeError("Docker was selected, but the docker command is unavailable.")
            print("\n=== Docker test ===")
            with tempfile.TemporaryDirectory(
                prefix="ipod-docker-test-", dir=work_dir
            ) as temporary:
                temporary_root = Path(temporary)
                backup = temporary_root / "backup"
                backup.mkdir()
                run_docker_suite(source, backup, limit)
            print("Docker test passed.")

        print("\nAll selected real-device tests passed.")
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
