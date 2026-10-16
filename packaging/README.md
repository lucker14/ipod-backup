# Packaging layout

Keep each distribution target's recipes together. User installation
instructions belong in the root [README](../README.md); release operations and
channel setup belong in [PUBLISHING.md](../PUBLISHING.md).

| Directory | Target | Current contents/status |
|---|---|---|
| `linux/` | Debian, RPM, Alpine, Arch | FPM builder creates local Linux packages; Arch recipe is development-only |
| `macos/` | Homebrew | Versioned tap formula template |
| `unix/` | macOS and Linux shell installer | Portable archive builder and release installer |
| `windows/` (planned) | Windows package managers | Current user launcher remains at repository root; add a directory when a WinGet/Chocolatey/MSI package is implemented |
| `bsd/` (planned) | FreeBSD, OpenBSD, NetBSD, DragonFly BSD | Add a directory after supported OS testing and a native recipe are available |

The Linux builder is a local-artifact tool, not a repository publisher. Release
automation belongs under `.github/workflows/`, separated by responsibility:

- `test.yml` validates unit tests on Linux, macOS, and Windows, and builds
  Linux/portable release artifacts on Linux.
- `release-packages.yml` builds and attaches release assets only.
- `publish-pypi.yml` publishes to PyPI only when its trusted-publisher setup is
  complete and explicitly enabled.

Add future APT/RPM/APK, Homebrew, AUR, WinGet, Chocolatey, or BSD publishing as
separate workflows. Each publisher should consume a verified release, have
only the credentials it needs, and stay disabled until its channel's install,
upgrade, and signature checks pass.
