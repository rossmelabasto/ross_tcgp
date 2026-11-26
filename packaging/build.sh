#!/usr/bin/env bash
# Build the deb, rpm and pacman packages of ross-tcgp for repo.rossmel.com.
#
# ross_tcgp is pure Python and only needs Pillow, NumPy and adb, which every distro packages,
# so one architecture-independent package uses the system's Python and libraries:
#
#   /usr/lib/ross-tcgp/ross_tcgp   the Python package
#   /usr/bin/ross-tcgp             the command
#
#   packaging/build.sh <version> <out-dir>      (needs nfpm and envsubst)
set -euo pipefail

version=${1:?version}
out=$(realpath -m "${2:?out-dir}")
root=$(cd "$(dirname "$0")/.." && pwd)

installed=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$root/src/ross_tcgp/__init__.py")
[ "$installed" = "$version" ] || { echo "version mismatch: package says $installed, building $version" >&2; exit 1; }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
stage="$work/stage"
mkdir -p "$stage/usr/lib/ross-tcgp" "$stage/usr/bin" "$out"

cp -r "$root/src/ross_tcgp" "$stage/usr/lib/ross-tcgp/"
find "$stage" -name '__pycache__' -type d -prune -exec rm -rf {} +

# -I keeps the user's environment (PYTHONPATH, ~/.local packages) out of it; the package path is
# added by hand because -I also ignores PYTHONPATH.
cat > "$stage/usr/bin/ross-tcgp" <<'SH'
#!/bin/sh
exec /usr/bin/python3 -I -c 'import sys; sys.path.insert(0, "/usr/lib/ross-tcgp"); from ross_tcgp.cli import main; sys.exit(main())' "$@"
SH
chmod 755 "$stage/usr/bin/ross-tcgp"
install -Dm644 "$root/LICENSE" "$stage/usr/share/licenses/ross-tcgp/LICENSE"
install -Dm644 "$root/README.md" "$stage/usr/share/doc/ross-tcgp/README.md"

for packager in deb rpm archlinux; do
  # nfpm doesn't expand variables in file paths: fill the config in first.
  VERSION="$version" STAGE="$stage" envsubst '${VERSION} ${STAGE}' \
    < "$root/packaging/nfpm.yaml" > "$work/nfpm.yaml"
  nfpm package --config "$work/nfpm.yaml" --packager "$packager" --target "$out/"
done
ls -la "$out"
