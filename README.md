# iPod nano backup

Back up files from an iPod mounted as a disk, check the copy, and optionally
rename tagged audio using embedded artist/title metadata. Supports Windows,
Debian/Linux, and macOS. Python 3.10+; no third-party Python packages.

## Quick start (no commands to type)

1. Connect the iPod and wait for it to appear on your computer.
2. Start `start_ipod_backup.bat` (Windows), `start_ipod_backup.command` (Mac,
   double-click), or `start_ipod_backup.sh` (Debian/Linux, run it from a
   terminal).
3. When asked where to save, press **Enter** for the suggested
   `~/Music/ipod-backup` folder, or type a different folder path.

The program finds the mounted iPod and copies **all** its files. Leave it
connected until it says the backup is complete. It never writes to the iPod.
Python 3.10 or newer must be installed.

## TL;DR (technical)

From the repository directory, set `IPOD_SOURCE` to the mounted volume path
and `IPOD_BACKUP` to the destination. Example:

```sh
export IPOD_SOURCE='/Volumes/IPOD UªÍVAT'
export IPOD_BACKUP="$HOME/Music/iPod-backup"

python3 device_test.py                         # five-file venv + Docker test
python3 ipod_backup.py backup                  # all files; no limit by default
python3 ipod_backup.py compare --hash          # full SHA-256 verification
python3 ipod_backup.py organize                # rename tagged audio in place
```

The real-device test defaults to `--limit 5` per operation and exercises
backup, hash comparison, organize, and comparison again in both a temporary
venv and Docker. It detects mounted volumes containing `iPod_Control`; use
`--source PATH` to override detection, `--mode venv|docker` to select one
runtime, and `--limit 0` to test all files. It prompts before reading.

All ordinary `ipod_backup.py` commands are unlimited by default. Add
`--limit N` to cap one operation; audio files are selected first. Backup
copies the iPod data without writing to it. Organize changes filenames only
in the backup.

The beginner launchers run `start_backup.py`: they auto-detect a mounted
iPod, ask for the destination (default `~/Music/ipod-backup`), then start a
complete unlimited backup. To resume, start the same launcher and use the
same destination.

Create a venv with `python3 -m venv .venv && source .venv/bin/activate`
(Windows PowerShell: `py -3 -m venv .venv; .\.venv\Scripts\Activate.ps1`).
No packages need installing.

Docker: `docker build -t ipod-backup .`. The host must mount the iPod first;
the device test discovers it on the host and bind-mounts it read-only into
the container. Docker Desktop/Engine must be running.

## Using the tool

### 1. Mount the iPod and set paths

Connect the iPod and let the operating system mount it. `IPOD_SOURCE` should
be the volume root (the directory containing `iPod_Control`) or that folder
itself. `IPOD_BACKUP` should point to a folder on a different volume or
directory tree.

macOS (Terminal; quote volume names containing spaces):

```sh
ls -1 /Volumes
export IPOD_SOURCE='/Volumes/IPOD UªÍVAT'
export IPOD_BACKUP="$HOME/Music/iPod-backup"
```

Debian/Linux (Bash; replace the example mount path):

```sh
lsblk
ls "/media/$USER"
export IPOD_SOURCE="/media/$USER/IPOD"
export IPOD_BACKUP="$HOME/Music/iPod-backup"
```

Windows (PowerShell; replace `E:\` with the iPod drive):

```powershell
$env:IPOD_SOURCE = 'E:\'
$env:IPOD_BACKUP = Join-Path $env:USERPROFILE 'Music\iPod-backup'
```

Paths can instead be passed as positional arguments:

```text
python ipod_backup.py backup "IPOD_MOUNT_PATH" "BACKUP_DIRECTORY"
python ipod_backup.py compare "IPOD_MOUNT_PATH" "BACKUP_DIRECTORY" --hash
python ipod_backup.py organize "BACKUP_DIRECTORY"
```

Once `IPOD_SOURCE` and `IPOD_BACKUP` are set, the positional paths can be
omitted. Use `python3` rather than `python` on Debian/macOS if necessary.

### 2. Run the limited device test

With Python available, run from this repository directory:

```text
python device_test.py
```

Debian/macOS may require `python3 device_test.py`. The script scans mounted
volume roots for `iPod_Control`; it does not recursively search unrelated
filesystems and does not need root/admin privileges in normal cases. If
multiple matching volumes are mounted, select one interactively or pass
`--source "MOUNT_PATH"`. To explicitly request automatic discovery, use
`--source auto`.

By default, the test:

1. Selects up to five files, prioritizing audio.
2. Copies them to a temporary directory using a temporary venv.
3. Compares selected files with SHA-256.
4. Organizes the temporary audio copy using its embedded tags.
5. Compares the renamed copy again.
6. Repeats those operations in Docker.

The test asks before it starts. The connected device is read-only for the
Docker run; the script does not write to the iPod. Temporary test copies are
deleted after the test. This is an integration smoke test, not a full backup
or a verification of every track. In a successful Mac run against this iPod,
all five selected tracks copied, matched by SHA-256, were renamed, and matched
again in both venv and Docker. The device had 440 files at that time.

Options:

```text
python device_test.py --mode venv           # only the venv test
python device_test.py --mode docker         # only the Docker test
python device_test.py --limit 10            # test up to 10 files per operation
python device_test.py --limit 0              # no file limit
python device_test.py --source "MOUNT_PATH"  # explicit mounted volume
python device_test.py --work-dir "PATH"     # location for temporary copies
python device_test.py --yes                  # skip confirmation
```

The test scans the iPod file list to choose files but only copies and hashes
the selected set. Allow free space for at least that selected set. Docker
cannot discover or mount USB hardware independently: the host must mount the
iPod, and Docker Desktop/Engine must be allowed to share the iPod mount and
temporary work directory.

### 3. Make a complete backup

The regular backup command is unlimited unless `--limit` is explicitly
provided:

```text
python ipod_backup.py backup
```

The script backs up `iPod_Control` when present; otherwise, it backs up the
supplied source directory. It preserves the directory structure and copies
music, library databases, artwork, and other files. It never modifies the
iPod. Each file is copied to a temporary file, verified, then moved into
place. Read/copy attempts are retried three times by default. If a read still
fails or the cable disconnects, reconnect the iPod and rerun the same command
to resume.

Existing files are skipped by size by default. Use `--hash` to hash the source
and existing destination file before skipping:

```text
python ipod_backup.py backup --hash
```

### 4. Verify the complete backup

Keep the iPod connected and run:

```text
python ipod_backup.py compare --hash
```

Hash comparison reads all source and backup files and may take time.
`MISSING` indicates a source file absent from the backup; `DIFFERS` indicates
different sizes or hashes; `EXTRA` indicates a backup-only file. Nothing is
deleted. Omit `--hash` for a faster size-only comparison. Run this full
comparison before moving files out of their original folders.

### 5. Rename tracks (optional)

```text
python ipod_backup.py organize
```

MP3 ID3 and M4A/MP4-family embedded tags are used to create names such as
`Artist - Title.mp3`. Directories and extensions are preserved; duplicate
names get numbered suffixes. Files without usable tags remain unchanged. The
organizer does not use the iPod's `iTunesDB` as a fallback and does not rename
files on the iPod.

Organizing is retryable. It processes the backup, retries individual rename
errors, and can be rerun after resolving a problem. The hidden
`.ipod-backup-names.json` file lets compare and resumed backup follow renamed
files while they stay in their original folders.

### 6. Optional listening folder and playback

For a flat collection, copy (preferably, to retain the verifiable backup) the
audio files from `IPOD_BACKUP/Music/F00`, `F01`, and similar folders into a
separate folder such as `~/Documents/ipod` (Windows:
`%USERPROFILE%\Documents\ipod`). Preserve duplicate tracks with distinct
filenames. Moving instead of copying changes the backup layout; run backup
again from the connected iPod to restore the original files.

For shuffle with AirPlay on macOS, import the folder in Music, create a
playlist, enable shuffle, and select the AirPlay TV/Apple TV. Windows and
Debian/Linux playback and AirPlay support depend on the player and receiver;
they are outside the scope of this script.

## Virtual environment

The script uses only the standard library. From the repository directory:

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python device_test.py
```

Debian/Linux or macOS:

```sh
python3 -m venv .venv
source .venv/bin/activate
python device_test.py
```

Debian may need `sudo apt install python3-venv`. Deactivate with `deactivate`.
Alternatively, run with the venv interpreter directly without activating it.

## Docker

Build the image in the repository directory:

```text
docker build -t ipod-backup .
```

The real-device test builds and uses its own `ipod-backup:device-test` image.
It finds the mounted source on the host; it does not make the container
responsible for discovering USB hardware.

Example manual run on Debian/Linux or macOS (with `IPOD_SOURCE` and
`IPOD_BACKUP` set):

```sh
mkdir -p "$IPOD_BACKUP"
docker run --rm --user "$(id -u):$(id -g)" \
  --mount "type=bind,source=$IPOD_SOURCE,target=/ipod,readonly" \
  --mount "type=bind,source=$IPOD_BACKUP,target=/backup" \
  ipod-backup backup /ipod /backup
```

Windows Docker Desktop users should use PowerShell paths in `--mount` and
ensure Docker Desktop can access both host folders. The iPod mount is read-only;
the backup folder must be writable.

## Tests and license

Unit tests (no connected iPod required):

```text
python -m unittest -v
```

The real-device integration test is `device_test.py` and requires a mounted
iPod; Docker testing additionally requires a working Docker daemon. Use
`python3` instead of `python` on Debian/macOS if needed.

Licensed under the [MIT License](LICENSE). Retain its copyright and permission
notice when redistributing. The notice identifies Petr Pluhar as the original
creator.
