#!/bin/sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 VERSION [OUTPUT_DIRECTORY]" >&2
    exit 2
fi

VERSION=$1
OUTPUT_DIR=${2:-dist}
case "$VERSION" in
    ''|*[!0-9A-Za-z.+:~_-]*)
        echo "Version must contain only letters, digits, and . + : ~ _ - characters." >&2
        exit 2
        ;;
esac
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR=$(CDPATH= cd -- "$OUTPUT_DIR" && pwd)
mkdir "$STAGE/ipod-backup"
cp "$ROOT/ipod_backup.py" "$ROOT/device_test.py" "$ROOT/start_backup.py" \
    "$ROOT/LICENSE" "$STAGE/ipod-backup/"
COPYFILE_DISABLE=1 tar -C "$STAGE" -czf "$OUTPUT_DIR/ipod-backup-portable.tar.gz" ipod-backup
printf 'Portable archive created: %s\n' "$OUTPUT_DIR/ipod-backup-portable.tar.gz"
