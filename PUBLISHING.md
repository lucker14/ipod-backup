# Publishing and package channels

This is the maintainer guide. The [README](README.md) is for users and lists
only install routes that are available or explicitly marked as not ready.

## What the repository builds today

Publishing a GitHub Release starts
`.github/workflows/release-packages.yml`. It builds:

- Debian `.deb`, RPM `.rpm`, and Alpine `.apk` local-install packages
- `ipod-backup-portable.tar.gz` and `install.sh` for macOS/Linux-style shells
- `SHA256SUMS` for the release files

GitHub Release downloads are not package repositories. The release workflow
has a Cloudsmith publisher, but it is disabled until repository settings,
OIDC trust, and package-manager signature verification are configured and
tested. Do not enable it or advertise package-name installs before that work
is complete. The RPM and APK files attached to GitHub Releases are unsigned;
that local-download status does not change when repository publishing is
enabled.

## Repository map

| Path | Purpose |
|---|---|
| `src/ipod_backup/` | Installable Python package and application entry points |
| `tests/` | Unit tests |
| `scripts/launchers/` | Beginner-friendly Windows, macOS, and Linux launchers |
| `pyproject.toml` | Python package metadata and installed command names |
| `packaging/linux/build-packages.sh` | Build local `.deb`, `.rpm`, and `.apk` files |
| `packaging/unix/build-portable-archive.sh` | Build the shell-installer payload |
| `packaging/unix/install.sh` | Install the portable release under a prefix |
| `packaging/macos/homebrew/ipod-backup.rb` | Homebrew development formula (`--HEAD`) |
| `packaging/macos/homebrew/ipod-backup.rb.template` | Versioned formula template for a Homebrew tap |
| `packaging/macos/homebrew/tap/` | Source for the separate `lucker14/homebrew-ipod-backup` tap |
| `packaging/linux/arch/PKGBUILD` | Arch development recipe tracking `main` |
| `packaging/linux/arch/PKGBUILD.release.template` | Versioned AUR recipe template |
| `.github/workflows/release-packages.yml` | Build and attach GitHub Release files |
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

## APT, DNF, and APK repositories

Cloudsmith publishing is prepared in `.github/workflows/release-packages.yml`
and is opt-in. It publishes the Debian, RPM, and Alpine packages from the
successful package-build job. The workflow also supports manually rebuilding
an existing tag through `workflow_dispatch` (for example, `v0.1.2`) to
publish to Cloudsmith without replacing the existing GitHub Release assets.

Current Cloudsmith setup for workspace `lucker14`:

- The multi-format repository `ipod-backup-deb` exists and has a **Public
  broadcast**. It currently contains no packages.
- The `ipod-backup-release-publisher` service account and GitHub Actions OIDC
  provider have been created. The service account has **Write** access to
  `ipod-backup-deb` only.
- The active OIDC provider is restricted to `lucker14/ipod-backup` and the
  `.github/workflows/release-packages.yml` workflow file. Its ref wildcard
  permits that workflow on any branch or tag.
- The automatically generated service API key has been rotated. OIDC is the
  intended authentication method; do not use or store the replacement API key.
- No packages have been published, and `CLOUDSMITH_PUBLISH` must remain unset
  or `false`. The README must not advertise `apt install`, `dnf install`, or
  `apk add` by package name until publication and clean-client testing pass.

Finish setup in this order:

1. Configure repository/package signing and obtain the repository setup
   instructions for Debian/Ubuntu, an RPM-based distribution, and Alpine.
   Keep client-side signature verification enabled.
2. In GitHub repository Settings → Secrets and variables → Actions → Variables,
   set `CLOUDSMITH_NAMESPACE=lucker14`,
   `CLOUDSMITH_SERVICE_ACCOUNT=ipod-backup-release-publisher`, and
   `CLOUDSMITH_REPOSITORY=ipod-backup-deb`. Leave `CLOUDSMITH_PUBLISH` unset
   or `false` until ready to make the packages public.
3. When ready, set `CLOUDSMITH_PUBLISH` to the exact value `true` and manually
   run the workflow with `v0.1.2` (select the `main` workflow branch). This
   immediately publishes the packages to the public broadcast.
4. Verify the public feed instructions, fresh installs, upgrades, and package
   signatures on Debian/Ubuntu, an RPM-based distribution, and Alpine. If any
   verification fails, set `CLOUDSMITH_PUBLISH` back to `false` and do not
   advertise package-name installs until the issue is resolved.
5. Update the user README with the verified feed setup and install commands
   only after all three package-manager tests pass.

The workflow uses Cloudsmith's official
[GitHub Actions/OIDC integration](https://docs.cloudsmith.com/integrations/integrating-with-github-actions).
Package upload commands use Cloudsmith's Debian, RPM, and Alpine repository
formats. Keep repository names and other non-secret settings in Actions
variables, never in credentials embedded in URLs or workflow literals.

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
