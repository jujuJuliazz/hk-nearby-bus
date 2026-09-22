#!/usr/bin/env bash
# Smoke-test public HK bus ETA APIs; refresh samples/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
S="$ROOT/samples"
mkdir -p "$S"

echo "== KMB stop list (headers) =="
curl -sS -D "$S/kmb_stop.headers.txt" -o /tmp/kmb_stop_full.json \
  'https://data.etabus.gov.hk/v1/transport/kmb/stop' --http1.1
python3 - <<'PY'
import json, pathlib
d=json.load(open('/tmp/kmb_stop_full.json'))
out={k:d[k] for k in d if k!='data'}
out['_note']=f"truncated; full n={len(d.get('data') or [])}"
out['data']=(d.get('data') or [])[:5]
pathlib.Path('/workspace/hk-nearby-bus/samples/kmb_stop_list_sample.json').write_text(
  json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
PY

echo "== KMB stop-eta Mong Kok =="
curl -sS -o "$S/kmb_stop_eta_mongkok.json" \
  'https://data.etabus.gov.hk/v1/transport/kmb/stop-eta/557B9185722A07DB' --http1.1

echo "== CTB route / stop / route-stop / eta =="
curl -sS -o "$S/ctb_route_list_full.json" 'https://rt.data.gov.hk/v2/transport/citybus/route/CTB'
curl -sS -o "$S/ctb_stop_001145.json" 'https://rt.data.gov.hk/v2/transport/citybus/stop/001145'
curl -sS -o "$S/ctb_route_stop_1_outbound.json" 'https://rt.data.gov.hk/v2/transport/citybus/route-stop/CTB/1/outbound'
curl -sS -o "$S/ctb_eta_001027_route1.json" 'https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/001027/1'
curl -sS -o "$S/ctb_stop_list_missing_422.json" 'https://rt.data.gov.hk/v2/transport/citybus/stop' || true

echo "Done. See $S"
