# Hydrological Boundaries

Polygon boundaries of India's hydrological units — river basins, sub-basins, watersheds, micro-watersheds, and priority micro-watersheds — from WRIS and SLUSI for water resource planning and management.

All files are distributed via GitHub Releases.

## Release Tag

`water/hydro-boundaries`

## Datasets

| Dataset | Description | Source |
|---------|-------------|--------|
| SLUSI_MicroWatersheds | Micro-watershed boundaries | SLUSI |
| SLUSI_Priority_MicroWatersheds | Priority micro-watershed boundaries | SLUSI |
| WRIS_Basin | River basin boundaries | India-WRIS |
| WRIS_SubBasin | Sub-basin boundaries | India-WRIS |
| WRIS_Watershed | Watershed boundaries | India-WRIS |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~2 GB

## Download

```bash
gh release download water/hydro-boundaries --repo yashveeeeeer/india-geodata
```

## Sources

- **India-WRIS** — https://indiawris.gov.in/
- **SLUSI (Soil and Land Use Survey of India)** — https://slusi.dacnet.nic.in/

## License

**CC0 1.0** (Public Domain)
