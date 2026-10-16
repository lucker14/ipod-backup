# Publishing and package channels

This is the maintainer guide. The [README](README.md) is for users and lists
only install routes that are available or explicitly marked as not ready.

## What the repository builds today

Publishing a GitHub Release starts
`.github/workflows/release-packages.yml`. It builds:

- Debian `.deb`, RPM `.rpm`, and Alpine `.apk` local-install packages
- `ipod-backup-portable.tar.gz` and `install.sh` for macOS/Linux-style shells
- `SHA256SUMS` for the release files

GitHub Release downloads are not package repositories. The Debian and Fedora
packages previously uploaded to Cloudsmith are on a time-limited trial feed;
they are not the permanent distribution channel. The release workflow now
supports a signed, project-owned Debian/Ubuntu APT repository on GitHub Pages.
Do not advertise package-name installs until that feed is deployed and tested.
The RPM and APK files attached to GitHub Releases are unsigned.

## Repository map

| Path | Purpose |
|---|---|
| `src/ipod_backup/` | Installable Python package and application entry points |
| `tests/` | Unit tests |
| `scripts/launchers/` | Beginner-friendly Windows, macOS, and Linux launchers |
| `pyproject.toml` | Python package metadata and installed command names |
| `packaging/linux/build-packages.sh` | Build local `.deb`, `.rpm`, and `.apk` files |
| `packaging/linux/apt/build-repository.sh` | Create a signed APT repository from Debian packages |
| `packaging/unix/build-portable-archive.sh` | Build the shell-installer payload |
| `packaging/unix/install.sh` | Install the portable release under a prefix |
| `packaging/macos/homebrew/ipod-backup.rb` | Homebrew development formula (`--HEAD`) |
| `packaging/macos/homebrew/ipod-backup.rb.template` | Versioned formula template for a Homebrew tap |
| `packaging/macos/homebrew/tap/` | Source for the separate `lucker14/homebrew-ipod-backup` tap |
| `packaging/linux/arch/PKGBUILD` | Arch development recipe tracking `main` |
| `packaging/linux/arch/PKGBUILD.release.template` | Versioned AUR recipe template |
| `.github/workflows/release-packages.yml` | Build and attach release files; optionally deploy the signed APT feed |
| `.github/workflows/publish-pypi.yml` | Optional PyPI trusted-publisher workflow |

`pyproject.toml` is the source of the Python package version. For a release,
the `v`-prefixed Git tag must match it. The Arch template also needs the
release version and source checksum.

## Current release

Release `v0.1.2` is published at
https://github.com/lucker14/ipod-backup/releases/tag/v0.1.2. Its package-build
workflow succeeded and attached the portable archive, installer, checksums,
and local `.deb`, `.rpm`, and `.apk` artifacts. The PyPI workflow was skipped
because trusted publishing is not configured. Tags `v0.1.0`, `v0.1.1`, and
`v0.1.2` must not be moved.

## Preparing the next GitHub Release

For each release:

1. Update `pyproject.toml` to the new version. Update the fallback Arch
   `pkgver` only if you intend to build that development recipe.
2. Run the unit tests and validate each built artifact on its target OS. Do not
   advertise an OS or package format based only on a successful build.
3. Push the reviewed commit and create an annotated tag matching the package
   version, for example `v0.1.3`.
4. Create and publish the GitHub Release for that tag. This triggers the
   workflow.
5. Confirm the workflow succeeds and the release has the `.deb`, `.rpm`,
   `.apk`, portable archive, installer, and checksum manifest.
6. Install, run, upgrade, and uninstall each package on clean test systems
   before announcing it.

GitHub Actions uses the repository's built-in `GITHUB_TOKEN`; no external
secrets are needed for the current asset-building workflow.

## Debian and Ubuntu APT repository

The project-owned APT feed is built from the `.deb` produced by
`.github/workflows/release-packages.yml` and deployed to the public GitHub Pages
site at `https://lucker14.github.io/ipod-backup/`. This is a signed project
repository, not the Debian or Ubuntu distribution archive. Hosting uses the
public GitHub Pages site; no package-hosting vendor account is required.

### One-time setup

1. Create a dedicated OpenPGP signing key for the repository. Keep its
   passphrase; do not use a personal key or share the private key in chat or
   source control:

   ```sh
   gpg --quick-generate-key "iPod Backup APT Repository" ed25519 sign 0
   gpg --list-secret-keys --keyid-format long
   gpg --armor --export-secret-keys FINGERPRINT > apt-repo-signing-key.asc
   ```

2. In GitHub repository Settings → Pages, set the build and deployment source
   to **GitHub Actions**.
3. In Settings → Secrets and variables → Actions → Secrets, add
   `APT_REPO_SIGNING_KEY` with the contents of the armored private-key file and
   `APT_REPO_SIGNING_KEY_PASSPHRASE` with its passphrase. Never commit either.
4. Keep the repository variable `APT_REPO_PUBLISH` unset or `false` until the
   first deployment is ready. The workflow only deploys when this variable is
   exactly `true`.

### First deployment and verification

1. Set `APT_REPO_PUBLISH=true` in Settings → Secrets and variables → Actions →
   Variables.
2. Run **Build release packages** manually from the `main` branch with
   `release_tag=v0.1.2`. This rebuilds the tagged Debian package and deploys
   the signed feed without replacing the existing GitHub Release assets.
3. Confirm these URLs are available:
   `https://lucker14.github.io/ipod-backup/dists/stable/InRelease` and
   `https://lucker14.github.io/ipod-backup/pool/main/i/ipod-backup/ipod-backup_0.1.2_all.deb`.
   The published `archive-keyring.gpg` is the public key; compare its
   fingerprint against the key you created before trusting it.
4. On clean Debian and Ubuntu test systems, install the key and source:

   ```sh
   sudo install -d -m 0755 /etc/apt/keyrings
   curl -fsSL https://lucker14.github.io/ipod-backup/archive-keyring.gpg \
     | sudo tee /etc/apt/keyrings/ipod-backup.gpg >/dev/null
   echo "deb [signed-by=/etc/apt/keyrings/ipod-backup.gpg] https://lucker14.github.io/ipod-backup/ stable main" \
     | sudo tee /etc/apt/sources.list.d/ipod-backup.list
   sudo apt update
   sudo apt install ipod-backup
   ```

5. Verify `apt update` validates the signed Release metadata without disabling
   signature checks. Test running the installed commands and an upgrade before
   adding these instructions to the user README.

After setup, each published GitHub Release deploys its `.deb` when
`APT_REPO_PUBLISH=true`. The repository currently retains the package from the
latest deployment; it is not an archive for pinning old versions.

### Temporary Cloudsmith trial

The v0.1.2 Debian package and Fedora RPM were also manually uploaded to a
Cloudsmith trial repository. They are not the recommended or maintained
install route. The billing page showed an Ultra trial billed at $0.00, no
payment method, and stated that no charge occurs unless the workspace is
upgraded. Do not upgrade or add a payment method for this project feed.

## RPM and Alpine packages

The GitHub Release includes local `.rpm` and `.apk` artifacts, but they are
unsigned and should not be installed by bypassing package verification. The
v0.1.2 RPM was manually placed in the temporary Cloudsmith trial feed; the APK
upload failed processing. Neither DNF nor APK is a maintained package
repository. Keep these channels marked unavailable until a sustainable,
signed feed and clean-system install/upgrade tests are in place.

## Homebrew

The public tap is `lucker14/homebrew-ipod-backup`; its formula and README are
maintained in `packaging/macos/homebrew/tap/` and published from that subtree.
Users install it with:

```sh
brew tap lucker14/ipod-backup
brew install ipod-backup
```

On Homebrew versions that block untrusted taps, inspect the formula and then
explicitly trust it if Homebrew prompts:

```sh
brew trust --formula lucker14/ipod-backup/ipod-backup
```

For each release, take the portable archive SHA-256 from `SHA256SUMS`, update
the URL, version, and checksum in `tap/Formula/ipod-backup.rb`, and publish the
subtree to the tap's `main` branch. The source checkout's development formula
is `packaging/macos/homebrew/ipod-backup.rb`; the versioned formula template
is `packaging/macos/homebrew/ipod-backup.rb.template`. Audit and test formulas
on macOS before announcing a new version.

## Arch Linux

A version-pinned AUR recipe and matching `.SRCINFO` for v0.1.2 are prepared in
`packaging/linux/arch/aur/`. The source archive checksum is verified. Before
publishing, validate with `makepkg --printsrcinfo`,
`makepkg --cleanbuild --syncdeps`, and `namcap` on Arch Linux, then push the two
files to the AUR `ipod-backup` repository from an authorized maintainer
account. AUR is a community build recipe, not an official binary package feed.
The AUR package name was available when checked; the current Mac did not have
a trusted AUR SSH host key, so it was not pushed.

## PyPI and pipx

The `ipod-backup` name was not registered on PyPI when checked. The workflow
supports PyPI's pending Trusted Publisher flow, so a first manual upload can
create the project without a long-lived token:

1. In the PyPI account's Publishing settings, add a pending GitHub Actions
   publisher for project `ipod-backup`, owner `lucker14`, repository
   `ipod-backup`, workflow `publish-pypi.yml`, with no environment.
2. Set the GitHub Actions repository variable `PUBLISH_TO_PYPI` to the exact
   value `true`.
3. Manually run **Publish to PyPI** from the `main` branch with release tag
   `v0.1.2`. This first upload creates the PyPI project and publishes the
   existing version. For later releases, the published GitHub Release
   automatically triggers PyPI publishing.
4. Verify the workflow succeeds and `pipx install ipod-backup` works before
   adding PyPI as an available route in the user README.

Do not create a long-lived PyPI token when trusted publishing is available.

## Windows, BSD, and other package managers

Windows currently has a `.bat` launcher for a source checkout; there is no
WinGet, Chocolatey, or MSI package yet. FreeBSD, OpenBSD, NetBSD, and DragonFly
BSD have no tested package or automatic volume-discovery support yet. Test
Python installation, device discovery, and backup on each target before
claiming support. Then choose an appropriate native route (for example,
FreeBSD Ports/pkg, OpenBSD ports/packages, WinGet, or Chocolatey) and add its
maintainer and release process here.

The portable shell installer is not a replacement for native packages on
BSD or Windows. It is intended for macOS and Linux; platform-specific install
routes must be tested separately.

## Before announcing a channel

- [ ] The package is built from the reviewed release tag and correct version.
- [ ] Fresh install, basic command, upgrade, and uninstall work on a clean
      supported OS.
- [ ] Signatures and trust setup are enabled for public package feeds.
- [ ] User documentation contains the real install commands and prerequisites.
- [ ] The package channel has a maintainer who will publish future updates.
