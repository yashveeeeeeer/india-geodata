#!/usr/bin/env python3
"""Measure how well each state and district is actually covered by monitors.

A state's air quality number is only as good as the monitors behind it. Delhi has
41 across 100% of its area; Jharkhand has one for 24 districts. This computes that
difference so the map can show a value together with how much to trust it, rather
than painting every unit with equal confidence.

For each unit it records the monitor count, the city count, and the share of the
unit's area lying within `--radius` km of any monitor. It also assigns every city
to its state and district, which is what lets the page roll city values up.

Writes:
    docs/projects/air-quality/data/coverage.json   for the page
    data/air-quality/monitor-coverage.csv          the published dataset

Usage:
    python scripts/build-aq-coverage.py [--radius 50]
"""

import argparse
import json
import os
import csv
from datetime import datetime, timezone

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

EQUAL_AREA = "EPSG:6933"          # metres, equal area — required for area shares
WGS84 = "EPSG:4326"


def decode_topology(path, obj_name):
    """Minimal TopoJSON reader: quantised, delta-encoded arcs into GeoJSON."""
    topo = json.load(open(path, encoding="utf-8"))
    tr = topo.get("transform")
    arcs = []
    for arc in topo["arcs"]:
        pts, x, y = [], 0, 0
        for dx, dy in arc:
            if tr:
                x += dx
                y += dy
                pts.append((x * tr["scale"][0] + tr["translate"][0],
                            y * tr["scale"][1] + tr["translate"][1]))
            else:
                pts.append((dx, dy))
        arcs.append(pts)

    def ring(idxs):
        pts = []
        for i in idxs:
            a = arcs[~i][::-1] if i < 0 else arcs[i]
            pts.extend(a if not pts else a[1:])
        return pts

    feats = []
    for g in topo["objects"][obj_name]["geometries"]:
        t = g.get("type")
        if t == "Polygon":
            coords = [ring(r) for r in g["arcs"]]
        elif t == "MultiPolygon":
            coords = [[ring(r) for r in poly] for poly in g["arcs"]]
        else:
            continue
        props = dict(g.get("properties", {}))
        props["fid"] = str(g.get("id"))          # unique; lgd is not (two J&K districts share 0)
        feats.append({"type": "Feature", "properties": props,
                      "geometry": {"type": t, "coordinates": coords}})
    return gpd.GeoDataFrame.from_features(feats, crs=WGS84)


def coverage_for(units, key_field, points, reach, label_field="name"):
    """Per unit: monitors inside it, and the share of its area within reach of any
    monitor — including monitors just outside the border, which still inform it."""
    out = {}
    for _, u in units.iterrows():
        geom = u.geometry
        if geom is None or geom.is_empty or geom.area <= 0:
            continue
        inside = int(points.within(geom).sum())
        covered = geom.intersection(reach).area if reach is not None else 0.0
        out[str(u[key_field])] = {
            "name": u[label_field],
            "lgd": str(u.get("lgd", "")),
            "stations": inside,
            "cover": round(covered / geom.area * 100, 1),
            "area_km2": round(geom.area / 1e6),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius", type=float, default=50.0, help="km a monitor is taken to inform")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    maps = os.path.join(root, "docs", "maps", "data")
    data_dir = os.path.join(root, "docs", "projects", "air-quality", "data")

    stations = json.load(open(os.path.join(data_dir, "stations.json"), encoding="utf-8"))
    cities = json.load(open(os.path.join(data_dir, "cities.json"), encoding="utf-8"))

    states = decode_topology(os.path.join(maps, "states.topo.json"), "states").to_crs(EQUAL_AREA)
    districts = decode_topology(os.path.join(maps, "districts.topo.json"), "districts").to_crs(EQUAL_AREA)
    print(f"  {len(states)} states, {len(districts)} districts")

    pts = gpd.GeoDataFrame(
        pd.DataFrame(stations),
        geometry=[Point(s["lon"], s["lat"]) for s in stations],
        crs=WGS84).to_crs(EQUAL_AREA)
    reach = pts.geometry.buffer(args.radius * 1000).union_all()
    print(f"  {len(pts)} monitors, {args.radius:.0f} km reach")

    st_cov = coverage_for(states, "fid", pts, reach)
    di_cov = coverage_for(districts, "fid", pts, reach)

    # Which unit does each city sit in? This is what lets the page roll city
    # values up to a district or state.
    cpts = gpd.GeoDataFrame(
        pd.DataFrame(cities),
        geometry=[Point(c["lon"], c["lat"]) for c in cities],
        crs=WGS84).to_crs(EQUAL_AREA)
    j_st = gpd.sjoin(cpts, states[["fid", "geometry"]].rename(columns={"fid": "st"}),
                     how="left", predicate="within")
    j_di = gpd.sjoin(cpts, districts[["fid", "geometry"]].rename(columns={"fid": "di"}),
                     how="left", predicate="within")
    city_unit = {}
    di_by_id = dict(zip(j_di["id"], j_di["di"]))
    for cid, st in zip(j_st["id"], j_st["st"]):
        di = di_by_id.get(cid)
        city_unit[cid] = {
            "state": None if pd.isna(st) else str(st),
            "district": None if pd.isna(di) else str(di),
        }
    placed = sum(1 for v in city_unit.values() if v["state"])
    print(f"  {placed} of {len(cities)} cities placed in a state")

    # Stations are placed individually too. A city point is the mean of its
    # monitors, so for a city spanning several districts — Delhi covers eleven —
    # the centroid lands in one of them and the rest would look unmonitored.
    spts = gpd.GeoDataFrame(
        pd.DataFrame(stations),
        geometry=[Point(s["lon"], s["lat"]) for s in stations],
        crs=WGS84).to_crs(EQUAL_AREA)
    s_st = gpd.sjoin(spts, states[["fid", "geometry"]].rename(columns={"fid": "st"}),
                     how="left", predicate="within")
    s_di = gpd.sjoin(spts, districts[["fid", "geometry"]].rename(columns={"fid": "di"}),
                     how="left", predicate="within")
    di_by_station = dict(zip(s_di["id"], s_di["di"]))
    city_of = {st["id"]: st["city"] + "|" + st["state"] for st in stations}
    city_id_by_key = {c["name"] + "|" + c["state"]: c["id"] for c in cities}
    station_unit = {}
    for sid, stv in zip(s_st["id"], s_st["st"]):
        div = di_by_station.get(sid)
        station_unit[sid] = {
            "state": None if pd.isna(stv) else str(stv),
            "district": None if pd.isna(div) else str(div),
            "city": city_id_by_key.get(city_of.get(sid, ""), None),
        }
    dplaced = sum(1 for v in station_unit.values() if v["district"])
    print(f"  {dplaced} of {len(stations)} monitors placed in a district")

    # city counts per unit, so the page can say how many cities back a number
    for unit_key, table in (("state", st_cov), ("district", di_cov)):
        seen = {}
        for v in table.values():
            v["cities"] = 0
        for sid, u in station_unit.items():
            k, c = u[unit_key], u["city"]
            if k and c and k in table:
                seen.setdefault(k, set()).add(c)
        for k, cs in seen.items():
            table[k]["cities"] = len(cs)

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "radius_km": args.radius,
        "note": "cover = share of the unit's area within radius_km of any monitor",
        "states": st_cov,
        "districts": di_cov,
        "cityUnit": city_unit,
        "stationUnit": station_unit,
    }
    out = os.path.join(data_dir, "coverage.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"  -> {os.path.relpath(out, root)} ({os.path.getsize(out)/1024:.0f} KB)")

    # the same numbers as a citable dataset
    ds_dir = os.path.join(root, "data", "air-quality")
    os.makedirs(ds_dir, exist_ok=True)
    csv_path = os.path.join(ds_dir, "monitor-coverage.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["level", "feature_id", "lgd_code", "name", "stations", "cities",
                    "pct_area_within_%dkm" % args.radius, "area_km2"])
        for level, table in (("state", st_cov), ("district", di_cov)):
            for fid, v in sorted(table.items(), key=lambda kv: -kv[1]["stations"]):
                w.writerow([level, fid, v["lgd"], v["name"], v["stations"], v["cities"],
                            v["cover"], v["area_km2"]])
    print(f"  -> {os.path.relpath(csv_path, root)}")

    nat = sum(v["area_km2"] for v in st_cov.values())
    weighted = sum(v["area_km2"] * v["cover"] for v in st_cov.values()) / nat
    zero = sum(1 for v in di_cov.values() if v["stations"] == 0)
    print(f"  national area within {args.radius:.0f} km of a monitor: {weighted:.1f}%")
    print(f"  districts with no monitor: {zero} of {len(di_cov)}")


if __name__ == "__main__":
    main()
