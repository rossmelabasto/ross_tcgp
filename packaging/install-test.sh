#!/usr/bin/env bash
# Install a built package on a clean system and use it without a phone: the command runs with
# the distro's Python, Pillow and NumPy, finds adb, refuses to scan with no device connected,
# and rebuilds a collection offline from a synthetic screenshot.
# Runs as root inside the distro's container:
#   install-test.sh <deb|rpm|arch> <package-file> <version>
set -euo pipefail
kind=$1 pkg=$(realpath "$2") version=$3

case "$kind" in
  deb)
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq "$pkg" >/dev/null
    ;;
  rpm)
    dnf install -y -q "$pkg"
    ;;
  arch)
    pacman-key --init >/dev/null 2>&1
    pacman -Syu --noconfirm >/dev/null
    pacman -U --noconfirm "$pkg" >/dev/null
    ;;
esac

echo "--- version and help"
ross-tcgp --version | tee /tmp/version
grep -q "$version" /tmp/version
ross-tcgp --help | head -3
command -v adb

echo "--- no phone connected: a clear error, not a traceback"
if ross-tcgp scan >/tmp/scan.txt 2>&1; then
  echo "scan should fail without a phone" >&2; exit 1
fi
cat /tmp/scan.txt
grep -qi 'device' /tmp/scan.txt
! grep -q 'Traceback' /tmp/scan.txt

echo "--- offline: the grid finder and digit templates work with the system libraries"
python3 -I - <<'PY'
import sys
sys.path.insert(0, "/usr/lib/ross-tcgp")
from PIL import Image, ImageDraw
from ross_tcgp import counts, grid
img = Image.new("RGB", (1080, 2340), (228, 237, 245))
d = ImageDraw.Draw(img)
for r in range(3):
    for c in range(3):
        x, y = 49 + c * 332, 900 + r * 457
        d.rectangle((x, y, x + 315, y + 439), fill=(40 + 60 * c, 90, 60 + 40 * r))
slots = grid.find_slots(img)
assert len(slots) == 9, len(slots)
assert len(counts.load_templates()) >= 10
print("grid and templates OK")
PY

echo "Install test passed on $kind"
