# State Boundaries

State and Union Territory boundaries of India.

## In-Repository Files

The `datameet/` subfolder contains a shapefile from the DataMeet community:

| File | Description |
|------|-------------|
| `datameet/Admin2.*` | State boundaries shapefile (SHP, DBF, SHX, PRJ) |

## Release Files

Available under the GitHub release tag **`admin/states`**.

| File | Source | Format |
|------|--------|--------|
| `LGD_States.parquet` | Local Government Directory | Parquet |
| `LGD_States.pmtiles` | Local Government Directory | PMTiles |
| `LGD_States.geojsonl.7z` | Local Government Directory | GeoJSONL (7z) |
| `SOI_States.parquet` | Survey of India | Parquet |
| `SOI_States.pmtiles` | Survey of India | PMTiles |
| `SOI_States.geojsonl.7z` | Survey of India | GeoJSONL (7z) |
| `bhuvan_states.parquet` | Bhuvan (ISRO) | Parquet |
| `bhuvan_states.pmtiles` | Bhuvan (ISRO) | PMTiles |
| `bhuvan_states.geojsonl.7z` | Bhuvan (ISRO) | GeoJSONL (7z) |

### Download

```bash
gh release download admin/states -R <owner>/india-geodata
```

## Sources

| Source | Description |
|--------|-------------|
| LGD | Local Government Directory, Ministry of Panchayati Raj |
| SOI | Survey of India |
| Bhuvan | ISRO Bhuvan geoportal |
| DataMeet | DataMeet community maps |

## Coordinate Reference System

WGS 84 (EPSG:4326)

## License

- **Release files**: CC0 (Public Domain)
- **DataMeet files**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
