# Village Boundaries

Village-level administrative boundaries and point locations for India.

## Files

All files are distributed via GitHub Releases under the tag **`admin/villages`**.

| File | Source | Format |
|------|--------|--------|
| `LGD_Villages.parquet` | Local Government Directory | Parquet |
| `LGD_Villages.pmtiles` | Local Government Directory | PMTiles |
| `LGD_Villages.geojsonl.7z` | Local Government Directory | GeoJSONL (7z) |
| `SOI_Villages.parquet` | Survey of India | Parquet |
| `SOI_Villages.pmtiles` | Survey of India | PMTiles |
| `SOI_Villages.geojsonl.7z` | Survey of India | GeoJSONL (7z) |
| `bhuvan_villages.parquet` | Bhuvan (ISRO) | Parquet |
| `bhuvan_villages.pmtiles` | Bhuvan (ISRO) | PMTiles |
| `bhuvan_villages.geojsonl.7z` | Bhuvan (ISRO) | GeoJSONL (7z) |
| `SOI_VILLAGE_POINT.parquet` | Survey of India | Parquet |
| `SOI_VILLAGE_POINT.pmtiles` | Survey of India | PMTiles |
| `SOI_VILLAGE_POINT.geojsonl.7z` | Survey of India | GeoJSONL (7z) |
| `Bhuvan_JK_Villages.parquet` | Bhuvan (ISRO) | Parquet |
| `Bhuvan_JK_Villages.pmtiles` | Bhuvan (ISRO) | PMTiles |
| `Bhuvan_JK_Villages.geojsonl.7z` | Bhuvan (ISRO) | GeoJSONL (7z) |

**Total**: 15 files (~4.2 GB)

### Download

```bash
gh release download admin/villages -R <owner>/india-geodata
```

## Sources

| Source | Description |
|--------|-------------|
| LGD | Local Government Directory, Ministry of Panchayati Raj |
| SOI | Survey of India (polygons and point locations) |
| Bhuvan | ISRO Bhuvan geoportal |

## Notes

- `SOI_VILLAGE_POINT` contains village centroid point geometries rather than
  polygon boundaries.
- `Bhuvan_JK_Villages` contains village boundaries specifically for Jammu &
  Kashmir.

## Coordinate Reference System

WGS 84 (EPSG:4326)

## License

CC0 (Public Domain)
