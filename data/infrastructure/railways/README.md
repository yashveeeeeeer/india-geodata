# Indian Railways

Comprehensive Indian railway geospatial data from multiple government sources.

All files are distributed via GitHub Releases.

## Release Tag

`infra/railways`

## Datasets

| Dataset | Description | Source |
|---------|-------------|--------|
| IR_Tracks | Indian Railway track lines | IR GeoPortal |
| IR_Track_POIs | Level crossings, bridges, and track points of interest | IR GeoPortal |
| IR_Stations | Indian Railway station locations | IR GeoPortal |
| SOI_Railway_Tracks | Railway tracks from Survey of India maps | Survey of India |
| SOI_Railway_Sidings | Railway sidings | Survey of India |
| SOI_Railway_Stations | Railway station locations | Survey of India |
| SOI_metros | Metro track lines | Survey of India |
| GatiShakti_Railway_Lands | Railway land parcels | GatiShakti |
| GatiShakti_Railway_stations | Railway station locations | GatiShakti |
| GatiShakti_Railway_tracks | Railway tracks | GatiShakti |
| GatiShakti_Dedicated_Freight_Corridors | Dedicated freight corridor lines | GatiShakti |
| GatiShakti_Railway_Goods_Sheds | Goods shed locations | GatiShakti |
| Bhuvan_Railway_bridges | Railway bridge locations | Bhuvan |
| INDIAN_RAILWAYS | Railway network (GeoJSON) | datta07/INDIAN-SHAPEFILES |

Each dataset (except the GeoJSON) is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~1.5 GB

### Repaired: IR_Track_POIs

1,009 of the 698,972 points sat far outside India, as far off as 19°S or 119°N.
The files were repaired in November 2026. 999 of these points have their real
position back, taken from the row's own `latitude`/`longitude` or
`xcoord`/`ycoord` columns. Each one was checked first: it sits near a track of
the same railway zone in IR_Tracks, or near other points on the same section at
the same kilometre. The other 10 have no position that could be checked, so
they now have no geometry; their other columns are kept. Nothing else in the
files changed. The fix is
[`scripts/repair-points-outside-india.py`](../../../scripts/repair-points-outside-india.py).

## Download

```bash
gh release download infra/railways --repo yashveeeeeeer/india-geodata
```

## Sources

- **Indian Railways GeoPortal** — https://gis.indianrailways.gov.in/
- **Survey of India** — https://indiamaps.gov.in/
- **PM GatiShakti National Master Plan** — https://bharatmaps.gov.in/
- **ISRO Bhuvan** — https://bhuvan.nrsc.gov.in/
- **indian_transport** by ramSeraph — https://github.com/ramSeraph/indian_transport
- **INDIAN-SHAPEFILES** by datta07 — https://github.com/datta07/INDIAN-SHAPEFILES

## License

**CC0 1.0** (Public Domain)
