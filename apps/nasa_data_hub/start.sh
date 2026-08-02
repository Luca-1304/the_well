#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env. The app will use NASA DEMO_KEY until you add a rotated personal key."
fi

python3 -m nasa_data_hub health
exec python3 -m nasa_data_hub serve --open
