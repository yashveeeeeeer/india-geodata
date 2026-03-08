# Parliamentary Constituency Boundaries

Lok Sabha (Parliamentary) constituency boundaries of India.

## In-Repository Files

### National

The `national/` subfolder contains files from DataMeet:

| File | Description |
|------|-------------|
| `national/india_pc_2019.*` | Parliamentary Constituencies shapefile (2019) |
| `national/india_pc_2019_simplified.geojson` | Simplified GeoJSON for web use |

### ECI State-wise

The `eci-statewise/` subfolder contains per-state boundary files sourced from
the Election Commission of India.

## Release Files

Available under the GitHub release tag **`electoral/constituencies`**.

| File | Source | Format |
|------|--------|--------|
| `LGD_Parliament_Constituencies.parquet` | Local Government Directory | Parquet |
| `LGD_Parliament_Constituencies.pmtiles` | Local Government Directory | PMTiles |
| `LGD_Parliament_Constituencies.geojsonl.7z` | Local Government Directory | GeoJSONL (7z) |
| `Susewind_Parliament_Constituencies_2014.parquet` | Raphael Susewind | Parquet |
| `Susewind_Parliament_Constituencies_2014.pmtiles` | Raphael Susewind | PMTiles |
| `Susewind_Parliament_Constituencies_2014.geojsonl.7z` | Raphael Susewind | GeoJSONL (7z) |

### Download

```bash
gh release download electoral/constituencies -R <owner>/india-geodata
```

## Sources

| Source | Description |
|--------|-------------|
| DataMeet | National parliamentary constituency shapefile (2019) |
| ECI | Election Commission of India, state-wise files |
| LGD | Local Government Directory, Ministry of Panchayati Raj |
| Susewind | Raphael Susewind's 2014 delimitation boundaries |

## Coordinate Reference System

WGS 84 (EPSG:4326)

## License

- **DataMeet files**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Release files**: CC0 (Public Domain)
