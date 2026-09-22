#!/usr/bin/env bash
# Citybus: one route's stops → lat/lng → ETA for first stop (pattern for building geo index).
set -euo pipefail
ROUTE="${1:-1}"
DIR="${2:-outbound}"
RS=$(curl -sS "https://rt.data.gov.hk/v2/transport/citybus/route-stop/CTB/${ROUTE}/${DIR}")
STOP=$(python3 -c "import json,sys; print(json.load(sys.stdin)['data'][0]['stop'])" <<<"$RS")
echo "route=$ROUTE dir=$DIR first_stop=$STOP"
curl -sS "https://rt.data.gov.hk/v2/transport/citybus/stop/${STOP}" | python3 -m json.tool | head -20
curl -sS "https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/${STOP}/${ROUTE}" | python3 -m json.tool | head -40
