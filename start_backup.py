#!/usr/bin/env python3
"""Beginner-friendly interactive entry point for a complete iPod backup."""

from __future__ import annotations

import sys
from pathlib import Path

import device_test
import ipod_backup


def select_volume(candidates: list[Path]) -> Path:
    if not candidates:
        raise RuntimeError(
            "No mounted iPod was found. Connect it, wait for it to appear in "
            "Finder/File Explorer, and start this program again."
        )
    if len(candidates) == 1:
        return candidates[0]
    print("More than one mounted volume contains iPod_Control:")
    for index, candidate in enumerate(candidates, start=1):
        print(f"  {index}. {candidate}")
    while True:
        answer = input("Type the number for your iPod: ").strip()
        try:
            selected = int(answer)
        except ValueError:
            selected = 0
        if 1 <= selected <= len(candidates):
            return candidates[selected - 1]
        print(f"Please type a number from 1 to {len(candidates)}.")


def choose_destination() -> Path:
    default = Path.home() / "Music" / "ipod-backup"
    answer = input(f"\nWhere should the backup be saved? [{default}]\n> ").strip()
    return Path(answer).expanduser() if answer else default


def main() -> int:
    if not sys.stdin.isatty():
        print("Start this using the provided .bat, .command, or .sh launcher.", file=sys.stderr)
        return 2
    try:
        print("Looking for a connected iPod...")
        candidates = device_test.find_ipod_volumes(device_test.mounted_volume_roots())
        volume = select_volume(candidates)
        source = ipod_backup.resolve_source(volume)
        destination = choose_destination().resolve()
        ipod_backup.ensure_disjoint(source, destination)

        files = ipod_backup.scan_files(source)
        total_bytes = sum(info.size for info in files.values())
        print(f"\nFound: {volume}")
        print(f"Files: {len(files):,} ({total_bytes:,} bytes)")
        print(f"Backup folder: {destination}")
        if destination.exists():
            print("Existing files will be checked and the backup can resume.")
        print("\nStarting the full backup...")

        result = ipod_backup.backup(source, destination, attempts=3, deep=False)
        if result == 0:
            print(f"\nBackup complete: {destination}")
            print("The iPod was not modified. You can safely rerun this to resume.")
        else:
            print(
                f"\nSome files could not be copied. Reconnect the iPod and "
                f"start this again to resume: {destination}",
                file=sys.stderr,
            )
        return result
    except (OSError, RuntimeError, ValueError) as error:
        print(f"\nCould not complete the backup: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled. Completed files remain in the backup folder.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
