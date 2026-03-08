# Habitation and Settlement Data

Habitation-level and settlement-area datasets for India, including point
locations and built-up area polygons from multiple sources.

## Files

All files are distributed via GitHub Releases under the tag **`admin/habitations`**.

| File | Source | Format |
|------|--------|--------|
| `PMGSY_Habitations.parquet` | PMGSY | Parquet |
| `PMGSY_Habitations.pmtiles` | PMGSY | PMTiles |
| `PMGSY_Habitations.geojsonl.7z` | PMGSY | GeoJSONL (7z) |
| `SOI_HumanSettlements_HUTS.parquet` | Survey of India | Parquet |
| `SOI_HumanSettlements_HUTS.pmtiles` | Survey of India | PMTiles |
| `SOI_HumanSettlements_HUTS.geojsonl.7z` | Survey of India | GeoJSONL (7z) |
| `SOI_HumanSettlements_VILLAGE_BLOCKS.parquet` | Survey of India | Parquet |
| `SOI_HumanSettlements_VILLAGE_BLOCKS.pmtiles` | Survey of India | PMTiles |
| `SOI_HumanSettlements_VILLAGE_BLOCKS.geojsonl.7z` | Survey of India | GeoJSONL (7z) |
| `SOI_places.parquet` | Survey of India | Parquet |
| `SOI_places.pmtiles` | Survey of India | PMTiles |
| `SOI_places.geojsonl.7z` | Survey of India | GeoJSONL (7z) |
| `karmashapes.parquet` | KarmaShapes | Parquet |
| `karmashapes.pmtiles` | KarmaShapes | PMTiles |
| `karmashapes.geojsonl.7z` | KarmaShapes | GeoJSONL (7z) |
| `GatiShakti_Settlement_Areas.parquet` | PM GatiShakti | Parquet |
| `GatiShakti_Settlement_Areas.pmtiles` | PM GatiShakti | PMTiles |
| `GatiShakti_Settlement_Areas.geojsonl.7z` | PM GatiShakti | GeoJSONL (7z) |
| `ESRI_Sentinel2_Builtup_Area.parquet` | ESRI / Sentinel-2 | Parquet |
| `ESRI_Sentinel2_Builtup_Area.pmtiles` | ESRI / Sentinel-2 | PMTiles |
| `ESRI_Sentinel2_Builtup_Area.geojsonl.7z` | ESRI / Sentinel-2 | GeoJSONL (7z) |
| `JJM.parquet` | Jal Jeevan Mission | Parquet |
| `JJM.pmtiles` | Jal Jeevan Mission | PMTiles |
| `JJM.geojsonl.7z` | Jal Jeevan Mission | GeoJSONL (7z) |

**Total**: 29 files (~11.7 GB) -- includes additional variants not listed above.

### Download

```bash
gh release download admin/habitations -R <owner>/india-geodata
```

## Sources

| Source | Description |
|--------|-------------|
| PMGSY | Pradhan Mantri Gram Sadak Yojana habitation points |
| SOI | Survey of India -- human settlements (HUTS, VILLAGE_BLOCKS) and places |
| KarmaShapes | Settlement boundary polygons |
| PM GatiShakti | Settlement area polygons from the GatiShakti platform |
| ESRI / Sentinel-2 | Built-up area derived from Sentinel-2 satellite imagery |
| JJM | Jal Jeevan Mission habitation data |

## Coordinate Reference System

WGS 84 (EPSG:4326)

## License

CC0 (Public Domain)
