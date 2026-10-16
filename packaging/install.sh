#!/bin/sh
set -eu

REPOSITORY=lucker14/ipod-backup
RELEASE_BASE="https://github.com/$REPOSITORY/releases/latest/download"
ARCHIVE_NAME=ipod-backup-portable.tar.gz
PREFIX=/usr/local
VERSION=

usage() {
    printf '%s\n' \
        "Usage: install.sh [--user | --prefix PATH] [--version VERSION]" \
        "  --user        Install into ~/.local (no administrator access needed)." \
        "  --prefix PATH Install under PATH (default: /usr/local)." \
        "  --version     Install a specific release (default: latest)." >&2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --user)
            PREFIX=${HOME:?HOME must be set}/.local
            ;;
        --prefix)
            if [ "$#" -lt 2 ] || [ -z "$2" ]; then
                usage
                exit 2
            fi
            PREFIX=$2
            shift
            ;;
        --version)
            if [ "$#" -lt 2 ] || [ -z "$2" ]; then
                usage
                exit 2
            fi
            VERSION=$2
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            exit 2
            ;;
    esac
    shift
done

case "$PREFIX" in
    /*) ;;
    *) PREFIX=$PWD/$PREFIX ;;
esac

if [ -n "$VERSION" ]; then
    case "$VERSION" in
        ''|*[!0-9A-Za-z.+:~_-]*|.*|*..*)
            echo "Release version contains unsupported characters." >&2
            exit 2
            ;;
        v*) VERSION=${VERSION#v} ;;
    esac
    if [ -z "$VERSION" ]; then
        echo "Release version cannot be empty." >&2
        exit 2
    fi
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to download the release." >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3.10 or newer is required. Install Python 3 and retry." >&2
    exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    echo "Python 3.10 or newer is required. Detected: $(python3 --version 2>&1)." >&2
    exit 1
fi

WRITE_CHECK=$PREFIX
while [ ! -e "$WRITE_CHECK" ]; do
    PARENT=$(dirname "$WRITE_CHECK")
    if [ "$PARENT" = "$WRITE_CHECK" ]; then
        break
    fi
    WRITE_CHECK=$PARENT
done
if [ ! -w "$WRITE_CHECK" ]; then
    echo "Cannot write to $PREFIX. Re-run with --user, --prefix PATH, or administrator access." >&2
    exit 1
fi

if [ -n "$VERSION" ]; then
    RELEASE_BASE="https://github.com/$REPOSITORY/releases/download/v$VERSION"
else
    VERSION=$(python3 <<'PY'
import json
import re
import urllib.request

request = urllib.request.Request(
    "https://api.github.com/repos/lucker14/ipod-backup/releases/latest",
    headers={"Accept": "application/vnd.github+json", "User-Agent": "ipod-backup-installer"},
)
with urllib.request.urlopen(request, timeout=20) as response:
    tag = json.load(response)["tag_name"]
version = tag[1:] if tag.startswith("v") else tag
if not re.fullmatch(r"(?!\.)(?!.*\.\.)[0-9A-Za-z.+:~_-]+", version):
    raise SystemExit("Latest GitHub release has an invalid version tag.")
print(version)
PY
    )
    RELEASE_BASE="https://github.com/$REPOSITORY/releases/download/v$VERSION"
fi

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ipod-backup-install.XXXXXX")
STAGING=
cleanup() {
    rm -rf "$TEMP_DIR"
    if [ -n "$STAGING" ]; then
        rm -rf "$STAGING"
    fi
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

curl --fail --location --silent --show-error \
    "$RELEASE_BASE/SHA256SUMS" -o "$TEMP_DIR/SHA256SUMS"
curl --fail --location --silent --show-error \
    "$RELEASE_BASE/$ARCHIVE_NAME" -o "$TEMP_DIR/$ARCHIVE_NAME"

python3 - "$TEMP_DIR/SHA256SUMS" "$TEMP_DIR/$ARCHIVE_NAME" "$ARCHIVE_NAME" <<'PY'
import hashlib
import pathlib
import sys
import tarfile

manifest = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
archive_path = pathlib.Path(sys.argv[2])
archive_name = sys.argv[3]
entries = [
    line.split(maxsplit=1)
    for line in manifest.splitlines()
    if len(line.split(maxsplit=1)) == 2
    and line.split(maxsplit=1)[1].lstrip("*") == archive_name
]
if len(entries) != 1:
    raise SystemExit(f"Release checksum manifest has no unique entry for {archive_name}.")
expected = entries[0][0]
actual = hashlib.sha256(archive_path.read_bytes()).hexdigest()
if actual != expected:
    raise SystemExit("Downloaded archive checksum does not match SHA256SUMS.")

expected_members = {
    "ipod-backup",
    "ipod-backup/LICENSE",
    "ipod-backup/ipod_backup.py",
    "ipod-backup/device_test.py",
    "ipod-backup/start_backup.py",
}
with tarfile.open(archive_path, "r:gz") as archive:
    members = archive.getmembers()
    if {member.name for member in members} != expected_members:
        raise SystemExit("Release archive contains an unexpected file list.")
    if any(
        member.name not in expected_members
        or not (member.isdir() if member.name == "ipod-backup" else member.isfile())
        for member in members
    ):
        raise SystemExit("Release archive contains an unexpected file type.")
PY

if ! tar -tzf "$TEMP_DIR/$ARCHIVE_NAME" | awk '
    /^\// { exit 1 }
    /(^|\/)\.\.(\/|$)/ { exit 1 }
    END { if (NR == 0) exit 1 }
'; then
    echo "The release archive has an invalid or empty file list." >&2
    exit 1
fi

DEST="$PREFIX/lib/ipod-backup/$VERSION"
BIN="$PREFIX/bin"
if [ -e "$DEST" ]; then
    if [ ! -f "$DEST/.managed-by-ipod-backup-installer" ]; then
        echo "Refusing to replace an unmanaged directory: $DEST" >&2
        exit 1
    fi
fi
mkdir -p "$PREFIX/lib/ipod-backup" "$BIN"
tar -xzf "$TEMP_DIR/$ARCHIVE_NAME" -C "$TEMP_DIR"
STAGING="$PREFIX/lib/ipod-backup/.${VERSION}.install.$$"
mkdir "$STAGING"
cp "$TEMP_DIR/ipod-backup/"* "$STAGING/"
touch "$STAGING/.managed-by-ipod-backup-installer"
if [ -d "$DEST" ]; then
    rm -rf "$DEST"
fi
mv "$STAGING" "$DEST"
STAGING=

for command_name in ipod-backup ipod-backup-cli ipod-backup-test; do
    case "$command_name" in
        ipod-backup) module=start_backup.py ;;
        ipod-backup-cli) module=ipod_backup.py ;;
        ipod-backup-test) module=device_test.py ;;
    esac
    printf '%s\n' \
        '#!/bin/sh' \
        'SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)' \
        "exec python3 \"\$SCRIPT_DIR/../lib/ipod-backup/$VERSION/$module\" \"\$@\"" \
        > "$BIN/$command_name"
    chmod 755 "$BIN/$command_name"
done

printf 'Installed iPod Backup %s under %s.\n' "$VERSION" "$PREFIX"
case ":$PATH:" in
    *":$BIN:"*) ;;
    *) printf 'Add %s to PATH to run the installed commands.\n' "$BIN" ;;
esac
