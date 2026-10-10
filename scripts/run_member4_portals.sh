#!/bin/zsh
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate
export MEMBER2_YOLO_WEIGHTS="models/member2_v2/pilot_v1/best.pt"
(sleep 2; open "http://127.0.0.1:8765/customer" "http://127.0.0.1:8765/staff") &
python -m app.server
