# Contributing

Thanks for helping! Issues and pull requests are welcome, in English or Spanish.

- **It doesn't work on my phone:** open an issue with your phone model, screen
  resolution (`adb shell wm size`) and, if you can, a scan with
  `ross-tcgp scan --save-pages pages/` (attach one or two screenshots).
- **Setup:** `python -m venv .venv && .venv/bin/pip install -e ".[dev]"`, then
  `.venv/bin/pytest`. Tests use synthetic images only: never commit game
  screenshots or card images.
- **Changing the recognition:** keep a folder of saved pages and re-run
  `ross-tcgp scan --from-pages DIR`: the total must still match the game's.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`…); versions follow SemVer.
- **Releases:** bump `__version__` and `pyproject.toml`, add the CHANGELOG entries
  (`CHANGELOG.md` and `CHANGELOG.es.md`), push to a `release-test/…` branch to
  run the package tests, then tag `vX.Y.Z`.
