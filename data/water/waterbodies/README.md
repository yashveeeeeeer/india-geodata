# Lakes, Reservoirs & Tanks

Polygon and point geometries of surface water bodies — lakes, reservoirs, tanks, and ponds — from WRIS, Survey of India topographic maps, and the Amrit Sarovar Water Observatory, with water body names, type, area, and temporal extent.

All files are distributed via GitHub Releases.

## Release Tag

`water/waterbodies`

## Datasets

| Dataset | Description | Source |
|---------|-------------|--------|
| Amrit_Sarovar_Water_Observatory_Ponds | Pond locations from the Amrit Sarovar observatory | Amrit Sarovar |
| combined_timeseries.csv.7z | Time-series data for monitored water bodies | Amrit Sarovar |
| SOI_Lakes | Lake polygons from Survey of India maps | Survey of India |
| SOI_Tanks | Tank polygons from Survey of India maps | Survey of India |
| SOI_Tank_Points | Tank point locations | Survey of India |
| WRIS_Lakes | Lake polygons from WRIS | India-WRIS |
| WRIS_Reservoirs | Reservoir polygons from WRIS | India-WRIS |
| WRIS_Waterbodies | General water body polygons from WRIS | India-WRIS |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~2 GB

## Download

```bash
gh release download water/waterbodies --repo yashveeeeeer/india-geodata
```

## Sources

- **India-WRIS** — https://indiawris.gov.in/
- **Survey of India** — https://indiamaps.gov.in/
- **Amrit Sarovar Water Observatory** — https://amritsarovar.gov.in/

## License

**CC0 1.0** (Public Domain)
