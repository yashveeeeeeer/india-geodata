# Assembly Constituency Boundaries

State Legislative Assembly constituency boundaries of India.

## In-Repository Files

### National

The `national/` subfolder contains a national-level shapefile from DataMeet:

| File | Description |
|------|-------------|
| `national/India_AC.*` | All-India Assembly Constituencies shapefile |

### ECI State-wise

The `eci-statewise/` subfolder contains per-state shapefiles sourced from the
Election Commission of India.

## Release Files

Available under the GitHub release tag **`electoral/constituencies`**.

| File | Source | Format |
|------|--------|--------|
| `LGD_Assembly_Constituencies.parquet` | Local Government Directory | Parquet |
| `LGD_Assembly_Constituencies.pmtiles` | Local Government Directory | PMTiles |
| `LGD_Assembly_Constituencies.geojsonl.7z` | Local Government Directory | GeoJSONL (7z) |
| `Susewind_Assembly_Constituencies_2014.parquet` | Raphael Susewind | Parquet |
| `Susewind_Assembly_Constituencies_2014.pmtiles` | Raphael Susewind | PMTiles |
| `Susewind_Assembly_Constituencies_2014.geojsonl.7z` | Raphael Susewind | GeoJSONL (7z) |

### Download

```bash
gh release download electoral/constituencies -R <owner>/india-geodata
```

## Sources

| Source | Description |
|--------|-------------|
| DataMeet | National assembly constituency shapefile |
| ECI | Election Commission of India, state-wise shapefiles |
| LGD | Local Government Directory, Ministry of Panchayati Raj |
| Susewind | Raphael Susewind's 2014 delimitation boundaries |

## Coordinate Reference System

WGS 84 (EPSG:4326)

## License

- **DataMeet files**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Release files**: CC0 (Public Domain)
