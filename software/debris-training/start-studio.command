#!/bin/zsh
set -e
cd -- "${0:A:h}"
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import ultralytics, PIL' >/dev/null 2>&1; then
    .venv/bin/python -m pip install -r requirements-train.txt
fi
echo 'Open http://127.0.0.1:8090/ in a browser on the Mac.'
echo 'The camera image comes from the 8091 SSH tunnel by default; full steps in docs/QUICKSTART.md.'
echo 'Set CAMERA_URL to use another raw-image address.'
.venv/bin/python studio.py --camera-url "${CAMERA_URL:-http://127.0.0.1:8091/raw.jpg}"
