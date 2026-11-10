#!/usr/bin/env python3
"""Repair the points that sit outside India in four release datasets.

A scan of every release Parquet file's extent found four point layers with
points far outside India. This script puts back the positions it can, takes
away the ones it can't, and writes new release files. Only the geometry of
those rows changes: every other row, and every other column, stays as it was.

    lift-stations   release water/irrigation, WRIS_LIFT_Stations
        35 stations have longitude and latitude the wrong way round. Swap them
        back, if the station then lands in its own state. (All 35 do.)
    track-pois      release infra/railways, IR_Track_POIs
        1,009 points sit far outside India. Most still carry their real place
        in the xcoord/ycoord or latitude/longitude columns. Use it when it lies
        near an IR_Tracks line of the same railway zone, or near good points on
        the same section at the same kilometre. Otherwise leave no position.
        (999 get their place back; 10 get no position.)
    habitations     release admin/habitations, PMGSY_Habitations
        72 habitations sit outside India. Swap longitude and latitude back when
        that puts the point in the habitation's own state (STATE_ID). The rest
        have broken numbers (some near-infinite) and get no position.
        (39 are swapped back; 33 get no position.)
    activities      release admin/panchayats, egramswaraj_activities
        5 multi-point activities have 1 or 2 of their points at 0°N 0°E.
        Remove those points. The activities' other points stay.

The three release files are patched, not rebuilt:
    .parquet        same schema, metadata and row groups; the geometry (and the
                    bbox column, if there is one) changes only in repaired rows
    .geojsonl.7z    every line is copied as it is, except the repaired features,
                    whose "geometry" is rewritten in the file's own style
    .pmtiles        tiles without a broken point are copied byte for byte. In
                    the others, broken features are taken out, and repaired ones
                    are put in at their new place, at the zoom levels they had
                    before. So tippecanoe isn't needed, and every other feature
                    keeps the place and zoom levels tippecanoe gave it.

After building, the script compares the new files with the originals, and
stops with an error if anything other than the repaired rows differs.

Usage:
    python scripts/repair-points-outside-india.py DATASET SRC_DIR OUT_DIR
        [--tracks IR_Tracks.parquet] [--states SOI_States.parquet]

    SRC_DIR   the dataset's three release files, for example from
              gh release download infra/railways --repo yashveeeeeeer/india-geodata -D SRC_DIR -p "IR_Track_POIs.*"
    OUT_DIR   gets the three repaired files, plus NAME.changes.csv with one
              line per repaired row (old and new position, and why)
    --tracks  IR_Tracks.parquet, release infra/railways (track-pois)
    --states  SOI_States.parquet, release admin/states (lift-stations, habitations)

Requires:
    pyarrow, shapely, geopandas, protobuf (pip install pyarrow shapely geopandas protobuf)
    7-Zip on PATH as 7z (or pass --sevenzip)
"""

import argparse
import csv
import gzip
import hashlib
import json
import math
import mmap
import os
import re
import shutil
import struct
import subprocess
from dataclasses import dataclass

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

# A box around India. Every good point in these four files is inside it.
LON = (68.0, 98.0)
LAT = (6.0, 38.0)

DATASETS = {
    "lift-stations": {
        "name": "WRIS_LIFT_Stations",
        "key": ["objectid"],
    },
    "track-pois": {
        "name": "IR_Track_POIs",
        "key": ["objectid", "gid", "layer"],
    },
    "habitations": {
        "name": "PMGSY_Habitations",
        "key": ["HAB_ID", "STATE_ID", "DISTRICT_I", "BLOCK_ID", "HAB_NAME", "TOT_POPULA"],
    },
    "activities": {
        "name": "egramswaraj_activities",
        "key": ["Activity Code", "gp_code"],
    },
}

# track-pois: how close a recovered position must be to count as confirmed.
NEAR_TRACK_M = 500     # to an IR_Tracks line of the same railway zone
NEAR_POINT_M = 500     # to a good point on the same section ...
NEAR_POINT_KM = 1      # ... whose kilometre (distkm) is within this much
METRIC_CRS = "EPSG:7755"  # WGS 84 / India NSF LCC, in metres


def inside(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    with np.errstate(invalid="ignore"):
        return (x >= LON[0]) & (x <= LON[1]) & (y >= LAT[0]) & (y <= LAT[1])


def norm(v):
    """A property value as a plain, comparable Python value."""
    if v is None:
        return None
    if isinstance(v, bytes):
        return v.decode("utf-8")
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        v = float(v)
        if math.isnan(v):
            return None
        return int(v) if v.is_integer() else v
    return v


@dataclass
class Fix:
    row: int          # row number in the Parquet file
    key: tuple        # the row's values of the dataset's key columns
    old: object       # shapely geometry as it was
    new: object       # repaired shapely geometry, or None for no position
    action: str       # swap | move | drop | drop-parts
    note: str


def coords_key(geom):
    """The geometry's points, rounded, for matching the same feature in other files."""
    return tuple(round(float(v), 6) for v in shapely.get_coordinates(geom).ravel())


# --------------------------------------------------------------------------
# Rules: which rows are broken, and what they become
# --------------------------------------------------------------------------

def read_points(path, columns):
    t = pq.read_table(path, columns=columns + ["geometry"])
    df = t.drop(["geometry"]).to_pandas()
    geoms = shapely.from_wkb(t.column("geometry").to_numpy(zero_copy_only=False))
    return df, geoms


def soi_state_of(states_path, xs, ys):
    """The Survey of India state each point falls in (None outside every state)."""
    import geopandas as gpd

    st = gpd.read_parquet(states_path)[["STATE", "geometry"]].to_crs("EPSG:4326")
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(xs, ys), crs="EPSG:4326")
    j = gpd.sjoin(pts, st, how="left", predicate="within")
    j = j[~j.index.duplicated()]
    return [v if isinstance(v, str) else None for v in j["STATE"].reindex(range(len(xs)))]


def swap_if_in_state(df, geoms, key, state_col, states_path):
    """Rows outside the box: swap x and y if that lands them in their own state."""
    x, y = shapely.get_x(geoms), shapely.get_y(geoms)
    bad = ~inside(x, y)
    good_idx = np.flatnonzero(~bad)
    # Which SOI state each state code stands for: where most of its good points are.
    sample = good_idx if len(good_idx) <= 200_000 else np.random.default_rng(0).choice(good_idx, 200_000, replace=False)
    names = soi_state_of(states_path, x[sample], y[sample])
    pairs = [(c, n) for c, n in zip(df[state_col].to_numpy()[sample], names) if n is not None]
    tally = {}
    for c, n in pairs:
        tally.setdefault(norm(c), {}).setdefault(n, 0)
        tally[norm(c)][n] += 1
    state_for = {c: max(d, key=d.get) for c, d in tally.items()}

    bad_idx = np.flatnonzero(bad)
    sx, sy = y[bad_idx], x[bad_idx]
    swappable = inside(sx, sy)
    landed = [None] * len(bad_idx)
    if swappable.any():
        got = soi_state_of(states_path, sx[swappable], sy[swappable])
        for i, n in zip(np.flatnonzero(swappable), got):
            landed[i] = n
    fixes = []
    for i, r in enumerate(bad_idx):
        k = tuple(norm(df[c].iat[r]) for c in key)
        want = state_for.get(norm(df[state_col].iat[r]))
        if swappable[i] and landed[i] is not None and landed[i] == want:
            fixes.append(Fix(int(r), k, geoms[r], shapely.Point(sx[i], sy[i]), "swap",
                             f"longitude and latitude were swapped; now in {landed[i]}"))
        elif swappable[i]:
            fixes.append(Fix(int(r), k, geoms[r], None, "drop",
                             f"swapped point lands in {landed[i]}, not {want}"))
        else:
            fixes.append(Fix(int(r), k, geoms[r], None, "drop", "coordinates unusable"))
    return fixes


def rules_lift_stations(src, args):
    key = DATASETS["lift-stations"]["key"]
    df, geoms = read_points(src, sorted(set(key + ["state"])))
    return swap_if_in_state(df, geoms, key, "state", args.states)


def rules_habitations(src, args):
    key = DATASETS["habitations"]["key"]
    df, geoms = read_points(src, key)
    return swap_if_in_state(df, geoms, key, "STATE_ID", args.states)


DMS_NUM = re.compile(r"\d+(?:\.\d+)?")


def parse_dms(s):
    """'23°10'3.1386"N' -> 23.1675385. Only clean degree, minute, second strings."""
    if not s:
        return math.nan
    n = DMS_NUM.findall(s)
    if len(n) != 3:
        return math.nan
    d, m, sec = (float(v) for v in n)
    if m >= 60 or sec >= 60:
        return math.nan
    return d + m / 60 + sec / 3600


def rules_track_pois(src, args):
    import geopandas as gpd

    key =DATASETS["track-pois"]["key"]
    cols = ["objectid", "gid", "layer", "railway", "tmssection", "distkm",
            "xcoord", "ycoord", "latitude", "longitude"]
    df, geoms = read_points(src, cols)
    df["x"], df["y"] = shapely.get_x(geoms), shapely.get_y(geoms)
    bad = ~inside(df.x, df.y)
    b = df[bad].copy()

    # Where the row says it is. The latitude/longitude strings are more precise
    # than xcoord/ycoord (3 decimals), and the rest of the file's geometry was
    # made from them, so use them when they parse cleanly and agree.
    lat = b.latitude.map(parse_dms)
    lon = b.longitude.map(parse_dms)
    agree = lat.notna() & lon.notna() & ((lat - b.ycoord).abs() <= 0.0011) & ((lon - b.xcoord).abs() <= 0.0011)
    b["cx"] = np.where(agree, lon.round(7), b.xcoord)
    b["cy"] = np.where(agree, lat.round(7), b.ycoord)
    b["src"] = np.where(agree, "latitude/longitude", "xcoord/ycoord")
    b["ok_box"] = inside(b.cx, b.cy)

    # Check 1: distance to the nearest IR_Tracks line of the same railway zone.
    tracks = gpd.read_parquet(args.tracks)[["railway", "geometry"]].to_crs(METRIC_CRS)
    cand = b[b.ok_box]
    pts = gpd.GeoSeries(gpd.points_from_xy(cand.cx, cand.cy), index=cand.index, crs="EPSG:4326").to_crs(METRIC_CRS)
    b["d_track"] = np.inf
    for rly, idx in cand.groupby("railway").groups.items():
        tr = tracks[tracks.railway == rly]
        if len(tr):
            j = gpd.sjoin_nearest(gpd.GeoDataFrame(geometry=pts.loc[idx]), tr, distance_col="d")
            b.loc[idx, "d_track"] = j[~j.index.duplicated()]["d"]

    # Check 2: distance to the nearest good point on the same railway and section,
    # within NEAR_POINT_KM of the same kilometre. IR_Tracks misses some lines, and
    # good points on those lines sit just as far from it.
    good = df[~bad]
    gpts = gpd.GeoSeries(gpd.points_from_xy(good.x, good.y), index=good.index, crs="EPSG:4326").to_crs(METRIC_CRS)
    b["d_point"] = np.inf
    for (rly, sec), idx in cand.groupby(["railway", "tmssection"]).groups.items():
        pool = good[(good.railway == rly) & (good.tmssection == sec)]
        if not len(pool):
            continue
        for i in idx:
            near = pool.index[(pool.distkm - b.at[i, "distkm"]).abs() <= NEAR_POINT_KM]
            if len(near):
                b.at[i, "d_point"] = gpts.loc[near].distance(pts.loc[i]).min()

    fixes = []
    for r, row in b.iterrows():
        k = tuple(norm(row[c]) for c in key)
        if not row.ok_box:
            fixes.append(Fix(int(r), k, geoms[r], None, "drop", "no position in India in any column"))
            continue
        where = f"{row.src}; {row.d_track:.0f} m from track" if np.isfinite(row.d_track) else f"{row.src}; no track of this zone"
        if np.isfinite(row.d_point):
            where += f", {row.d_point:.0f} m from points on its section"
        if row.d_track <= NEAR_TRACK_M or row.d_point <= NEAR_POINT_M:
            fixes.append(Fix(int(r), k, geoms[r], shapely.Point(row.cx, row.cy), "move", "position from " + where))
        else:
            fixes.append(Fix(int(r), k, geoms[r], None, "drop", "position not confirmed: " + where))
    return fixes


def rules_activities(src, args):
    """Multi-points with parts at exactly 0,0: drop those parts."""
    key = DATASETS["activities"]["key"]
    pf = pq.ParquetFile(src)
    fixes, offset = [], 0
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg, columns=key + ["geometry"])
        g = shapely.from_wkb(t.column("geometry").to_numpy(zero_copy_only=False))
        x1, y1, x2, y2 = shapely.bounds(g).T
        for i in np.flatnonzero(~(inside(x1, y1) & inside(x2, y2))):
            pts = shapely.get_coordinates(g[i])
            zero = (pts[:, 0] == 0) & (pts[:, 1] == 0)
            if not zero.any():
                continue  # just outside the box but not 0,0: left alone
            k = tuple(norm(t.column(c)[int(i)].as_py()) for c in key)
            keep = pts[~zero]
            new = shapely.MultiPoint(keep) if len(keep) else None
            fixes.append(Fix(offset + int(i), k, g[i], new, "drop-parts",
                             f"{int(zero.sum())} of {len(pts)} points at 0°N 0°E removed"))
        offset += t.num_rows
    return fixes


RULES = {
    "lift-stations": rules_lift_stations,
    "track-pois": rules_track_pois,
    "habitations": rules_habitations,
    "activities": rules_activities,
}


# --------------------------------------------------------------------------
# Parquet
# --------------------------------------------------------------------------

def wkb(geom):
    return None if geom is None else shapely.to_wkb(geom, byte_order=1, flavor="iso", output_dimension=2)


def bbox_of(geom):
    if geom is None:
        return None
    x1, y1, x2, y2 = shapely.bounds(geom)
    return {"xmin": float(x1), "ymin": float(y1), "xmax": float(x2), "ymax": float(y2)}


def write_parquet(src, dst, fixes):
    pf = pq.ParquetFile(src)
    schema = pf.schema_arrow
    by_row = {f.row: f for f in fixes}
    has_bbox = "bbox" in schema.names

    # New extent for the "geo" metadata: the old one, minus broken rows, plus repaired ones.
    ext = [math.inf, math.inf, -math.inf, -math.inf]
    offset = 0
    for rg in range(pf.num_row_groups):
        g = shapely.from_wkb(pf.read_row_group(rg, columns=["geometry"]).column(0).to_numpy(zero_copy_only=False))
        x1, y1, x2, y2 = shapely.bounds(g).T
        keep = np.ones(len(g), bool)
        for r in by_row:
            if offset <= r < offset + len(g):
                keep[r - offset] = False
        keep &= ~np.isnan(x1)
        if keep.any():
            ext = [min(ext[0], x1[keep].min()), min(ext[1], y1[keep].min()),
                   max(ext[2], x2[keep].max()), max(ext[3], y2[keep].max())]
        offset += len(g)
    for f in fixes:
        if f.new is not None:
            x1, y1, x2, y2 = shapely.bounds(f.new)
            ext = [min(ext[0], x1), min(ext[1], y1), max(ext[2], x2), max(ext[3], y2)]
    ext = [float(v) for v in ext]

    meta = dict(schema.metadata or {})
    geo = json.loads(meta[b"geo"])
    geo["columns"]["geometry"]["bbox"] = ext
    meta[b"geo"] = json.dumps(geo).encode()
    schema = schema.with_metadata(meta)

    store_schema = b"ARROW:schema" in (pf.metadata.metadata or {})
    gi = schema.get_field_index("geometry")
    bi = schema.get_field_index("bbox") if has_bbox else None
    with pq.ParquetWriter(dst, schema, compression="zstd", compression_level=9, store_schema=store_schema) as w:
        offset = 0
        for rg in range(pf.num_row_groups):
            t = pf.read_row_group(rg)
            n = t.num_rows
            here = [f for r, f in by_row.items() if offset <= r < offset + n]
            if here:
                geom = t.column(gi).to_pylist()
                for f in here:
                    geom[f.row - offset] = wkb(f.new)
                t = t.set_column(gi, schema.field(gi), pa.array(geom, type=schema.field(gi).type))
                if has_bbox:
                    bb = t.column(bi).to_pylist()
                    for f in here:
                        bb[f.row - offset] = bbox_of(f.new)
                    t = t.set_column(bi, schema.field(bi), pa.array(bb, type=schema.field(bi).type))
            w.write_table(t, row_group_size=n)
            offset += n
        if not store_schema:
            # without the Arrow schema, pyarrow leaves out the file metadata: put "geo" back
            w.add_key_value_metadata({k.decode(): v.decode() for k, v in meta.items()})
    return ext


def check_parquet(src, dst, fixes):
    a, b = pq.ParquetFile(src), pq.ParquetFile(dst)
    sa, sb = a.schema_arrow, b.schema_arrow
    assert sa.remove_metadata() == sb.remove_metadata(), "schema changed"
    for i in range(len(sa)):
        assert sa.field(i).metadata == sb.field(i).metadata, f"field metadata changed: {sa.field(i).name}"
    ma, mb = dict(sa.metadata or {}), dict(sb.metadata or {})
    ga, gb = json.loads(ma.pop(b"geo")), json.loads(mb.pop(b"geo"))
    ga["columns"]["geometry"].pop("bbox")
    gb["columns"]["geometry"].pop("bbox")
    assert ma == mb and ga == gb, "file metadata changed beyond the extent"
    assert a.metadata.num_rows == b.metadata.num_rows, "row count changed"
    assert [a.metadata.row_group(i).num_rows for i in range(a.num_row_groups)] == \
           [b.metadata.row_group(i).num_rows for i in range(b.num_row_groups)], "row groups changed"
    want = {f.row: wkb(f.new) for f in fixes}
    changed, offset = set(), 0
    for rg in range(a.num_row_groups):
        ta, tb = a.read_row_group(rg), b.read_row_group(rg)
        for name in sa.names:
            ca, cb = ta.column(name), tb.column(name)
            if name in ("geometry", "bbox"):
                if ca.equals(cb):
                    continue
                la, lb = ca.to_pylist(), cb.to_pylist()
                for i, (u, v) in enumerate(zip(la, lb)):
                    if u != v:
                        r = offset + i
                        assert r in want, f"row {r}: {name} changed but is not a repaired row"
                        if name == "geometry":
                            assert v == want[r], f"row {r}: geometry is not the repaired one"
                            changed.add(r)
            else:
                assert ca.equals(cb), f"column {name} changed in row group {rg}"
        offset += ta.num_rows
    assert changed == set(want), f"{len(set(want) - changed)} repaired rows did not change"
    return len(changed)


# --------------------------------------------------------------------------
# GeoJSONL
# --------------------------------------------------------------------------

GEOM_KEY = b'"geometry": '
NUMBER = re.compile(rb"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


def geometry_span(line):
    """(start, end) of the geometry value in a GeoJSON feature line.
    All four files hold points or multi-points, so the geometry has no inner braces."""
    i = line.find(GEOM_KEY)
    if i < 0:
        return None
    if line.find(GEOM_KEY, i + 1) >= 0:
        raise ValueError("more than one geometry key in a line")
    start = i + len(GEOM_KEY)
    if line.startswith(b"null", start):
        return start, start + 4
    return start, line.index(b"}", start) + 1


def inside1(x, y):
    return LON[0] <= x <= LON[1] and LAT[0] <= y <= LAT[1]


def new_geometry_text(old_text, fix):
    """The repaired geometry, written the way the line wrote the old one."""
    if fix.new is None:
        return b"null"
    gdal_style = old_text.startswith(b"{ ")  # GDAL: { "type": "Point", "coordinates": [ x, y ] }
    nums = NUMBER.findall(old_text[old_text.index(b"coordinates"):])
    if fix.action == "swap":
        # Same numbers, as written, the other way round.
        assert len(nums) == 2
        x, y = nums[1], nums[0]
        body = b"[ " + x + b", " + y + b" ]" if gdal_style else b"[" + x + b", " + y + b"]"
        return old_text[: old_text.index(b"[")] + body + old_text[old_text.rindex(b"]") + 1:]
    if fix.action == "drop-parts":
        old = json.loads(old_text)
        if json.dumps(old).encode() != old_text:
            raise ValueError("unexpected geometry style")  # re-writing it would change more than the parts
        old["coordinates"] = [p for p in old["coordinates"] if not (p[0] == 0 and p[1] == 0)]
        return json.dumps(old).encode()
    # move: a new point
    x, y = json.dumps(float(fix.new.x)).encode(), json.dumps(float(fix.new.y)).encode()
    if gdal_style:
        return b'{ "type": "Point", "coordinates": [ ' + x + b", " + y + b" ] }"
    return b'{"type": "Point", "coordinates": [' + x + b", " + y + b"]}"


def parse_coords(geom):
    c = geom["coordinates"]
    if geom["type"] == "Point":
        return [c]
    return c


def patch_geojsonl(src7z, dst7z, name, fixes, key, sevenzip):
    by_key = {}
    for f in fixes:
        by_key.setdefault(f.key, []).append(f)
    plain = os.path.join(os.path.dirname(dst7z), name + ".geojsonl")
    used, lines = set(), 0
    p = subprocess.Popen([sevenzip, "e", "-so", src7z, name + ".geojsonl"], stdout=subprocess.PIPE,
                         stdin=subprocess.DEVNULL, bufsize=1 << 20)
    with open(plain, "wb", buffering=1 << 20) as out:
        for line in p.stdout:
            lines += 1
            span = geometry_span(line)
            if span is None or line[span[0]:span[1]] == b"null":
                out.write(line)
                continue
            gtext = line[span[0]:span[1]]
            pts = parse_coords(json.loads(gtext))
            if all(inside1(p_[0], p_[1]) for p_ in pts):
                out.write(line)
                continue
            props = json.loads(line).get("properties") or {}
            k = tuple(norm(props.get(c)) for c in key)
            ck = tuple(round(float(v), 6) for p_ in pts for v in p_)
            match = [f for f in by_key.get(k, []) if coords_key(f.old) == ck and f.row not in used]
            if len(match) != 1:
                raise SystemExit(f"line {lines}: {len(match)} repairs match this feature outside India: {k}")
            f = match[0]
            used.add(f.row)
            new = new_geometry_text(gtext, f)
            if f.new is not None:  # the rewritten text must say what the Parquet says
                got = tuple(round(float(v), 6) for p_ in parse_coords(json.loads(new)) for v in p_)
                assert got == coords_key(f.new), f"line {lines}: text differs from Parquet"
            out.write(line[:span[0]] + new + line[span[1]:])
    if p.wait() != 0:
        raise SystemExit("7z failed reading " + src7z)
    missing = [f for f in fixes if f.row not in used]
    if missing:
        raise SystemExit(f"{len(missing)} repaired rows not found in the GeoJSONL, e.g. {missing[0].key}")
    if os.path.exists(dst7z):
        os.remove(dst7z)
    # run in the output folder, so the archive holds just the file name
    subprocess.run([sevenzip, "a", "-t7z", "-m0=PPMd", "-y", os.path.basename(dst7z), os.path.basename(plain)],
                   cwd=os.path.dirname(os.path.abspath(dst7z)), check=True,
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    os.remove(plain)
    return lines


def check_geojsonl(src7z, dst7z, name, fixes, key, sevenzip):
    pa_ = subprocess.Popen([sevenzip, "e", "-so", src7z, name + ".geojsonl"], stdout=subprocess.PIPE,
                           stdin=subprocess.DEVNULL)
    pb_ = subprocess.Popen([sevenzip, "e", "-so", dst7z, name + ".geojsonl"], stdout=subprocess.PIPE,
                           stdin=subprocess.DEVNULL)
    want = {}
    for f in fixes:
        want.setdefault((f.key, coords_key(f.old)), []).append(f)
    n = changed = 0
    for la, lb in zip(pa_.stdout, pb_.stdout):
        n += 1
        if la == lb:
            continue
        sa, sb = geometry_span(la), geometry_span(lb)
        assert la[:sa[0]] == lb[:sb[0]] and la[sa[1]:] == lb[sb[1]:], f"line {n}: more than the geometry changed"
        props = json.loads(la).get("properties") or {}
        geom = json.loads(la[sa[0]:sa[1]])
        k = (tuple(norm(props.get(c)) for c in key), tuple(round(float(v), 6) for p_ in parse_coords(geom) for v in p_))
        assert k in want, f"line {n}: changed but is not a repaired feature"
        changed += 1
    rest_a, rest_b = pa_.stdout.read(1), pb_.stdout.read(1)
    assert pa_.wait() == 0 and pb_.wait() == 0, "7z failed reading the archives"
    assert not rest_a and not rest_b, "line count changed"
    assert n > 0, "no lines read"
    assert changed == len(fixes), f"{changed} lines changed, {len(fixes)} expected"
    return n, changed


# --------------------------------------------------------------------------
# Mapbox vector tiles (just enough of the format to edit point features)
# --------------------------------------------------------------------------

def _tile_class():
    from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

    F = descriptor_pb2.FieldDescriptorProto
    fdp = descriptor_pb2.FileDescriptorProto(name="india_geodata_mvt.proto", package="india_geodata_mvt", syntax="proto2")
    tile = fdp.message_type.add(name="Tile")
    gt = tile.enum_type.add(name="GeomType")
    for i, n in enumerate(["UNKNOWN", "POINT", "LINESTRING", "POLYGON"]):
        gt.value.add(name=n, number=i)
    val = tile.nested_type.add(name="Value")
    for n, num, typ in [("string_value", 1, F.TYPE_BYTES), ("float_value", 2, F.TYPE_FLOAT),
                        ("double_value", 3, F.TYPE_DOUBLE), ("int_value", 4, F.TYPE_INT64),
                        ("uint_value", 5, F.TYPE_UINT64), ("sint_value", 6, F.TYPE_SINT64),
                        ("bool_value", 7, F.TYPE_BOOL)]:
        val.field.add(name=n, number=num, type=typ, label=F.LABEL_OPTIONAL)
    feat = tile.nested_type.add(name="Feature")
    feat.field.add(name="id", number=1, type=F.TYPE_UINT64, label=F.LABEL_OPTIONAL)
    feat.field.add(name="tags", number=2, type=F.TYPE_UINT32, label=F.LABEL_REPEATED).options.packed = True
    feat.field.add(name="type", number=3, type=F.TYPE_ENUM, label=F.LABEL_OPTIONAL,
                   type_name=".india_geodata_mvt.Tile.GeomType", default_value="UNKNOWN")
    feat.field.add(name="geometry", number=4, type=F.TYPE_UINT32, label=F.LABEL_REPEATED).options.packed = True
    lay = tile.nested_type.add(name="Layer")
    lay.field.add(name="version", number=15, type=F.TYPE_UINT32, label=F.LABEL_OPTIONAL, default_value="1")
    lay.field.add(name="name", number=1, type=F.TYPE_BYTES, label=F.LABEL_OPTIONAL)
    lay.field.add(name="features", number=2, type=F.TYPE_MESSAGE, label=F.LABEL_REPEATED,
                  type_name=".india_geodata_mvt.Tile.Feature")
    lay.field.add(name="keys", number=3, type=F.TYPE_BYTES, label=F.LABEL_REPEATED)
    lay.field.add(name="values", number=4, type=F.TYPE_MESSAGE, label=F.LABEL_REPEATED,
                  type_name=".india_geodata_mvt.Tile.Value")
    lay.field.add(name="extent", number=5, type=F.TYPE_UINT32, label=F.LABEL_OPTIONAL, default_value="4096")
    tile.field.add(name="layers", number=3, type=F.TYPE_MESSAGE, label=F.LABEL_REPEATED,
                   type_name=".india_geodata_mvt.Tile.Layer")
    pool = descriptor_pool.DescriptorPool()
    pool.Add(fdp)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("india_geodata_mvt.Tile"))


Tile = None
POINT = 1
VALUE_FIELDS = ("string_value", "float_value", "double_value", "int_value", "uint_value", "sint_value", "bool_value")


def value_py(v):
    for n in VALUE_FIELDS:
        if v.HasField(n):
            x = getattr(v, n)
            return x.decode("utf-8", "replace") if n == "string_value" else x
    return None


def unzig(v):
    return (v >> 1) ^ -(v & 1)


def zig(v):
    return (v << 1) if v >= 0 else ((-v) << 1) - 1


def decode_points(geometry):
    pts, x, y, i, n = [], 0, 0, 0, len(geometry)
    while i < n:
        cmd, cnt = geometry[i] & 7, geometry[i] >> 3
        i += 1
        if cmd in (1, 2):
            for _ in range(cnt):
                x += unzig(geometry[i])
                y += unzig(geometry[i + 1])
                i += 2
                pts.append((x, y))
    return pts


def encode_points(pts):
    g, cx, cy = [(len(pts) << 3) | 1], 0, 0
    for x, y in pts:
        g += [zig(x - cx), zig(y - cy)]
        cx, cy = x, y
    return g


def merc_y(lat):
    lat = max(min(lat, 85.0511287798), -85.0511287798)
    return (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2


def to_lonlat(z, tx, ty, px, py, extent):
    n = 1 << z
    lon = (tx + px / extent) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + py / extent) / n))))
    return lon, lat


def place_point(lon, lat, z, extent, buffer):
    """Tiles at zoom z that hold the point (with tippecanoe's buffer), and its place in each."""
    n = 1 << z
    gx = math.floor((lon + 180) / 360 * n * extent)
    gy = math.floor(merc_y(lat) * n * extent)
    out = []
    for tx in (gx // extent - 1, gx // extent, gx // extent + 1):
        for ty in (gy // extent - 1, gy // extent, gy // extent + 1):
            if 0 <= tx < n and 0 <= ty < n:
                px, py = gx - tx * extent, gy - ty * extent
                if -buffer <= px <= extent + buffer and -buffer <= py <= extent + buffer:
                    out.append((tx, ty, px, py))
    return out


def tile_inside_box(z, x, y, pad=0.05):
    n = 1 << z
    lon1, lon2 = (x - pad) / n * 360 - 180, (x + 1 + pad) / n * 360 - 180
    top = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y - pad) / n))))
    bot = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1 + pad) / n))))
    return lon1 >= LON[0] and lon2 <= LON[1] and bot >= LAT[0] and top <= LAT[1]


# --------------------------------------------------------------------------
# PMTiles v3
# --------------------------------------------------------------------------

HEADER = struct.Struct("<7sB11Q6B4iB2i")  # 127 bytes
HEADER_FIELDS = ("magic", "version", "root_off", "root_len", "meta_off", "meta_len", "leaf_off", "leaf_len",
                 "data_off", "data_len", "n_addressed", "n_entries", "n_contents", "clustered",
                 "internal_compression", "tile_compression", "tile_type", "min_zoom", "max_zoom",
                 "min_lon", "min_lat", "max_lon", "max_lat", "center_zoom", "center_lon", "center_lat")
GZIP = 2


def read_varint(b, p):
    r = s = 0
    while True:
        c = b[p]
        p += 1
        r |= (c & 0x7F) << s
        if c < 0x80:
            return r, p
        s += 7


def put_varint(out, v):
    while v >= 0x80:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v)


def decode_directory(raw):
    b = gzip.decompress(raw)
    n, p = read_varint(b, 0)
    ids, runs, lens, offs = [0] * n, [0] * n, [0] * n, [0] * n
    last = 0
    for i in range(n):
        v, p = read_varint(b, p)
        last += v
        ids[i] = last
    for i in range(n):
        runs[i], p = read_varint(b, p)
    for i in range(n):
        lens[i], p = read_varint(b, p)
    for i in range(n):
        v, p = read_varint(b, p)
        offs[i] = offs[i - 1] + lens[i - 1] if (v == 0 and i > 0) else v - 1
    return list(zip(ids, offs, lens, runs))


def encode_directory(entries):
    out = bytearray()
    put_varint(out, len(entries))
    last = 0
    for e in entries:
        put_varint(out, e[0] - last)
        last = e[0]
    for e in entries:
        put_varint(out, e[3])
    for e in entries:
        put_varint(out, e[2])
    for i, e in enumerate(entries):
        if i > 0 and e[1] == entries[i - 1][1] + entries[i - 1][2]:
            put_varint(out, 0)
        else:
            put_varint(out, e[1] + 1)
    return gzip.compress(bytes(out), mtime=0)


def _rotate(n, x, y, rx, ry):
    if ry == 0:
        if rx == 1:
            x, y = n - 1 - x, n - 1 - y
        x, y = y, x
    return x, y


def zxy_to_id(z, x, y):
    acc = ((1 << (2 * z)) - 1) // 3
    d, s = 0, (1 << z) >> 1
    while s > 0:
        rx = 1 if x & s else 0
        ry = 1 if y & s else 0
        d += s * s * ((3 * rx) ^ ry)
        x, y = _rotate(s, x, y, rx, ry)
        s >>= 1
    return acc + d


def id_to_zxy(tid):
    z, acc = 0, 0
    while acc + (1 << (2 * z)) <= tid:
        acc += 1 << (2 * z)
        z += 1
    t, x, y, s = tid - acc, 0, 0, 1
    n = 1 << z
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        x, y = _rotate(s, x, y, rx, ry)
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return z, x, y


class PMTiles:
    def __init__(self, path):
        self.f = open(path, "rb")
        self.mm = mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ)
        self.h = dict(zip(HEADER_FIELDS, HEADER.unpack(self.mm[:127])))
        assert self.h["magic"] == b"PMTiles" and self.h["version"] == 3, path
        assert self.h["internal_compression"] == GZIP and self.h["tile_compression"] == GZIP, "expects gzip"
        self.meta_raw = self.mm[self.h["meta_off"]:self.h["meta_off"] + self.h["meta_len"]]
        self.meta = json.loads(gzip.decompress(self.meta_raw))
        self.tiles = {}  # tile id -> (offset, length) within the tile data
        self._walk(self.h["root_off"], self.h["root_len"])

    def _walk(self, off, length):
        for tid, o, l, run in decode_directory(self.mm[off:off + length]):
            if run == 0:
                self._walk(self.h["leaf_off"] + o, l)
            else:
                for i in range(run):
                    self.tiles[tid + i] = (o, l)

    def raw(self, tid):
        o, l = self.tiles[tid]
        start = self.h["data_off"] + o
        return self.mm[start:start + l]

    def tile(self, tid):
        t = Tile()
        t.ParseFromString(gzip.decompress(self.raw(tid)))
        return t

    def close(self):
        self.mm.close()
        self.f.close()


def build_directories(entries):
    root = encode_directory(entries)
    if len(root) <= 16384 - 127:
        return root, b""
    leaf_size = 4096
    while True:
        leaves, root_entries = bytearray(), []
        for i in range(0, len(entries), leaf_size):
            chunk = entries[i:i + leaf_size]
            enc = encode_directory(chunk)
            root_entries.append((chunk[0][0], len(leaves), len(enc), 0))
            leaves += enc
        root = encode_directory(root_entries)
        if len(root) <= 16384 - 127:
            return root, bytes(leaves)
        leaf_size = int(leaf_size * 1.2)


def write_pmtiles(src, dst, changed, removed, bounds):
    """Copy src to dst, with `changed` tiles (id -> gzipped bytes) replaced or added
    and `removed` tile ids left out. Tile data stays in tile-id order."""
    ids = sorted((set(src.tiles) - removed) | set(changed))
    entries, plan, seen_old, seen_new, pos = [], [], {}, {}, 0
    for tid in ids:
        if tid in changed:
            data = changed[tid]
            h = hashlib.sha256(data).digest()
            if h in seen_new:
                off = seen_new[h]
            else:
                off = seen_new[h] = pos
                plan.append(("new", data))
                pos += len(data)
            length = len(data)
        else:
            o, length = src.tiles[tid]
            if o in seen_old:
                off = seen_old[o]
            else:
                off = seen_old[o] = pos
                plan.append(("old", o, length))
                pos += length
        if entries and entries[-1][1] == off and entries[-1][0] + entries[-1][3] == tid:
            entries[-1] = (entries[-1][0], off, length, entries[-1][3] + 1)
        else:
            entries.append((tid, off, length, 1))
    root, leaves = build_directories(entries)

    meta = dict(src.meta)
    if "antimeridian_adjusted_bounds" in meta:
        meta["antimeridian_adjusted_bounds"] = ",".join(f"{v:.6f}" for v in bounds)
    meta_raw = gzip.compress(json.dumps(meta, ensure_ascii=False).encode("utf-8"), mtime=0) if meta != src.meta else src.meta_raw

    h = dict(src.h)
    h["root_off"], h["root_len"] = 127, len(root)
    h["meta_off"], h["meta_len"] = 127 + len(root), len(meta_raw)
    h["leaf_off"], h["leaf_len"] = h["meta_off"] + len(meta_raw), len(leaves)
    h["data_off"], h["data_len"] = h["leaf_off"] + len(leaves), pos
    h["n_addressed"] = sum(e[3] for e in entries)
    h["n_entries"] = len(entries)
    h["n_contents"] = len(seen_old) + len(seen_new)
    lat_max = 85.0511287
    h["min_lon"], h["max_lon"] = round(bounds[0] * 1e7), round(bounds[2] * 1e7)
    h["min_lat"], h["max_lat"] = round(max(bounds[1], -lat_max) * 1e7), round(min(bounds[3], lat_max) * 1e7)
    with open(dst, "wb") as out:
        out.write(HEADER.pack(*(h[k] for k in HEADER_FIELDS)))
        out.write(root)
        out.write(meta_raw)
        out.write(leaves)
        base = src.h["data_off"]
        for p in plan:
            if p[0] == "new":
                out.write(p[1])
            else:
                out.write(src.mm[base + p[1]:base + p[1] + p[2]])
    return h


def patch_pmtiles(src_path, dst_path, fixes, key, bounds):
    """Take broken features out of the tiles, and put repaired ones in."""
    src = PMTiles(src_path)
    by_key = {}
    for f in fixes:
        by_key.setdefault(f.key, []).append(f)
    changed_tiles = {}   # tile id -> parsed Tile, edited
    moves = {}           # row -> {"zooms": set, "tags": [(key bytes, value bytes)], "id", "layer": (name, version, extent)}
    stats = {"tiles_scanned": 0, "features_removed": 0, "parts_removed": 0}

    for tid in sorted(src.tiles):
        z, x, y = id_to_zxy(tid)
        if tile_inside_box(z, x, y):
            continue  # no point outside the box can be in this tile
        stats["tiles_scanned"] += 1
        t = src.tile(tid)
        edited = False
        for layer in t.layers:
            keys = [k.decode("utf-8") for k in layer.keys]
            kpos = [keys.index(k) if k in keys else None for k in key]
            drop = []
            for fi, feat in enumerate(layer.features):
                if feat.type != POINT:
                    continue
                pts = decode_points(feat.geometry)
                out = [not inside1(*to_lonlat(z, x, y, px, py, layer.extent)) for px, py in pts]
                if not any(out):
                    continue
                attrs = {}
                for i in range(0, len(feat.tags), 2):
                    attrs[feat.tags[i]] = value_py(layer.values[feat.tags[i + 1]])
                k = tuple(norm(attrs.get(kp)) if kp is not None else None for kp in kpos)
                cands = by_key.get(k, [])
                if len(cands) != 1:
                    raise SystemExit(f"tile {z}/{x}/{y}: a feature outside India matches {len(cands)} repairs: {k}")
                f = cands[0]
                edited = True
                if f.action == "drop-parts":
                    keep = [p for p, o in zip(pts, out) if not o]
                    stats["parts_removed"] += len(pts) - len(keep)
                    if keep:
                        del feat.geometry[:]
                        feat.geometry.extend(encode_points(keep))
                        continue
                drop.append(fi)
                if f.action in ("swap", "move"):
                    m = moves.setdefault(f.row, {"zooms": set(), "tags": None})
                    m["zooms"].add(z)
                    if m["tags"] is None:
                        m["tags"] = [(layer.keys[feat.tags[i]], layer.values[feat.tags[i + 1]].SerializeToString())
                                     for i in range(0, len(feat.tags), 2)]
                        m["id"] = feat.id if feat.HasField("id") else None
                        m["layer"] = (bytes(layer.name), layer.version, layer.extent)
            for fi in reversed(drop):
                del layer.features[fi]
            stats["features_removed"] += len(drop)
        if edited:
            changed_tiles[tid] = t

    # Put repaired features in at their new place, at the zoom levels they had.
    not_in_tiles = [f for f in fixes if f.action in ("swap", "move") and f.row not in moves]
    added = 0
    fx_by_row = {f.row: f for f in fixes}
    for row, m in moves.items():
        f = fx_by_row[row]
        name, version, extent = m["layer"]
        for z in sorted(m["zooms"]):
            for tx, ty, px, py in place_point(f.new.x, f.new.y, z, extent, buffer=5 * extent // 256):
                tid = zxy_to_id(z, tx, ty)
                if tid not in changed_tiles:
                    if tid in src.tiles:
                        changed_tiles[tid] = src.tile(tid)
                    else:
                        changed_tiles[tid] = Tile()
                t = changed_tiles[tid]
                layer = next((l for l in t.layers if l.name == name), None)
                if layer is None:
                    layer = t.layers.add()
                    layer.version, layer.name, layer.extent = version, name, extent
                kidx = {k: i for i, k in enumerate(layer.keys)}
                vidx = {v.SerializeToString(): i for i, v in enumerate(layer.values)}
                feat = layer.features.add()
                if m["id"] is not None:
                    feat.id = m["id"]
                for kb, vb in m["tags"]:
                    if kb not in kidx:
                        kidx[kb] = len(layer.keys)
                        layer.keys.append(kb)
                    if vb not in vidx:
                        vidx[vb] = len(layer.values)
                        layer.values.add().ParseFromString(vb)
                    feat.tags.extend([kidx[kb], vidx[vb]])
                feat.type = POINT
                feat.geometry.extend(encode_points([(px, py)]))
                added += 1

    out, removed = {}, set()
    for tid, t in changed_tiles.items():
        for i in reversed(range(len(t.layers))):
            if len(t.layers[i].features) == 0:
                del t.layers[i]
        if len(t.layers) == 0:
            removed.add(tid)
        else:
            out[tid] = gzip.compress(t.SerializeToString(), mtime=0)
    removed &= set(src.tiles)
    stats.update(features_added=added, tiles_changed=len(out), tiles_removed=len(removed),
                 repaired_rows_not_in_old_tiles=len(not_in_tiles))
    big = max((len(v) for v in out.values()), default=0)
    stats["largest_changed_tile_kb"] = round(big / 1024, 1)
    write_pmtiles(src, dst_path, out, removed, bounds)
    src.close()
    return stats, moves


def tile_features(pm, tid, key):
    """Every feature in a tile as (signature, key values, decoded points)."""
    out = []
    if tid not in pm.tiles:
        return out
    z, x, y = id_to_zxy(tid)
    for layer in pm.tile(tid).layers:
        keys = [k.decode("utf-8") for k in layer.keys]
        for feat in layer.features:
            tags = [(keys[feat.tags[i]], layer.values[feat.tags[i + 1]].SerializeToString())
                    for i in range(0, len(feat.tags), 2)]
            sig = (bytes(layer.name), layer.extent, feat.id if feat.HasField("id") else None, feat.type,
                   tuple(feat.geometry), tuple(sorted(tags)))
            attrs = {k: value_py(layer.values[feat.tags[i + 1]])
                     for i, k in ((i, keys[feat.tags[i]]) for i in range(0, len(feat.tags), 2))}
            pts = [to_lonlat(z, x, y, px, py, layer.extent) for px, py in decode_points(feat.geometry)]
            out.append((sig, tuple(norm(attrs.get(c)) for c in key), pts))
    return out


def check_pmtiles(src_path, dst_path, fixes, key):
    a, b = PMTiles(src_path), PMTiles(dst_path)
    for k in ("clustered", "internal_compression", "tile_compression", "tile_type", "min_zoom", "max_zoom",
              "center_zoom", "center_lon", "center_lat"):
        assert a.h[k] == b.h[k], f"header {k} changed"
    ma, mb = dict(a.meta), dict(b.meta)
    ma.pop("antimeridian_adjusted_bounds", None)
    mb.pop("antimeridian_adjusted_bounds", None)
    assert ma == mb, "metadata changed beyond the bounds"
    by_key = {f.key: f for f in fixes}
    same = diff = gone = new = 0
    for tid in sorted(set(a.tiles) | set(b.tiles)):
        if tid in a.tiles and tid in b.tiles and a.raw(tid) == b.raw(tid):
            same += 1
            continue
        diff += 1
        where = "tile %d/%d/%d" % id_to_zxy(tid)
        fa, fb = tile_features(a, tid, key), tile_features(b, tid, key)
        count_b = {}
        for sig, _, _ in fb:
            count_b[sig] = count_b.get(sig, 0) + 1
        for sig, k, pts in fa:
            if count_b.get(sig, 0) > 0:
                count_b[sig] -= 1
                continue
            # went away or changed: must be a repaired row that had a point outside the box
            assert k in by_key, f"{where}: a feature that is not a repaired row changed"
            assert not all(inside1(*p) for p in pts), f"{where}: a feature inside India changed"
            gone += 1
        count_a = {}
        for sig, _, _ in fa:
            count_a[sig] = count_a.get(sig, 0) + 1
        for sig, k, pts in fb:
            if count_a.get(sig, 0) > 0:
                count_a[sig] -= 1
                continue
            # new or changed: must be a repaired row, now wholly inside the box, where the Parquet puts it
            f = by_key.get(k)
            assert f is not None and f.new is not None, f"{where}: a feature appeared that is not a repaired row"
            assert all(inside1(*p) for p in pts), f"{where}: a repaired feature is still outside India"
            want = shapely.get_coordinates(f.new)
            tol = 2 * 360 / ((1 << id_to_zxy(tid)[0]) * sig[1])  # two tile units
            for lon, lat in pts:
                d = np.hypot(want[:, 0] - lon, want[:, 1] - lat).min()
                assert d < tol, f"{where}: a repaired feature is {d:.5f}° from its new position"
            new += 1
    a.close()
    b.close()
    return {"tiles_same": same, "tiles_different": diff, "features_gone_or_changed": gone,
            "features_new_or_changed": new}


# --------------------------------------------------------------------------

def find_7z(given):
    for cand in [given, "7z", "7zz", "7za", r"C:\Program Files\7-Zip\7z.exe"]:
        if cand and shutil.which(cand):
            return shutil.which(cand)
    raise SystemExit("7-Zip not found: install it or pass --sevenzip")


def main():
    global Tile
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset", choices=sorted(DATASETS))
    ap.add_argument("src", help="folder with the three release files")
    ap.add_argument("out", help="folder for the repaired files")
    ap.add_argument("--tracks", help="IR_Tracks.parquet (track-pois)")
    ap.add_argument("--states", help="SOI_States.parquet (lift-stations, habitations)")
    ap.add_argument("--sevenzip", help="path to 7z")
    args = ap.parse_args()
    if args.dataset == "track-pois" and not args.tracks:
        ap.error("track-pois needs --tracks IR_Tracks.parquet")
    if args.dataset in ("lift-stations", "habitations") and not args.states:
        ap.error(f"{args.dataset} needs --states SOI_States.parquet")
    sevenzip = find_7z(args.sevenzip)
    Tile = _tile_class()
    cfg = DATASETS[args.dataset]
    name, key = cfg["name"], cfg["key"]
    src ={ext: os.path.join(args.src, name + ext) for ext in (".parquet", ".geojsonl.7z", ".pmtiles")}
    dst = {ext: os.path.join(args.out, name + ext) for ext in src}
    for p in src.values():
        if not os.path.exists(p):
            raise SystemExit("missing " + p)
    os.makedirs(args.out, exist_ok=True)

    fixes = RULES[args.dataset](src[".parquet"], args)
    keys = [f.key for f in fixes]
    assert len(set(keys)) == len(keys), "the key columns don't tell the broken rows apart"
    counts = {}
    for f in fixes:
        counts[f.action] = counts.get(f.action, 0) + 1
    print(f"{name}: {len(fixes)} rows to repair: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))

    with open(os.path.join(args.out, name + ".changes.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["row"] + key + ["action", "old_position", "new_position", "note"])
        for f in fixes:
            w.writerow([f.row, *f.key, f.action, shapely.to_wkt(f.old, rounding_precision=7),
                        "" if f.new is None else shapely.to_wkt(f.new, rounding_precision=7), f.note])

    bounds = write_parquet(src[".parquet"], dst[".parquet"], fixes)
    print(f"  parquet written; extent {', '.join(f'{v:.4f}' for v in bounds)}")
    lines = patch_geojsonl(src[".geojsonl.7z"], dst[".geojsonl.7z"], name, fixes, key, sevenzip)
    print(f"  geojsonl written ({lines:,} lines)")
    stats, moves = patch_pmtiles(src[".pmtiles"], dst[".pmtiles"], fixes, key, bounds)
    print("  pmtiles written: " + ", ".join(f"{k} {v}" for k, v in stats.items()))

    print("checking against the originals")
    n = check_parquet(src[".parquet"], dst[".parquet"], fixes)
    print(f"  parquet: only the {n} repaired rows differ, only in geometry")
    n, c = check_geojsonl(src[".geojsonl.7z"], dst[".geojsonl.7z"], name, fixes, key, sevenzip)
    print(f"  geojsonl: {c} of {n:,} lines differ, only in geometry")
    r = check_pmtiles(src[".pmtiles"], dst[".pmtiles"], fixes, key)
    print("  pmtiles: " + ", ".join(f"{k} {v}" for k, v in r.items()))
    for ext, p in dst.items():
        print(f"  {os.path.basename(p)}  {os.path.getsize(p):,} bytes (was {os.path.getsize(src[ext]):,})")


if __name__ == "__main__":
    main()
