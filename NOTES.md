# HK Nearby Bus — API research & MVP plan

Research date: 2026-09-22 (HKT). Samples under `samples/`. No deploy. Does not touch `campus-bus`.

## Summary (feasibility)

| Operator | Feasible for MVP? | Stop list + lat/lng | ETA by stop | Auth | Browser CORS |
|----------|-------------------|---------------------|-------------|------|--------------|
| **KMB / LWB** | **Yes — best fit** | Full list ✅ | All routes at stop ✅ | None | **Yes** (`Access-Control-Allow-Origin: *`) |
| **Citybus (incl. ex-NWFB)** | Yes, harder | **Per-stop only** (no bulk `/stop`) | Needs **stop + route** | None | **Yes** (`*`) |
| **NWFB standalone** | N/A | Merged into CTB since 2023-07-01; use `company_id=CTB` | same | — | — |
| data.gov.hk | Catalog only | Points at operator hosts above | same | — | — |

**Browser can call both operator APIs directly.** Verified with GET + OPTIONS. Static hosting (GitHub Pages / Cloudflare Pages) is fine for a client-only MVP — **no serverless proxy required** for these two APIs.

---

## Working endpoints (curl-verified 2026-09-22)

### KMB / LWB — base `https://data.etabus.gov.hk`

Docs: `samples/kmb_eta_api_specification.pdf`, `samples/kmb_eta_data_dictionary.pdf`  
Official dataset: https://data.gov.hk/en-data/dataset/hk-td-tis_21-etakmb

| Need | Method | URL | Notes |
|------|--------|-----|-------|
| Stop list + lat/lng | GET | `/v1/transport/kmb/stop` | ~6741 stops, ~1.2 MB JSON; `lat`/`long` strings |
| One stop | GET | `/v1/transport/kmb/stop/{stop_id}` | |
| ETA all routes at stop | GET | `/v1/transport/kmb/stop-eta/{stop_id}` | **MVP primary** |
| ETA one route@stop | GET | `/v1/transport/kmb/eta/{stop_id}/{route}/{service_type}` | |
| Route list | GET | `/v1/transport/kmb/route/` | |
| Route-stops | GET | `/v1/transport/kmb/route-stop/{route}/{outbound\|inbound}/{service_type}` | |

Example (worked):

```bash
curl -sS 'https://data.etabus.gov.hk/v1/transport/kmb/stop' --http1.1
curl -sS 'https://data.etabus.gov.hk/v1/transport/kmb/stop-eta/557B9185722A07DB' --http1.1
```

ETA fields: `route`, `dir`, `service_type`, `seq`, `dest_*`, `eta` (ISO8601 `+08:00` or null), `eta_seq`, `rmk_*`.

### Citybus (CTB; includes former NWFB) — base `https://rt.data.gov.hk`

Docs: `samples/citybus_api_spec.pdf`, `samples/citybus_data_dictionary.pdf`  
Use **V2** only (`/v2/transport/citybus/`). V1/v1.1 citybus-nwfb paths are obsolete.

| Need | Method | URL | Notes |
|------|--------|-----|-------|
| Company | GET | `/v2/transport/citybus/company/CTB` | |
| Route list | GET | `/v2/transport/citybus/route/CTB` | Works in practice (~406 routes) |
| One route | GET | `/v2/transport/citybus/route/CTB/{route}` | Spec form |
| **One stop** + lat/lng | GET | `/v2/transport/citybus/stop/{stop_id}` | **No bulk stop list** — `/stop` → HTTP 422 |
| Route-stops | GET | `/v2/transport/citybus/route-stop/CTB/{route}/{inbound\|outbound}` | |
| ETA | GET | `/v2/transport/citybus/eta/CTB/{stop_id}/{route}` | Must know route(s) at stop |

Example (worked):

```bash
curl -sS 'https://rt.data.gov.hk/v2/transport/citybus/route/CTB'
curl -sS 'https://rt.data.gov.hk/v2/transport/citybus/stop/001145'
curl -sS 'https://rt.data.gov.hk/v2/transport/citybus/route-stop/CTB/1/outbound'
curl -sS 'https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/001027/1'
```

### Auth

None for any of the above. Public open data. No API keys.

### CORS (critical)

| Host | `Access-Control-Allow-Origin` | OPTIONS |
|------|-------------------------------|---------|
| `data.etabus.gov.hk` | `*` | 204; allows GET |
| `rt.data.gov.hk` | `*` | 200; `GET,OPTIONS` |

**Implication:** Client-side `fetch()` from a static page is OK. Cloudflare/GitHub Pages cannot proxy anyway — and **we do not need a proxy** for KMB/CTB today. Revisit only if headers change or rate limits force batching server-side.

Rate limits: CTB docs mention HTTP 429. Keep ETA polls polite (e.g. 15–30s, few nearest stops).

---

## Recommended MVP architecture

**Phase 1 (ship first): KMB-only nearby stops**

1. Static page (vanilla JS or tiny Vite) on GitHub Pages / Cloudflare Pages.
2. `navigator.geolocation.getCurrentPosition`.
3. On load (or daily cache): fetch KMB `/stop` once → cache in `localStorage` / IndexedDB with date key (static data updates ~05:00 HKT).
4. Haversine filter: nearest N stops within R meters (e.g. N=8, R=400m).
5. Parallel `fetch` `/stop-eta/{id}` for those stops.
6. UI: stop name + distance; under each, routes grouped with minutes = `max(0, round((eta - now) / 60e3))`; show dest + remark; hide null `eta`.

**Phase 2: Add Citybus**

CTB has no bulk stop geo index. Build offline/once:

1. Fetch `/route/CTB`.
2. For each route × `{inbound,outbound}` → `/route-stop/...` → unique `stop` IDs.
3. Fetch `/stop/{id}` for each unique ID → `{id, name, lat, long}`.
4. Ship as static JSON asset **or** build in browser once and cache (many requests; better as build-time script).
5. For nearby CTB stops: map stop→routes from step 2, then call `/eta/CTB/{stop}/{route}` per (stop, route) pair (or throttle top routes).

**Do not** use a Pages “proxy” — it won’t work. If CORS ever breaks: Cloudflare Worker / tiny serverless proxy later.

**Out of scope for this MVP:** GMB, MTR, LRT, campus shuttle (`/workspace/campus-bus`).

---

## Prototype scripts

- `scripts/curl_smoke.sh` — curl all verified endpoints, write samples.
- `scripts/nearby_kmb_prototype.py` — given lat/lng, print nearby KMB stops + ETAs in minutes (server-side fetch; mirrors browser logic).

Run:

```bash
python3 scripts/nearby_kmb_prototype.py --lat 22.3244 --lng 114.1657 --radius 250 --limit 5
```

---

## Sample files

| File | What |
|------|------|
| `kmb_stop_list_sample.json` | First 5 of full stop list |
| `kmb_stops_near_mongkok.json` | Stops near Mong Kok |
| `kmb_stop_single.json` | One stop |
| `kmb_stop_eta_mongkok.json` | Live ETAs @ Tong Mi Rd |
| `kmb_stop_eta_chukyuen.json` | Live ETAs @ Chuk Yuen |
| `kmb_route_list_sample.json` | Route list snippet |
| `kmb_route_stop_1_outbound.json` | Route-stops |
| `ctb_*` | Company, routes, stop, route-stop, ETA, 422 on bulk `/stop` |
| `*_api_specification.pdf` / `*_data_dictionary.pdf` | Official docs |

---

## Exact endpoints that worked (checklist)

- ✅ `GET https://data.etabus.gov.hk/v1/transport/kmb/stop`
- ✅ `GET https://data.etabus.gov.hk/v1/transport/kmb/stop/{stop_id}`
- ✅ `GET https://data.etabus.gov.hk/v1/transport/kmb/stop-eta/{stop_id}`
- ✅ `GET https://data.etabus.gov.hk/v1/transport/kmb/route`
- ✅ `GET https://data.etabus.gov.hk/v1/transport/kmb/route-stop/{route}/outbound/{service_type}`
- ✅ CORS `*` on KMB (GET + OPTIONS)
- ✅ `GET https://rt.data.gov.hk/v2/transport/citybus/company/CTB`
- ✅ `GET https://rt.data.gov.hk/v2/transport/citybus/route/CTB`
- ✅ `GET https://rt.data.gov.hk/v2/transport/citybus/stop/{stop_id}`
- ✅ `GET https://rt.data.gov.hk/v2/transport/citybus/route-stop/CTB/{route}/outbound`
- ✅ `GET https://rt.data.gov.hk/v2/transport/citybus/eta/CTB/{stop_id}/{route}`
- ✅ CORS `*` on CTB (GET + OPTIONS)
- ❌ `GET https://rt.data.gov.hk/v2/transport/citybus/stop` → **422** (no bulk list)

---

## Existing WIP in this folder (left untouched)

Already present before/alongside this research (not modified by the research pass beyond adding NOTES/samples/scripts/`prototype-browser.html`):

- `index.html` — fuller KMB nearby UI (Leaflet, geolocation)
- `stops-kmb.json` — cached full KMB stop list (~6741)
- `README.md`, `.nojekyll`

Research artifacts to use: `NOTES.md`, `samples/`, `scripts/`, `prototype-browser.html`.
