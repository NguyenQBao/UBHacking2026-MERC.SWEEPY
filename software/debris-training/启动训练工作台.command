#!/bin/zsh
set -e
cd -- "${0:A:h}"
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import ultralytics, PIL' >/dev/null 2>&1; then
    .venv/bin/python -m pip install -r requirements-train.txt
fi
echo '请在 Mac 浏览器打开 http://127.0.0.1:8090/'
echo '默认通过8091 SSH隧道取相机原图，完整步骤见仓库docs/QUICKSTART.md。'
echo '也可通过CAMERA_URL环境变量指定自己的原图接口。'
.venv/bin/python studio.py --camera-url "${CAMERA_URL:-http://127.0.0.1:8091/raw.jpg}"
