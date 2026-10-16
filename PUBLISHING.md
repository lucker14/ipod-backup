# Publishing and package channels

This is the maintainer guide. The [README](README.md) is for users and lists
only install routes that are available or explicitly marked as not ready.

## What the repository builds today

Publishing a GitHub Release starts
`.github/workflows/release-packages.yml`. It builds:

- Debian `.deb`, RPM `.rpm`, and Alpine `.apk` local-install packages
- `ipod-backup-portable.tar.gz` and `install.sh` for macOS/Linux-style shells
- `SHA256SUMS` for the release files

The workflow does **not** create public APT/DNF/APK feeds or sign packages.
GitHub Release downloads are not package repositories. The APK and RPM are
unsigned unless a future signing step is explicitly added and tested. Do not
publish unsigned packages to a public feed or tell users to bypass signature
verification.

## Repository map

| Path | Purpose |
|---|---|
| `pyproject.toml` | Python package metadata and installed command names |
| `packaging/linux/build-packages.sh` | Build local `.deb`, `.rpm`, and `.apk` files |
| `packaging/unix/build-portable-archive.sh` | Build the shell-installer payload |
| `packaging/unix/install.sh` | Install the portable release under a prefix |
| `Formula/ipod-backup.rb` | Homebrew development formula (`--HEAD`) |
| `packaging/macos/homebrew/ipod-backup.rb.template` | Versioned formula template for a Homebrew tap |
| `packaging/linux/arch/PKGBUILD` | Arch development recipe tracking `main` |
| `packaging/linux/arch/PKGBUILD.release.template` | Versioned AUR recipe template |
| `.github/workflows/release-packages.yml` | Build and attach GitHub Release files |
| `.github/workflows/publish-pypi.yml` | Optional PyPI trusted-publisher workflow |

`pyproject.toml` is the source of the Python package version. For a release,
the `v`-prefixed Git tag must match it (`v0.1.1` for package version `0.1.1`).
The Arch template also needs the release version and source checksum.

## First: validate and publish a GitHub Release

Tag `v0.1.0` already points at the earlier packaging commit and must not be
moved. The first release built from this cleaned-up distribution setup is
`v0.1.1`; `pyproject.toml` is set to that version. The release workflow checks
that the tag matches the project version before building.

For each release:

1. Update `pyproject.toml` to the new version. Update the fallback Arch
   `pkgver` only if you intend to build that development recipe.
2. Run the unit tests and validate each built artifact on its target OS. Do not
   advertise an OS or package format based only on a successful build.
3. Push the reviewed commit and create an annotated tag matching the package
   version, for example `v0.1.1`.
4. Create and publish the GitHub Release for that tag. This triggers the
   workflow.
5. Confirm the workflow succeeds and the release has the `.deb`, `.rpm`,
   `.apk`, portable archive, installer, and checksum manifest.
6. Install, run, upgrade, and uninstall each package on clean test systems
   before announcing it.

GitHub Actions uses the repository's built-in `GITHUB_TOKEN`; no external
secrets are needed for the current asset-building workflow.

## APT, DNF, and APK repositories

The release workflow only attaches package files; it does not publish feeds.
To offer `apt install ipod-backup`, `dnf install ipod-backup`, or `apk add
ipod-backup`, choose a package host supporting Debian, RPM, and Alpine
(Cloudsmith is one option), create public repositories, and add a separate
release-only publisher workflow. Test the host's current upload commands and
client setup instructions before adding them to the README.

Repository publishing also needs trust/signing configured and tested:

- Debian/APT repository metadata must be signed (usually handled by the host).
- RPM packages/repository trust needs a tested GPG signing key and client
  instructions.
- APK packages must be signed with a private key; clients need the matching
  public key in `/etc/apk/keys/`.

Store upload credentials and private keys only as narrowly scoped GitHub
Actions secrets. Never put credentials in a URL, workflow literal, or
pull-request job. Keep repository names and non-secret settings in Actions
variables. Do not document package-name installation until fresh install and
upgrade work on clean systems with signature verification enabled.

## Homebrew

The in-repository formula installs the development branch. To offer
`brew install`, create a public tap repository named `homebrew-ipod-backup`
under the maintainer account. For each release, take the portable archive
SHA-256 from `SHA256SUMS`, fill in `@VERSION@` and `@SHA256@` in
`packaging/macos/homebrew/ipod-backup.rb.template`, and publish it in the tap as
`Formula/ipod-backup.rb`. Run `brew audit --strict` and install/test the
formula on macOS before announcing it.

## Arch Linux

The current PKGBUILD tracks `main` and skips source verification. To publish on
AUR, fill `@VERSION@` and `@SHA256@` in
`packaging/linux/arch/PKGBUILD.release.template` using the exact tagged source
archive, build it with `makepkg --cleanbuild --syncdeps`, and publish the
resulting recipe as `ipod-backup` from an AUR account. AUR is a community
build recipe, not an official binary package feed.

## PyPI and pipx

`pipx install .` works from a source checkout. The PyPI workflow is separate
and skipped unless repository variable `PUBLISH_TO_PYPI` is exactly `true`.
To publish:

1. Create the project on PyPI.
2. Configure a PyPI Trusted Publisher for owner `lucker14`, repository
   `ipod-backup`, workflow `publish-pypi.yml`, with no environment.
3. Ensure `pyproject.toml` has the release version and set Actions variable
   `PUBLISH_TO_PYPI=true`.
4. Publish a reviewed release and verify the PyPI workflow succeeds before
   documenting `pipx install ipod-backup`.

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
