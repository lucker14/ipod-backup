#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 DEB_DIRECTORY OUTPUT_DIRECTORY" >&2
    exit 2
fi

DEB_DIRECTORY=$1
OUTPUT_DIRECTORY=$2
: "${APT_REPO_SIGNING_KEY:?Set APT_REPO_SIGNING_KEY to an armored private key}"
: "${APT_REPO_SIGNING_KEY_PASSPHRASE:?Set APT_REPO_SIGNING_KEY_PASSPHRASE}"

for command_name in apt-ftparchive dpkg-scanpackages gpg gzip; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: $command_name" >&2
        exit 1
    fi
done

if [[ -e "$OUTPUT_DIRECTORY" ]] && [[ -n "$(find "$OUTPUT_DIRECTORY" -mindepth 1 -print -quit)" ]]; then
    echo "Output directory must be empty: $OUTPUT_DIRECTORY" >&2
    exit 1
fi

shopt -s nullglob
packages=("$DEB_DIRECTORY"/*.deb)
if [[ ${#packages[@]} -eq 0 ]]; then
    echo "No Debian packages found in $DEB_DIRECTORY" >&2
    exit 1
fi

temporary_gnupg_home=$(mktemp -d)
chmod 700 "$temporary_gnupg_home"
trap 'rm -rf "$temporary_gnupg_home"' EXIT
export GNUPGHOME=$temporary_gnupg_home

printf '%s\n' "$APT_REPO_SIGNING_KEY" | gpg --batch --import
key_fingerprint=$(gpg --batch --with-colons --list-secret-keys |
    awk -F: '$1 == "fpr" { print $10; exit }')
if [[ -z "$key_fingerprint" ]]; then
    echo "No private signing key was imported" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIRECTORY/pool/main/i/ipod-backup"
cp -- "${packages[@]}" "$OUTPUT_DIRECTORY/pool/main/i/ipod-backup/"
mkdir -p "$OUTPUT_DIRECTORY/dists/stable/main"

(
    cd "$OUTPUT_DIRECTORY"
    dpkg-scanpackages --arch all pool /dev/null > Packages
    for architecture in amd64 arm64 armhf i386 ppc64el riscv64 s390x; do
        index_directory="dists/stable/main/binary-$architecture"
        mkdir -p "$index_directory"
        cp Packages "$index_directory/Packages"
        gzip -n -9c Packages > "$index_directory/Packages.gz"
    done
    apt-ftparchive \
        -o APT::FTPArchive::Release::Origin="iPod Backup" \
        -o APT::FTPArchive::Release::Label="iPod Backup" \
        -o APT::FTPArchive::Release::Suite=stable \
        -o APT::FTPArchive::Release::Codename=stable \
        -o APT::FTPArchive::Release::Architectures="amd64 arm64 armhf i386 ppc64el riscv64 s390x" \
        -o APT::FTPArchive::Release::Components=main \
        -o APT::FTPArchive::Release::Description="iPod Backup APT repository" \
        release dists/stable > dists/stable/Release
)

gpg --batch --yes --export "$key_fingerprint" > "$OUTPUT_DIRECTORY/archive-keyring.gpg"
gpg --batch --yes --pinentry-mode loopback \
    --passphrase "$APT_REPO_SIGNING_KEY_PASSPHRASE" \
    --local-user "${key_fingerprint}!" \
    --clearsign \
    --output "$OUTPUT_DIRECTORY/dists/stable/InRelease" \
    "$OUTPUT_DIRECTORY/dists/stable/Release"
gpg --batch --yes --pinentry-mode loopback \
    --passphrase "$APT_REPO_SIGNING_KEY_PASSPHRASE" \
    --local-user "${key_fingerprint}!" \
    --armor \
    --detach-sign \
    --output "$OUTPUT_DIRECTORY/dists/stable/Release.gpg" \
    "$OUTPUT_DIRECTORY/dists/stable/Release"

cat > "$OUTPUT_DIRECTORY/index.html" <<'EOF'
<!doctype html>
<html lang="en">
  <meta charset="utf-8">
  <title>iPod Backup APT repository</title>
  <h1>iPod Backup APT repository</h1>
  <p>Signed Debian packages for Debian and Ubuntu are available through APT.</p>
</html>
EOF
