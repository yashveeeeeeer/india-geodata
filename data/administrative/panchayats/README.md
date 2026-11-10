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

### Known problem: egramswaraj_activities

182 of the 7,360,307 activity points sit outside India: 4 at 0°N 0°E, off the
coast of Africa, and 178 just outside India's border or coast. The 0°N 0°E
points make "Zoom to layer" in QGIS take in Africa. To drop those four, keep
only points east of 68°E (in QGIS: Processing → Extract/clip by extent).

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
