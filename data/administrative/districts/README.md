# District Boundaries

District-level administrative boundaries of India.

## In-Repository Files

Census shapefiles from DataMeet are stored directly in the repository:

| Directory | Description |
|-----------|-------------|
| `census-2001/` | District boundaries from Census 2001 (shapefile) |
| `census-2011/` | District boundaries from Census 2011 (shapefile) |

## Release Files

Available under the GitHub release tag **`admin/districts`**.

| File | Source | Format |
|------|--------|--------|
| `LGD_Districts.parquet` | Local Government Directory | Parquet |
| `LGD_Districts.pmtiles` | Local Government Directory | PMTiles |
| `LGD_Districts.geojsonl.7z` | Local Government Directory | GeoJSONL (7z) |
| `SOI_Districts.parquet` | Survey of India | Parquet |
| `SOI_Districts.pmtiles` | Survey of India | PMTiles |
| `SOI_Districts.geojsonl.7z` | Survey of India | GeoJSONL (7z) |
| `bhuvan_districts.parquet` | Bhuvan (ISRO) | Parquet |
| `bhuvan_districts.pmtiles` | Bhuvan (ISRO) | PMTiles |
| `bhuvan_districts.geojsonl.7z` | Bhuvan (ISRO) | GeoJSONL (7z) |

### Download

```bash
gh release download admin/districts -R <owner>/india-geodata
```

## Sources

- **DataMeet**: Census 2001 and Census 2011 district boundaries from the
  [DataMeet Maps repository](https://github.com/datameet/maps).
- **LGD**: Local Government Directory, Ministry of Panchayati Raj.
- **SOI**: Survey of India.
- **Bhuvan**: ISRO Bhuvan geoportal.

## Coordinate Reference System

WGS 84 (EPSG:4326)

## License

- **Release files**: CC0 (Public Domain)
- **DataMeet files**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
