# Changelog

All notable changes to this project. Versions follow [SemVer](https://semver.org/).

## [0.2.1] - 2026-11-26

### Fixed
- `scan` checks that the card grid is on screen before touching the phone; on any other
  screen (a battle, the shop…) it stops without scrolling.
- A scan that reads no cards no longer saves a snapshot.

## [0.2.0] - 2026-11-26

### Added
- Linux packages for [repo.rossmel.com](https://repo.rossmel.com/tcgp/): `ross-tcgp` for pacman,
  APT and DNF, architecture-independent, using the system's Python, Pillow, NumPy and adb.
- Release workflow that installs and runs each package on Arch, CachyOS, Ubuntu 22.04 and 24.04,
  Debian 13 and Fedora before publishing.

## [0.1.0] - 2026-11-25

### Added
- `ross-tcgp scan`: reads the whole "My Cards" grid over adb, identifies every card against
  ~4,600 reference images and reads its copy count; `--quick` only reads what's new.
- `show`, `diff` and `update` commands; JSON snapshots in `~/.local/share/ross_tcgp`.
- `scan --save-pages` / `--from-pages` to keep screenshots and re-read them offline.
