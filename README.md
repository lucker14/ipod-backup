# iPod music backup

Back up files from an iPod mounted as a disk, check the copy, and optionally
rename tagged audio using embedded artist/title metadata. The app uses Python
3.10+ and has no third-party runtime dependencies.

## Quick start (no commands to type)

1. Connect the iPod and wait for it to appear on your computer.
2. Start `scripts/launchers/start_ipod_backup.bat` (Windows),
   `scripts/launchers/start_ipod_backup.command` (Mac, double-click), or
   `scripts/launchers/start_ipod_backup.sh` (Debian/Linux, run it from a
   terminal).
3. When asked where to save, press **Enter** for the suggested
   `~/Music/ipod-backup` folder, or type a different folder path.

The program finds the mounted iPod and copies **all** its files. Leave it
connected until it says the backup is complete. It never writes to the iPod.
The launcher creates a private `.venv`, installs this project into it, then
starts the backup. Python 3.10 or newer must be installed.

## Installation

### Current install options

| Platform/channel | Status | Install route |
|---|---|---|
| Windows | Launcher included; standalone installer/package not yet published | Install Python 3.10+, then run `scripts/launchers/start_ipod_backup.bat` |
| macOS | Homebrew tap available; beginner launcher also included | `brew tap lucker14/ipod-backup`, then `brew install ipod-backup` (trust the tap if Homebrew prompts) |
| Linux | Launcher included; project APT feed is being prepared | Install Python 3.10+, then run `scripts/launchers/start_ipod_backup.sh` |
| Any OS with Python | Source checkout install | `pipx install .` from a clone; a PyPI release is not published yet |
| macOS/Linux | GitHub Release installer available | See “Release installer” below |
| Debian/Ubuntu | `.deb` available for local installation; signed project APT feed not yet deployed | See “Native Linux packages” below |
| Fedora/RHEL, Alpine | Unsigned local `.rpm` / `.apk` assets; no maintained DNF/APK feeds | See [PUBLISHING.md](PUBLISHING.md); unsigned packages are not recommended for normal installation |
| Arch Linux | Development PKGBUILD only; not published to AUR | See [PUBLISHING.md](PUBLISHING.md) |
| FreeBSD/other BSD | No tested installer yet | Python/source use may work; platform discovery and packaging need testing |

All routes require Python 3.10 or newer. The Python package has no third-party
runtime dependencies. The beginner launchers create a private virtual
environment and install the project from the checkout.

### Release installer (macOS and Linux)

After a GitHub Release has been published and its workflow succeeds, download
and inspect the installer before running it:

```sh
curl -fsSLO https://github.com/lucker14/ipod-backup/releases/latest/download/install.sh
less install.sh
sh install.sh --user
```

Or install without saving a local copy:

```sh
curl -fsSL https://github.com/lucker14/ipod-backup/releases/latest/download/install.sh | sh -s -- --user
```

The one-line command is convenient, but downloading and reviewing the script
first is safer.

This installs `ipod-backup`, `ipod-backup-cli`, and `ipod-backup-test` under
`~/.local`; add `~/.local/bin` to `PATH` if needed. The installer requires
`curl`, `tar`, and Python 3.10+. It checks the archive against the release's
`SHA256SUMS`; because both are downloaded from GitHub, this detects corruption
but is not an independent publisher signature. Use `--version VERSION` to
choose a version already published as a GitHub Release.

### Install from a source checkout

With `pipx` installed:

```sh
pipx install .
```

This installs the three commands listed above. To try the Homebrew development
formula, run
`brew install --HEAD ./packaging/macos/homebrew/ipod-backup.rb` from a checkout.
It is not yet a versioned tap formula.

### Windows source install

Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/)
and download the repository. Double-click
`scripts/launchers/start_ipod_backup.bat`. The launcher
creates a private virtual environment and starts the interactive backup. A
WinGet, Chocolatey, or MSI release is not available yet.

### Native Linux packages

The GitHub Release includes a Debian package for local installation:

```sh
sudo apt install ./ipod-backup_0.1.2_all.deb
```

This requires Python 3.10 or newer. The `.deb` is also listed in a temporary
Cloudsmith trial feed, but that is not the maintained distribution channel.
A signed project-owned APT feed on GitHub Pages is being prepared; it is not
deployed or verified yet. Use the local `.deb` install above for now. Follow
[PUBLISHING.md](PUBLISHING.md) for maintainer setup; package-name install
instructions will be added after clean Debian and Ubuntu tests.

The v0.1.2 RPM was also uploaded to the temporary Cloudsmith trial feed but
has not been tested with DNF. An APK upload failed processing. The GitHub
Release RPM and APK files are unsigned; do not bypass package signature checks
to install them. Maintainer setup instructions are in [PUBLISHING.md](PUBLISHING.md).

## Supported devices

This is not limited to the 4th-generation iPod nano. It works from the mounted
filesystem layout, not a hard-coded model list. The host operating system must
mount the iPod as a readable volume. Automatic discovery looks for
`iPod_Control`; music organization expects audio files under
`iPod_Control/Music/Fxx`. Backup copies other files and folders under
`iPod_Control` too.

The physical device tested so far is one iPod nano (4th generation). Other
models that expose the same folders are **layout-compatible candidates, not
verified devices**. The software cannot identify an exact model from these
folders, and a matching layout does not guarantee that every file format,
database, or model-specific feature works. The tool does not use Apple's
device synchronization protocol and is not intended for iPod touch/iOS devices
that do not mount as a disk.

There is no model-size or music-count limit in the backup code. Available
destination space and filesystem limits (for example, a filesystem's maximum
file size) still apply. The limited integration test checks only five files
by default; increase `--limit` or use `--limit 0` to test more or all files.
The ordinary full backup is unlimited by default.

## TL;DR (technical)

From a checkout, first install the project into the active Python environment
with `python -m pip install -e .`. Then set `IPOD_SOURCE` to the mounted volume
path and `IPOD_BACKUP` to the destination. Example:

```sh
export IPOD_SOURCE='/Volumes/IPOD UªÍVAT'
export IPOD_BACKUP="$HOME/Music/iPod-backup"

python3 -m ipod_backup.device_test             # five-file venv + Docker test
python3 -m ipod_backup backup                  # all files; no limit by default
python3 -m ipod_backup compare --hash          # full SHA-256 verification
python3 -m ipod_backup organize                # rename tagged audio in place
```

The real-device test defaults to `--limit 5` per operation and exercises
backup, hash comparison, organize, and comparison again in both a temporary
venv and Docker. It detects mounted volumes containing `iPod_Control`; use
`--source PATH` to override detection, `--mode venv|docker` to select one
runtime, and `--limit 0` to test all files. It prompts before reading.

All ordinary `python -m ipod_backup` commands are unlimited by default. Add
`--limit N` to cap one operation; audio files are selected first. Backup
copies the iPod data without writing to it. Organize changes filenames only
in the backup.

The beginner launchers in `scripts/launchers/` create/reuse the repository's
private `.venv`, install the project, auto-detect a mounted iPod, ask for the
destination (default `~/Music/ipod-backup`), and start a complete unlimited
backup. To resume, start the same launcher and use the same destination.

The project currently has no third-party runtime dependencies. Its package
metadata and development tools are managed through `pyproject.toml`.

## Project layout

| Path | Contents |
|---|---|
| `src/ipod_backup/` | Installable application package and command entry points |
| `tests/` | Unit tests |
| `scripts/launchers/` | Beginner-friendly platform launchers |
| `packaging/` | Linux, macOS, and portable installer recipes |
| `.github/workflows/` | CI, release asset builds, and optional PyPI publishing |
| `Dockerfile` | Container image for the command-line tool |
| `PUBLISHING.md` | Maintainer release and package-channel instructions |

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
python -m ipod_backup backup "IPOD_MOUNT_PATH" "BACKUP_DIRECTORY"
python -m ipod_backup compare "IPOD_MOUNT_PATH" "BACKUP_DIRECTORY" --hash
python -m ipod_backup organize "BACKUP_DIRECTORY"
```

Once `IPOD_SOURCE` and `IPOD_BACKUP` are set, the positional paths can be
omitted. Use `python3` rather than `python` on Debian/macOS if necessary.

### 2. Run the limited device test

With Python available, run from this repository directory:

```text
python -m ipod_backup.device_test
```

Debian/macOS may require `python3 -m ipod_backup.device_test`. The script scans mounted
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
Docker run; the script does not write to the iPod. Docker mounts the installed
Python module read-only into `python:3.12-slim`; no project image build is
required. Temporary test copies are deleted after the test. This is an
integration smoke test, not a full backup or a verification of every track.

Options:

```text
python -m ipod_backup.device_test --mode venv           # only the venv test
python -m ipod_backup.device_test --mode docker         # only the Docker test
python -m ipod_backup.device_test --limit 10            # test up to 10 files per operation
python -m ipod_backup.device_test --limit 0              # no file limit
python -m ipod_backup.device_test --source "MOUNT_PATH"  # explicit mounted volume
python -m ipod_backup.device_test --work-dir "PATH"     # location for temporary copies
python -m ipod_backup.device_test --yes                  # skip confirmation
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
python -m ipod_backup backup
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
python -m ipod_backup backup --hash
```

### 4. Verify the complete backup

Keep the iPod connected and run:

```text
python -m ipod_backup compare --hash
```

Hash comparison reads all source and backup files and may take time.
`MISSING` indicates a source file absent from the backup; `DIFFERS` indicates
different sizes or hashes; `EXTRA` indicates a backup-only file. Nothing is
deleted. Omit `--hash` for a faster size-only comparison. Run this full
comparison before moving files out of their original folders.

### 5. Rename tracks (optional)

```text
python -m ipod_backup organize
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
python -m pip install --editable .
python -m ipod_backup.device_test
```

Debian/Linux or macOS:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable .
python -m ipod_backup.device_test
```

Debian may need `sudo apt install python3-venv`. Deactivate with `deactivate`.
Alternatively, run with the venv interpreter directly without activating it.
The beginner launchers perform these setup steps automatically and use the
repository's `.venv` without requiring manual activation.

## Docker

Build the image in the repository directory:

```text
docker build -t ipod-backup .
```

The real-device test uses `python:3.12-slim` and mounts the Python module and
device read-only into the container. It finds the mounted source on the host;
it does not make the container responsible for discovering USB hardware.

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

Unit tests (no connected iPod required; install the checkout with
`python -m pip install --editable .` first):

```text
python -m unittest discover -v
```

The real-device integration test is `python -m ipod_backup.device_test` and requires a mounted
iPod; Docker testing additionally requires a working Docker daemon. Use
`python3` instead of `python` on Debian/macOS if needed.

Licensed under the [MIT License](LICENSE). Retain its copyright and permission
notice when redistributing. The notice identifies Petr Pluhar as the original
creator.
