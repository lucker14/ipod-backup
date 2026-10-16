# Release and package publishing guide

This guide separates what this repository already automates from the account,
hosting, and signing setup only the maintainer can do. Replace every
`<PLACEHOLDER>` with your own value. Never commit API tokens or private signing
keys.

## Current state

Publishing a GitHub Release (using a tag such as `v1.0.0`) runs
`.github/workflows/release-packages.yml`. It builds Debian, RPM, and Alpine
packages, a portable archive, an installer script, and a SHA-256 manifest, then
attaches those files to the release.

The attached packages and checksum manifest are release downloads, **not**
APT, DNF, or APK repositories. The portable installer is for users who want an
install command without configuring a package feed. Its checksum detects
accidental corruption, but because both files are downloaded from GitHub it
does not replace a signature verified with a separately trusted public key.

## 1. One-time GitHub setup

1. Keep the repository public if you want public downloads.
2. In **Settings → Actions → General**, allow GitHub Actions to create and
   approve pull requests only if you later choose a workflow that updates a
   separate tap/AUR repository. The current release workflow only needs the
   built-in `GITHUB_TOKEN` with Contents: read and write; that permission is
   already declared in the workflow.
3. Protect `main`: require review and passing checks, and restrict who can
   create/publish version tags and GitHub Releases.
4. Never publish a release from an unreviewed tag. A release triggers package
   creation and makes the installer-visible artifacts public.

No GitHub secret is needed for the default GitHub Release build. The optional
Cloudsmith upload requires the secret and variables described below.

## 2. Releasing and checking the install artifacts

1. Update the project version in `pyproject.toml` and the default version in
   `packaging/arch/PKGBUILD` to the release version.
2. Run the unit tests, build/check packages on clean supported Linux systems,
   and review the release diff.
3. Create and push an annotated tag, then create a GitHub Release for that tag:

   ```sh
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

   Create/publish the GitHub Release for `v1.0.0` in GitHub's Releases UI (or
   `gh release create v1.0.0 --generate-notes`). Publishing the release starts
   the workflow.
4. Wait for **Build release packages** to pass. Confirm the release has:
   `ipod-backup_<version>_all.deb`, `ipod-backup-<version>-1.noarch.rpm`,
   `ipod-backup-<version>.apk`, `ipod-backup-portable.tar.gz`, `install.sh`,
   and `SHA256SUMS`. If RPM/APK signing is enabled, it also has
   `RPM-GPG-KEY` and/or `ipod-backup.rsa.pub`.
5. Test package installation/removal on clean Debian/Ubuntu, Fedora/RHEL, and
   Alpine systems before announcing the release. Until signing is configured,
   the FPM-generated RPM/APK are unsigned and suitable only for explicit local
   testing. Test the APK signature path before using APK in a repository.

The package workflows currently use Python `>=3.10`. Check that the OS
releases you advertise provide that version before publishing a package feed.

## 3. Optional curl installer

The release includes a portable archive and installer. Users can first
download, inspect, then run it:

```sh
curl -fsSLO https://github.com/lucker14/ipod-backup/releases/latest/download/install.sh
less install.sh
sh install.sh --user
```

Or install the latest published version in one command:

```sh
curl -fsSL https://github.com/lucker14/ipod-backup/releases/latest/download/install.sh | sh -s -- --user
```

`--user` installs under `~/.local`; the user may need to add `~/.local/bin` to
`PATH`. A system-wide install defaults to `/usr/local`; download and inspect
the script, then run `sudo sh install.sh`. A specific version can be selected
with `--version 1.0.0`. The installer supports Unix-like systems with `sh`,
`curl`, `tar`, and Python 3.10+. It verifies the portable archive against the
release's `SHA256SUMS` before installing. The feed/package-manager route below
is preferable for managed machines. Re-running the installer replaces that
version only when it was previously installed by this script; older version
directories remain available for rollback.

## 4. APT, DNF, and APK package repositories

### Recommended hosted-repository approach

Choose a hosted service that explicitly supports **Debian/APT, RPM/DNF, and
Alpine/APK**, for example Cloudsmith. Create one public repository per package
format there; the provider hosts indexes/metadata and documents the client
setup for each OS. Other services are fine if they support all the formats
and signing model you need.

Record these values somewhere private/controlled (the names below are examples,
not configured values):

| Value | Example placeholder | Used for |
|---|---|---|
| Account/namespace | `<PACKAGE_REPO_OWNER>` | Repository owner on the hosting service |
| Debian repository | `<DEB_REPOSITORY>` | APT package upload and client source |
| RPM repository | `<RPM_REPOSITORY>` | DNF package upload and client repo file |
| Alpine repository | `<APK_REPOSITORY>` | APK package upload and client repository |
| Debian distribution/component | `<DEB_DISTRO>` / `<DEB_COMPONENT>` | APT repository layout |
| RPM distribution/release | `<RPM_DISTRO>` | RPM repository layout |
| Alpine version/branch | `<ALPINE_VERSION>` / `<ALPINE_BRANCH>` | APK repository layout |
| Upload credential | GitHub Actions secret `CLOUDSMITH_API_KEY` | CI upload only; never a client install secret |

Then:

1. Enable repository metadata/package signing in the provider. Obtain the
   provider's **public** client configuration and key-install instructions.
   The public signing key may be committed/served; the private key or upload
   token must not be.
2. For RPM signing, generate a dedicated GPG signing key and export its
   **unencrypted** armored private key. Add it as the Actions secret
   `RPM_SIGNING_PRIVATE_KEY` and set `RPM_SIGNING_KEY_ID` to its key ID in
   Actions variables. The workflow imports it only for the protected release,
   signs the RPM, verifies it, and attaches `RPM-GPG-KEY` to the release.
   Keep the signing key backed up offline and never reuse a personal key.
   `SIGN_RPM_RELEASE=true` enables signing even when repository publishing is
   not enabled.

   Example key creation/export on a trusted maintainer computer:

   ```sh
   gpg --batch --pinentry-mode loopback --passphrase '' \
     --quick-generate-key "iPod Backup RPM Signing <YOUR_EMAIL>" rsa4096 sign 0
   gpg --list-secret-keys --keyid-format=long
   gpg --armor --export-secret-keys <RPM_SIGNING_KEY_ID>
   ```

   Copy the final command's output directly into the GitHub Actions secret;
   do not save it in this repository.
3. For APK signing, generate a dedicated RSA key named `ipod-backup.rsa` and
   add its PEM private key as the Actions secret `APK_SIGNING_PRIVATE_KEY`.
   `SIGN_APK_RELEASE=true` makes the release workflow sign the APK in Alpine
   and attach `ipod-backup.rsa.pub` to the release. Install that public key on
   Alpine clients under `/etc/apk/keys/` before enabling the repository. Keep
   the private key backed up offline. Never set the APK publication variable
   until this signing path has been tested.

   Example key creation on a trusted maintainer computer:

   ```sh
   openssl genrsa -out ipod-backup.rsa 4096
   openssl rsa -in ipod-backup.rsa -pubout -out ipod-backup.rsa.pub
   ```

   Copy the private key PEM into the Actions secret; publish only the `.pub`
   key. Do not put either key in a pull-request artifact.
4. Create a narrowly scoped Cloudsmith API key with upload access to those
   repositories. Add it to **Repository Settings → Secrets and variables →
   Actions → Secrets** as `CLOUDSMITH_API_KEY`. Do not use a read/write
   all-repositories key if narrower repository permissions are available.
5. In **Actions → Variables**, set `CLOUDSMITH_OWNER` to your namespace and
   `CLOUDSMITH_CLI_VERSION` to a tested, pinned Cloudsmith CLI version. To
   publish Debian packages, also set `PUBLISH_TO_CLOUDSMITH=true` and
   `CLOUDSMITH_DEB_REPO=<debian repo name>`. To publish RPMs, first set
   `SIGN_RPM_RELEASE=true`, confirm the signed release package/key installs
   successfully, then set `PUBLISH_CLOUDSMITH_RPM=true` and
   `CLOUDSMITH_RPM_REPO=<rpm repo name>`. To publish Alpine packages, first
   set `SIGN_APK_RELEASE=true`, confirm `apk add` with the published public key
   on a clean Alpine system, then set `PUBLISH_CLOUDSMITH_APK=true` and
   `CLOUDSMITH_APK_REPO=<alpine repo name>`.
6. Test install and upgrade from the provider's signed client configuration
   on a clean VM/container for every OS family and release you claim to
   support.
7. Add the provider-generated client repository configuration commands below
   to the README, replacing all placeholders and linking to the public
   signing-key instructions. Do not copy a made-up key or repository URL.

Client-side documentation should ultimately contain provider-generated
commands in this shape (these are **not** runnable until filled with the
provider's real values):

```sh
# APT: install the provider's signing key/configuration, then:
sudo apt update
sudo apt install ipod-backup

# DNF: install or enable the provider's .repo configuration, then:
sudo rpm --import https://github.com/lucker14/ipod-backup/releases/latest/download/RPM-GPG-KEY
sudo dnf install ipod-backup

# APK: install/trust the provider's public signing key and configure its repo:
curl -fsSL https://github.com/lucker14/ipod-backup/releases/latest/download/ipod-backup.rsa.pub \
  | sudo tee /etc/apk/keys/ipod-backup.rsa.pub >/dev/null
sudo apk update
sudo apk add ipod-backup
```

Do not tell users to use `--allow-untrusted` for a public APK repository.
Public APK packages/indexes need a working trust setup. Without the signing
secrets and variables above, the release APK remains unsigned and cannot be
published to the public Cloudsmith Alpine feed.

### Alternative: host repositories yourself

You can instead host signed APT, RPM, and APK repositories on infrastructure
you control. This means operating their metadata generators, repository
signing keys, key rotation, immutable/versioned publication, and availability.
Do not expose signing secrets to pull-request workflows. Only publish from a
protected release workflow after reviewing the tagged source. Prefer a
specialist package host unless you already operate these services.

## 5. Homebrew tap (macOS)

Homebrew needs a separate public tap repository; the in-repository formula is
currently a development (`--HEAD`) recipe, not a versioned formula ready for
`brew install`.

1. Create a public repository named `homebrew-ipod-backup` under your GitHub
   account. Its tap name will be `lucker14/ipod-backup`.
2. Download the release's `SHA256SUMS`, get the hash for
   `ipod-backup-portable.tar.gz`, and replace `@VERSION@` and `@SHA256@` in
   `packaging/homebrew/ipod-backup.rb.template`. Copy the completed formula to
   the tap repository as `Formula/ipod-backup.rb`.
3. Test it with `brew audit --strict --online Formula/ipod-backup.rb` and
   `brew install --build-from-source <formula>` on macOS.
4. Users can then install using:

   ```sh
   brew tap lucker14/ipod-backup
   brew install ipod-backup
   ```

For automatic tap updates, create a narrowly scoped GitHub token that can
write **only** to `lucker14/homebrew-ipod-backup`, save it as
`HOMEBREW_TAP_TOKEN`, and add a release-only workflow that updates the
versioned formula. Do not use a personal all-repositories token if a
fine-grained token can be used. Until that workflow is configured, update the
tap manually per release.

## 6. Arch Linux / AUR

The current `packaging/arch/PKGBUILD` is a development starting point: it
tracks `main` and skips source checksum verification. For each release:

1. Replace `@VERSION@` and `@SHA256@` in
   `packaging/arch/PKGBUILD.release.template`. Calculate the source archive
   checksum from the exact tagged archive, not from an unchecked branch, and
   copy the completed file to the AUR checkout as `PKGBUILD`.
2. Build and inspect it with `makepkg --cleanbuild --syncdeps`.
3. Create an AUR account and publish the package as `ipod-backup` using the
   AUR SSH key and documented AUR Git workflow.
4. Update AUR metadata on every release. Never put the AUR private SSH key in
   the source repository. If automating, store a dedicated deploy key as an
   Actions secret and limit it to the AUR publishing workflow.

Users then install from AUR using their preferred AUR helper; AUR is a
community build recipe, not an official binary repository.

## 7. Python package index (optional)

The project has `pyproject.toml` console-script metadata and can be installed
from a checkout with `pipx install .`. A release workflow is prepared in
`.github/workflows/publish-pypi.yml`; it is skipped unless the repository
variable `PUBLISH_TO_PYPI` is exactly `true`.

To enable it:

1. Create the project on PyPI and set its **Trusted Publisher** to owner
   `lucker14`, repository `ipod-backup`, workflow
   `publish-pypi.yml`, environment blank.
2. Update `pyproject.toml`'s version before each tagged release.
3. In GitHub **Settings → Secrets and variables → Actions → Variables**, set
   `PUBLISH_TO_PYPI` to `true`.
4. Publish a reviewed release and confirm the PyPI workflow succeeds. Users
   can then run `pipx install ipod-backup` or `python3 -m pip install
   ipod-backup`.

For a first test, configure TestPyPI as a separate trusted publisher and
temporarily target it from a separate workflow/configuration. Do not create or
commit a PyPI API token when trusted publishing is available.

## 8. Windows

The existing `start_ipod_backup.bat` launcher remains the supported
no-package-manager Windows install. Once the PyPI workflow is enabled, users
can also install the console commands with `pipx` from PowerShell:

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
py -m pipx install ipod-backup
```

There is no MSI, WinGet, or Chocolatey package configured. Those require a
separate Windows packaging/release route; do not present them as available
until a manifest/package and update process are published and tested.

## Maintainer completion checklist

- [ ] Decide the package-hosting service and create public APT, RPM, and APK
      repositories.
- [ ] Configure Debian repository signing and create dedicated RPM/APK signing
      keys. Add only the private signing keys and upload token as Actions
      secrets; test signing and client trust before advertising installs.
- [ ] Set the Cloudsmith repository variables and enable each upload toggle
      only after signing and client installation have passed on clean systems.
- [ ] Create the Homebrew tap and publish a versioned, audited formula.
- [ ] Decide whether to maintain an AUR package and pin its source/checksum.
- [ ] Decide whether to publish to PyPI.
- [ ] Add real provider-specific client setup instructions to the README.
- [ ] Publish a test release and verify fresh install, upgrade, and uninstall
      on each advertised OS.
- [ ] Replace every placeholder in this guide before presenting those channels
      as available. Keep credentials and private keys out of the guide.
