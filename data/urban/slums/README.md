# Slum Boundary Data

Slum delineation boundaries for select Indian cities and states.
All files are distributed via GitHub Releases only.

## Release Tag

`urban/boundaries`

## Datasets

| Dataset | Coverage | Source |
|---------|----------|--------|
| BBMP_Bangalore_Slum_Boundaries | Bangalore | BBMP |
| DUSIB_Delhi_Slum_Boundaries | Delhi | DUSIB |
| UMD_Mumbai_Slum_Boundaries_2016 | Mumbai (2016) | University of Maryland |
| TS_CDMA_Slum_Boundaries | Telangana | TS-CDMA |
| TRACGIS_GHMC_Slums | Hyderabad (GHMC) | TRACGIS |
| TNGIS_TN_Slum_Boundaries | Tamil Nadu | TNGIS |
| WB_AMRUT_Slum_boundaries | AMRUT cities | World Bank |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

## Download

```bash
gh release download urban/boundaries --repo <owner>/india-geodata --pattern "*Slum*"
```

## Sources

- **BBMP** -- Bruhat Bengaluru Mahanagara Palike
- **DUSIB** -- Delhi Urban Shelter Improvement Board
- **University of Maryland** -- Mumbai slum mapping (2016)
- **TS-CDMA** -- Telangana Centre for Data Management and Analytics
- **TRACGIS** -- Telangana State Remote Sensing Applications Centre
- **TNGIS** -- Tamil Nadu Geographic Information System
- **World Bank AMRUT** -- Urban development programme datasets

## License

**CC0** (Public Domain)
