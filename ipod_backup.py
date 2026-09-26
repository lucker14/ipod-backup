#!/usr/bin/env python3
"""Resumable, non-destructive backup and comparison for an iPod mounted as a disk."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

CHUNK_SIZE = 1024 * 1024
AUDIO_SUFFIXES = {".mp3", ".m4a", ".m4p", ".m4b", ".mp4"}
NAME_MAP_FILE = ".ipod-backup-names.json"


@dataclass(frozen=True)
class FileInfo:
    path: Path
    size: int


def resolve_source(source: Path) -> Path:
    """Use iPod_Control when the supplied path is the mounted volume root."""
    source = source.expanduser()
    if not source.exists() and source.name.endswith("$"):
        without_prompt_marker = source.with_name(source.name[:-1])
        if without_prompt_marker.exists():
            print(
                f"Note: {source} does not exist; using {without_prompt_marker} "
                "(removed trailing shell prompt '$').",
                file=sys.stderr,
            )
            source = without_prompt_marker
    if not source.exists():
        raise FileNotFoundError(
            f"Source path does not exist: {source}. Check that the iPod is mounted "
            "and that IPOD_SOURCE (or the supplied source argument) is its exact "
            "mount path."
        )
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise ValueError(f"Source is not a directory: {source}")
    if source.name.casefold() != "ipod_control":
        control = next(
            (entry for entry in source.iterdir()
             if entry.is_dir() and entry.name.casefold() == "ipod_control"),
            None,
        )
        if control is not None:
            source = control.resolve(strict=True)
    return source


def ensure_disjoint(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("Source and destination must not contain or overlap one another.")


def scan_files(root: Path) -> dict[str, FileInfo]:
    files: dict[str, FileInfo] = {}
    normalized: dict[str, str] = {}

    def onerror(error: OSError) -> None:
        raise error

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=onerror):
        kept_dirs: list[str] = []
        for name in dirs:
            full_path = Path(directory) / name
            if full_path.is_symlink():
                print(f"Warning: ignoring symbolic link: {full_path}", file=sys.stderr)
            else:
                kept_dirs.append(name)
        dirs[:] = sorted(kept_dirs)
        for name in sorted(names):
            full_path = Path(directory) / name
            if full_path.is_symlink():
                print(f"Warning: ignoring symbolic link: {full_path}", file=sys.stderr)
                continue
            if not full_path.is_file():
                continue
            relative = full_path.relative_to(root).as_posix()
            if relative == NAME_MAP_FILE:
                continue
            key = unicodedata.normalize("NFD", relative).casefold()
            previous = normalized.get(key)
            if previous is not None and previous != relative:
                raise ValueError(
                    "Two source paths collide on a case-insensitive or "
                    "Unicode-normalizing destination filesystem: "
                    f"{previous!r} and {relative!r}"
                )
            normalized[key] = relative
            files[relative] = FileInfo(full_path, full_path.stat().st_size)
    return files


def limit_files(files: dict[str, FileInfo], limit: int | None) -> dict[str, FileInfo]:
    if limit is None:
        return files
    if limit < 1:
        raise ValueError("--limit must be at least 1")
    ordered = sorted(
        files.items(),
        key=lambda item: (item[1].path.suffix.casefold() not in AUDIO_SUFFIXES, item[0]),
    )
    return dict(ordered[:limit])


def load_name_map(root: Path) -> dict[str, str]:
    manifest = root / NAME_MAP_FILE
    if not manifest.exists():
        return {}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError(f"Unsupported or invalid name map: {manifest}")
    mappings = data.get("renamed")
    if not isinstance(mappings, dict):
        raise ValueError(f"Invalid renamed-file entries in {manifest}")
    result: dict[str, str] = {}
    targets: set[str] = set()
    for original, current in mappings.items():
        if not isinstance(original, str) or not isinstance(current, str):
            raise ValueError(f"Invalid path entry in {manifest}")
        original_path = Path(original)
        current_path = Path(current)
        if (
            original_path.is_absolute()
            or current_path.is_absolute()
            or ".." in original_path.parts
            or ".." in current_path.parts
        ):
            raise ValueError(f"Unsafe path entry in {manifest}")
        if current in targets:
            raise ValueError(f"Duplicate destination path in {manifest}: {current}")
        result[original] = current
        targets.add(current)
    return result


def save_name_map(root: Path, mappings: dict[str, str]) -> None:
    manifest = root / NAME_MAP_FILE
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=root,
            prefix=".ipod-backup-names.",
            suffix=".partial",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump({"version": 1, "renamed": mappings}, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, manifest)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def decode_tag_text(data: bytes, encoding: int) -> str:
    encodings = {0: "latin-1", 1: "utf-16", 2: "utf-16-be", 3: "utf-8"}
    try:
        text = data.decode(encodings[encoding], errors="replace")
    except (IndexError, LookupError):
        return ""
    return next((part.strip() for part in text.split("\x00") if part.strip()), "").strip()


def id3_text_frames(data: bytes) -> tuple[str | None, str | None]:
    title = artist = None
    if len(data) < 10 or data[:3] != b"ID3":
        return title, artist
    major = data[3]
    if major not in (2, 3, 4):
        return title, artist
    tag_size_bytes = data[6:10]
    if any(byte & 0x80 for byte in tag_size_bytes):
        return title, artist
    tag_size = sum(byte << shift for byte, shift in zip(tag_size_bytes, (21, 14, 7, 0)))
    end = min(len(data), 10 + tag_size)
    offset = 10
    flags = data[5]
    if flags & 0x40:
        if offset + 4 > end:
            return title, artist
        extended_size_bytes = data[offset:offset + 4]
        if major == 4:
            extended_size = sum(
                byte << shift
                for byte, shift in zip(extended_size_bytes, (21, 14, 7, 0))
            )
            offset += extended_size
        else:
            offset += 4 + int.from_bytes(extended_size_bytes, "big")

    while offset < end:
        header_size = 6 if major == 2 else 10
        if offset + header_size > end:
            break
        if major == 2:
            frame_id = data[offset:offset + 3].decode("ascii", errors="ignore")
            frame_size = int.from_bytes(data[offset + 3:offset + 6], "big")
        else:
            frame_id = data[offset:offset + 4].decode("ascii", errors="ignore")
            size_bytes = data[offset + 4:offset + 8]
            if major == 4:
                if any(byte & 0x80 for byte in size_bytes):
                    break
                frame_size = sum(
                    byte << shift for byte, shift in zip(size_bytes, (21, 14, 7, 0))
                )
            else:
                frame_size = int.from_bytes(size_bytes, "big")
        if not frame_id.strip("\x00"):
            break
        frame_start = offset + header_size
        frame_end = frame_start + frame_size
        if frame_end > end or frame_size == 0:
            break

        wanted = {"TT2": "title", "TP1": "artist"} if major == 2 else {
            "TIT2": "title",
            "TPE1": "artist",
        }
        field = wanted.get(frame_id)
        if field and frame_start < frame_end:
            encoding = data[frame_start]
            value = decode_tag_text(data[frame_start + 1:frame_end], encoding)
            if value:
                if field == "title":
                    title = title or value
                else:
                    artist = artist or value
        offset = frame_end
    return title, artist


def mp4_file_atoms(stream, start: int, end: int):
    offset = start
    while offset + 8 <= end:
        stream.seek(offset)
        header = stream.read(8)
        if len(header) != 8:
            break
        size = int.from_bytes(header[:4], "big")
        atom_type = header[4:8]
        header_size = 8
        if size == 1:
            extended_size = stream.read(8)
            if len(extended_size) != 8:
                break
            size = int.from_bytes(extended_size, "big")
            header_size = 16
        elif size == 0:
            size = end - offset
        if size < header_size or offset + size > end:
            break
        yield atom_type, offset + header_size, offset + size
        offset += size


def mp4_text_tags(path: Path) -> tuple[str | None, str | None]:
    title = artist = None

    def find_metadata(stream, start: int, end: int) -> None:
        nonlocal title, artist
        for atom_type, payload_start, atom_end in mp4_file_atoms(stream, start, end):
            if atom_type in (b"moov", b"udta"):
                find_metadata(stream, payload_start, atom_end)
            elif atom_type == b"meta":
                find_metadata(stream, min(payload_start + 4, atom_end), atom_end)
            elif atom_type == b"ilst":
                for item_type, item_start, item_end in mp4_file_atoms(
                    stream, payload_start, atom_end
                ):
                    field = {
                        b"\xa9nam": "title",
                        b"\xa9ART": "artist",
                        b"aART": "artist",
                    }.get(item_type)
                    if field is None:
                        continue
                    for child_type, child_start, child_end in mp4_file_atoms(
                        stream, item_start, item_end
                    ):
                        if child_type == b"data" and child_end - child_start >= 8:
                            stream.seek(child_start + 8)
                            value = stream.read(min(child_end - child_start - 8, 1024 * 1024))
                            text = value.decode("utf-8", errors="replace").strip(
                                "\x00 \t\r\n"
                            )
                            if text:
                                if field == "title":
                                    title = title or text
                                else:
                                    artist = artist or text

    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        find_metadata(stream, 0, stream.tell())
    return title, artist


def audio_metadata(path: Path) -> tuple[str | None, str | None]:
    with path.open("rb") as stream:
        header = stream.read(10)
        if header[:3] == b"ID3":
            size_bytes = header[6:10]
            if any(byte & 0x80 for byte in size_bytes):
                return None, None
            tag_size = sum(byte << shift for byte, shift in zip(size_bytes, (21, 14, 7, 0)))
            stream.seek(0)
            tag = stream.read(10 + tag_size)
            title, artist = id3_text_frames(tag)
            if title or artist:
                return title, artist
        stream.seek(0, os.SEEK_END)
        file_size = stream.tell()
        if file_size >= 128:
            stream.seek(-128, os.SEEK_END)
            id3v1 = stream.read(128)
        else:
            id3v1 = b""

    if path.suffix.casefold() in {".m4a", ".m4p", ".m4b", ".mp4"}:
        title, artist = mp4_text_tags(path)
        if title or artist:
            return title, artist
    if id3v1[:3] == b"TAG":
        title = id3v1[3:33].decode("latin-1", errors="replace").strip(" \x00")
        artist = id3v1[33:63].decode("latin-1", errors="replace").strip(" \x00")
        return title or None, artist or None
    return None, None


def safe_filename_component(text: str, maximum_bytes: int = 200) -> str:
    text = "".join(
        "-" if character in '/\\:*?"<>|' else character
        for character in text
        if ord(character) >= 32 and ord(character) != 127
    )
    text = " ".join(text.split()).strip(" .")
    while text and len(text.encode("utf-8")) > maximum_bytes:
        text = text[:-1]
    return text


def filename_from_metadata(path: Path, title: str | None, artist: str | None) -> str | None:
    title = safe_filename_component(title or "")
    artist = safe_filename_component(artist or "")
    if artist and title:
        name = f"{artist} - {title}"
    else:
        name = title or artist
    if not name:
        return None
    if name.split(".", 1)[0].upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    }:
        name = f"_{name}"
    extension = path.suffix
    available = max(1, 240 - len(extension.encode("utf-8")))
    while name and len(name.encode("utf-8")) > available:
        name = name[:-1]
    return f"{name}{extension}"


def retry_rename(source: Path, destination: Path, attempts: int) -> None:
    last_error: OSError | None = None
    for attempt in range(attempts):
        try:
            source.rename(destination)
            return
        except OSError as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 8))
    assert last_error is not None
    raise last_error


def organize(root: Path, attempts: int, limit: int | None = None) -> int:
    files = {
        relative: info
        for relative, info in scan_files(root).items()
        if info.path.suffix.casefold() in AUDIO_SUFFIXES
    }
    files = limit_files(files, limit)
    name_map = load_name_map(root)
    renamed = 0
    skipped = 0
    untagged = 0
    failed = 0

    for relative, info in sorted(files.items()):
        source = info.path
        try:
            title, artist = audio_metadata(source)
            target_name = filename_from_metadata(source, title, artist)
            if target_name is None:
                untagged += 1
                print(f"NO TAGS  {relative}")
                continue
            if target_name == source.name:
                skipped += 1
                continue
            destination = source.with_name(target_name)
            base = destination.stem
            extension = destination.suffix
            number = 2
            while destination.exists():
                destination = source.with_name(f"{base} ({number}){extension}")
                number += 1
            name_map[relative] = destination.relative_to(root).as_posix()
            save_name_map(root, name_map)
            retry_rename(source, destination, attempts)
            renamed += 1
            print(f"Renamed  {relative} -> {destination.relative_to(root).as_posix()}")
        except (OSError, UnicodeError) as error:
            failed += 1
            print(f"FAILED   {relative}: {error}", file=sys.stderr)

    print(
        f"Organizing finished: {renamed} renamed, {skipped} already named, "
        f"{untagged} without usable tags, {failed} failed. "
        f"Processed {len(files)} audio files"
        f"{f' (limit {limit})' if limit is not None else ''}. "
        "Rerun the same command to continue after errors."
    )
    return 1 if failed else 0


def copy_one(source: FileInfo, destination: Path, attempts: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error: OSError | None = None

    for attempt in range(attempts):
        temporary: Path | None = None
        try:
            before = source.path.stat()
            digest = hashlib.sha256()
            copied = 0
            with source.path.open("rb") as input_stream:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=destination.parent,
                    prefix=f".{destination.name}.",
                    suffix=".ipod-backup-partial",
                    delete=False,
                ) as output_stream:
                    temporary = Path(output_stream.name)
                    while chunk := input_stream.read(CHUNK_SIZE):
                        output_stream.write(chunk)
                        digest.update(chunk)
                        copied += len(chunk)
                    output_stream.flush()
                    os.fsync(output_stream.fileno())

            after = source.path.stat()
            if copied != before.st_size or after.st_size != before.st_size:
                raise OSError(f"Source changed or returned a short read: {source.path}")
            if sha256_file(temporary) != digest.hexdigest():
                raise OSError(f"Local copy verification failed: {destination}")

            os.replace(temporary, destination)
            temporary = None
            os.utime(destination, ns=(after.st_atime_ns, after.st_mtime_ns))
            return
        except OSError as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 8))
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    assert last_error is not None
    raise last_error


def compare(
    source_root: Path,
    destination_root: Path,
    deep: bool,
    limit: int | None = None,
) -> int:
    all_source_files = scan_files(source_root)
    source_files = limit_files(all_source_files, limit)
    destination_files = scan_files(destination_root) if destination_root.exists() else {}
    name_map = load_name_map(destination_root) if destination_root.exists() else {}
    expected_destinations = {
        name_map.get(relative, relative): relative for relative in all_source_files
    }
    selected_destinations = {
        name_map.get(relative, relative): relative for relative in source_files
    }
    missing = sorted(
        relative for destination, relative in selected_destinations.items()
        if destination not in destination_files
    )
    extra = sorted(destination_files.keys() - expected_destinations.keys())
    different: list[str] = []

    for destination_path, relative in sorted(selected_destinations.items()):
        if destination_path not in destination_files:
            continue
        source = source_files[relative]
        destination = destination_files[destination_path]
        if source.size != destination.size:
            different.append(relative)
        elif deep:
            try:
                if sha256_file(source.path) != sha256_file(destination.path):
                    different.append(relative)
            except OSError as error:
                print(f"Error hashing {relative}: {error}", file=sys.stderr)
                different.append(relative)

    for relative in missing:
        print(f"MISSING  {relative}")
    for relative in different:
        print(f"DIFFERS  {relative}")
    for relative in extra:
        print(f"EXTRA    {relative}")

    print(
        f"Compared {len(source_files)} of {len(all_source_files)} source files"
        f"{f' (limit {limit})' if limit is not None else ''}: "
        f"{len(missing)} missing, {len(different)} different, {len(extra)} extra."
    )
    return 1 if missing or different or extra else 0


def backup(
    source_root: Path,
    destination_root: Path,
    attempts: int,
    deep: bool,
    limit: int | None = None,
) -> int:
    source_files = limit_files(scan_files(source_root), limit)
    destination_root.mkdir(parents=True, exist_ok=True)
    name_map = load_name_map(destination_root)
    copied = 0
    skipped = 0
    failed = 0

    for relative, source in sorted(source_files.items()):
        destination_relative = name_map.get(relative, relative)
        destination = destination_root / Path(destination_relative)
        try:
            if destination.is_file() and destination.stat().st_size == source.size:
                try:
                    already_matches = (
                        not deep or sha256_file(source.path) == sha256_file(destination)
                    )
                except OSError:
                    already_matches = False
                if already_matches:
                    skipped += 1
                    continue
            copy_one(source, destination, attempts)
            copied += 1
            print(f"Copied   {relative}")
        except OSError as error:
            failed += 1
            print(f"FAILED   {relative}: {error}", file=sys.stderr)

    print(
        f"Backup finished: {copied} copied, {skipped} already present, "
        f"{failed} failed. Processed {len(source_files)} source files"
        f"{f' (limit {limit})' if limit is not None else ''}. "
        "No destination files were deleted."
    )
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Back up and compare music/library files from a mounted iPod."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("backup", "compare"):
        command = subparsers.add_parser(name)
        command.add_argument(
            "source",
            type=Path,
            nargs="?",
            default=os.environ.get("IPOD_SOURCE"),
            help="mounted iPod path (defaults to the IPOD_SOURCE environment variable)",
        )
        command.add_argument(
            "destination",
            type=Path,
            nargs="?",
            default=os.environ.get("IPOD_BACKUP"),
            help="backup directory (defaults to the IPOD_BACKUP environment variable)",
        )
        command.add_argument(
            "--hash",
            action="store_true",
            help="hash existing files instead of relying on file sizes (slower)",
        )
        command.add_argument(
            "--limit",
            type=int,
            help="maximum files to process; audio files are selected first (default: unlimited)",
        )
        if name == "backup":
            command.add_argument(
                "--attempts",
                type=int,
                default=3,
                help="read/copy attempts per file (default: 3)",
            )
    organize_command = subparsers.add_parser(
        "organize",
        help="rename backed-up audio files using embedded artist/title tags",
    )
    organize_command.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=os.environ.get("IPOD_BACKUP"),
        help="backup directory (defaults to the IPOD_BACKUP environment variable)",
    )
    organize_command.add_argument(
        "--attempts",
        type=int,
        default=3,
        help="rename attempts per file (default: 3)",
    )
    organize_command.add_argument(
        "--limit",
        type=int,
        help="maximum audio files to process (default: unlimited)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.limit is not None and args.limit < 1:
            raise ValueError("--limit must be at least 1")
        if args.command == "organize":
            if args.attempts < 1:
                raise ValueError("--attempts must be at least 1")
            if args.directory is None:
                raise ValueError(
                    "Supply a backup directory or set the IPOD_BACKUP environment variable."
                )
            directory = args.directory.expanduser().resolve(strict=True)
            if not directory.is_dir():
                raise ValueError(f"Not a directory: {directory}")
            print(f"Organizing backup in place: {directory}")
            return organize(directory, args.attempts, args.limit)

        if args.source is None:
            raise ValueError(
                "Supply the iPod mount path or set the IPOD_SOURCE environment variable."
            )
        if args.destination is None:
            raise ValueError(
                "Supply a backup directory or set the IPOD_BACKUP environment variable."
            )
        source_root = resolve_source(args.source)
        destination_root = args.destination.expanduser().resolve()
        ensure_disjoint(source_root, destination_root)
        print(f"Reading from: {source_root}")
        print(f"Saving to:    {destination_root}")

        if args.command == "backup":
            if args.attempts < 1:
                raise ValueError("--attempts must be at least 1")
            return backup(
                source_root, destination_root, args.attempts, args.hash, args.limit
            )
        return compare(source_root, destination_root, args.hash, args.limit)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
