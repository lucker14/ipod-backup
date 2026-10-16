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
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/usr/lib/ipod-backup" "$STAGE/usr/bin" \
    "$STAGE/usr/share/licenses/ipod-backup" "$OUTPUT_DIR"
OUTPUT_DIR=$(CDPATH= cd -- "$OUTPUT_DIR" && pwd)
cp "$ROOT/ipod_backup.py" "$ROOT/device_test.py" "$ROOT/start_backup.py" \
    "$STAGE/usr/lib/ipod-backup/"
cp "$ROOT/LICENSE" "$STAGE/usr/share/licenses/ipod-backup/LICENSE"

for command_name in ipod-backup ipod-backup-cli ipod-backup-test; do
    case "$command_name" in
        ipod-backup) module=start_backup.py ;;
        ipod-backup-cli) module=ipod_backup.py ;;
        ipod-backup-test) module=device_test.py ;;
    esac
    printf '%s\n' \
        '#!/bin/sh' \
        "exec python3 /usr/lib/ipod-backup/$module \"\$@\"" \
        > "$STAGE/usr/bin/$command_name"
    chmod 755 "$STAGE/usr/bin/$command_name"
done

mkdir -p "$STAGE/usr/share/doc/ipod-backup"
cp "$ROOT/README.md" "$STAGE/usr/share/doc/ipod-backup/README.md"

fpm \
    --input-type dir \
    --output-type deb \
    --name ipod-backup \
    --version "$VERSION" \
    --architecture all \
    --depends 'python3 >= 3.10' \
    --description "Back up files from an iPod mounted as a disk" \
    --license MIT \
    --url https://github.com/lucker14/ipod-backup \
    --package "$OUTPUT_DIR/ipod-backup_${VERSION}_all.deb" \
    --chdir "$STAGE" .

fpm \
    --input-type dir \
    --output-type rpm \
    --name ipod-backup \
    --version "$VERSION" \
    --architecture noarch \
    --depends 'python3 >= 3.10' \
    --description "Back up files from an iPod mounted as a disk" \
    --license MIT \
    --url https://github.com/lucker14/ipod-backup \
    --package "$OUTPUT_DIR/ipod-backup-${VERSION}-1.noarch.rpm" \
    --chdir "$STAGE" .

fpm \
    --input-type dir \
    --output-type apk \
    --name ipod-backup \
    --version "$VERSION" \
    --architecture noarch \
    --depends 'python3>=3.10' \
    --description "Back up files from an iPod mounted as a disk" \
    --license MIT \
    --url https://github.com/lucker14/ipod-backup \
    --package "$OUTPUT_DIR/ipod-backup-${VERSION}.apk" \
    --chdir "$STAGE" .

printf 'Packages created in %s\n' "$OUTPUT_DIR"
