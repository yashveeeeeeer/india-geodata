# Locality Boundary Data

Locality-level boundary data for Indian cities.
All files are distributed via GitHub Releases only.

## Release Tag

`urban/boundaries`

## Datasets

| Dataset | Description | Source |
|---------|-------------|--------|
| GSDL_Localities | Locality boundaries for Delhi | Geospatial Delhi Limited |
| WB_AMRUT_Localities | Locality boundaries for AMRUT cities | World Bank |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

## Download

```bash
gh release download urban/boundaries --repo <owner>/india-geodata --pattern "*Localities*"
```

## Sources

- **Geospatial Delhi Limited (GSDL)** -- Delhi locality boundaries
- **World Bank AMRUT** -- Urban development programme datasets

## License

**CC0** (Public Domain)
