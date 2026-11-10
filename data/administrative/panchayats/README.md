# Panchayat Boundaries

Panchayat-level administrative boundaries of India.

## Files

All files are distributed via GitHub Releases under the tag **`admin/panchayats`**.

| File | Source | Format |
|------|--------|--------|
| `LGD_Panchayats.parquet` | Local Government Directory | Parquet |
| `LGD_Panchayats.pmtiles` | Local Government Directory | PMTiles |
| `LGD_Panchayats.geojsonl.7z` | Local Government Directory | GeoJSONL (7z) |
| `bhuvan_panchayats.parquet` | Bhuvan (ISRO) | Parquet |
| `bhuvan_panchayats.pmtiles` | Bhuvan (ISRO) | PMTiles |
| `bhuvan_panchayats.geojsonl.7z` | Bhuvan (ISRO) | GeoJSONL (7z) |
| `egramswaraj_activities.parquet` | eGramSwaraj | Parquet |
| `egramswaraj_activities.pmtiles` | eGramSwaraj | PMTiles |
| `egramswaraj_activities.geojsonl.7z` | eGramSwaraj | GeoJSONL (7z) |

**Total**: 9 files (~4.2 GB)

### Repaired: egramswaraj_activities

5 of the 7,360,307 activities had 1 or 2 of their points at 0°N 0°E, off the
coast of Africa, which made "Zoom to layer" in QGIS take in Africa. The files
were repaired in November 2026: those 6 points are gone, and the 5 activities
keep their other points, which are in India. Nothing else in the files changed.
The fix is
[`scripts/repair-points-outside-india.py`](../../../scripts/repair-points-outside-india.py).

### Known problem: points just outside India

About 1,500 points, in about 900 activities, still sit outside India's outline.
Most are within a kilometre of the border or coast. About 280 are more than 5 km
out, some in neighbouring countries, and are probably wrong. They are left as
they are, because nothing in the row says where they should be.

### Download

```bash
gh release download admin/panchayats -R <owner>/india-geodata
```

## Sources

| Source | Description |
|--------|-------------|
| LGD | Local Government Directory, Ministry of Panchayati Raj |
| Bhuvan | ISRO Bhuvan geoportal |
| eGramSwaraj | eGramSwaraj portal (activity/asset locations) |

## Coordinate Reference System

WGS 84 (EPSG:4326)

## License

CC0 (Public Domain)
