#!/usr/bin/env bash
# Free, no-card way to expose your local backend so the live Cloudflare page
# can reach it. Requires: cloudflared (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
set -euo pipefail
cd "$(dirname "$0")"

pip install -r requirements.txt

# 1) Fill in configs/default.env first (see configs.example.env)
if [ ! -f configs/default.env ]; then
  echo "Missing configs/default.env — copy configs.example.env and fill in SESSION_ID first."
  exit 1
fi

# 2) Optional API key guard
export API_KEY="${API_KEY:-}"

# 3) Start the API locally, then expose it with a free Cloudflare quick tunnel
python webapp.py &
APP_PID=$!
sleep 3
cloudflared tunnel --url http://localhost:5000

kill $APP_PID 2>/dev/null || true
