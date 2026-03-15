# Police Data

Police-related geospatial datasets for India.

## Sub-datasets

| Directory | Description | Source |
|-----------|-------------|--------|
| `jurisdictions/` (release only) | Police station jurisdiction boundaries for select states | State GIS portals via Bharatmaps |
| `stations/` | Police station point locations across India | datta07/INDIAN-SHAPEFILES |

## Datasets

### Police Station Jurisdictions

Polygon boundaries for 8 states/regions. Available via release tag `police/jurisdictions`.

| State | Source |
|-------|--------|
| Tamil Nadu | TNGIS |
| Karnataka | KGISMAPS |
| Andhra Pradesh | APSAC |
| Telangana | TRACGIS |
| Bihar | Bhugoal |
| Rajasthan | Rajdharaa |
| Delhi | Geospatial Delhi Limited |
| Marine zones | NCOG |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~36 files, ~96 MB

### Police Station Locations

Point locations of police stations across India.

| File | Format | Size |
|------|--------|------|
| INDIA_POLICE_STATIONS.geojson | GeoJSON | ~5 MB |

## Download

```bash
# Jurisdiction boundaries (release)
gh release download police/jurisdictions --repo yashveeeeeer/india-geodata

# Station locations (in repo)
# Browse at data/police/stations/
```

## Sources

- **State GIS Portals** via Bharatmaps — https://bharatmaps.gov.in/
- **INDIAN-SHAPEFILES** by datta07 — https://github.com/datta07/INDIAN-SHAPEFILES

## License

- **Jurisdictions:** CC0 (Public Domain)
- **Stations:** See source repository for details
