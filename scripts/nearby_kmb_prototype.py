#!/usr/bin/env python3
"""Prototype: nearby KMB stops + minutes-until-arrival (mirrors planned browser logic)."""
from __future__ import annotations

import argparse
import json
import math
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Any

KMB_STOP = "https://data.etabus.gov.hk/v1/transport/kmb/stop"
KMB_STOP_ETA = "https://data.etabus.gov.hk/v1/transport/kmb/stop-eta/{stop_id}"
HKT = timezone(timedelta(hours=8))


def get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def minutes_until(eta_iso: str | None, now: datetime) -> int | None:
    if not eta_iso:
        return None
    # API returns +08:00; fromisoformat handles it
    eta = datetime.fromisoformat(eta_iso)
    if eta.tzinfo is None:
        eta = eta.replace(tzinfo=HKT)
    return max(0, int(round((eta - now).total_seconds() / 60.0)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lng", type=float, required=True)
    ap.add_argument("--radius", type=float, default=300.0, help="meters")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()

    print(f"Fetching KMB stop list…")
    stops = get_json(KMB_STOP).get("data") or []
    scored = []
    for s in stops:
        try:
            lat, lng = float(s["lat"]), float(s["long"])
        except (KeyError, TypeError, ValueError):
            continue
        d = haversine_m(args.lat, args.lng, lat, lng)
        if d <= args.radius:
            scored.append((d, s))
    scored.sort(key=lambda x: x[0])
    nearby = scored[: args.limit]
    print(f"Found {len(scored)} within {args.radius}m; showing {len(nearby)}\n")

    now = datetime.now(HKT)
    for dist, s in nearby:
        sid = s["stop"]
        print(f"=== {s.get('name_tc') or s.get('name_en')} ({sid}) — {dist:.0f} m ===")
        payload = get_json(KMB_STOP_ETA.format(stop_id=sid))
        rows = payload.get("data") or []
        # group by route+dir+dest
        by_key: dict[tuple, list] = {}
        for row in rows:
            key = (row.get("route"), row.get("dir"), row.get("dest_tc") or row.get("dest_en"))
            by_key.setdefault(key, []).append(row)
        if not by_key:
            print("  (no ETAs)\n")
            continue
        for (route, direction, dest), group in sorted(by_key.items(), key=lambda x: (x[0][0] or "", x[0][1] or "")):
            etas = []
            for g in sorted(group, key=lambda r: r.get("eta_seq") or 0):
                m = minutes_until(g.get("eta"), now)
                if m is None:
                    continue
                rmk = g.get("rmk_tc") or g.get("rmk_en") or ""
                etas.append(f"{m}′" + (f" ({rmk})" if rmk else ""))
            if etas:
                print(f"  {route} → {dest} [{direction}]: {', '.join(etas)}")
        print()


if __name__ == "__main__":
    main()
