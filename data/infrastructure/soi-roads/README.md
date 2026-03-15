# SOI Roads and Transport Structures

Road network and transport infrastructure extracted from Survey of India topographic maps.

All files are distributed via GitHub Releases.

## Release Tag

`infra/soi-roads`

## Datasets

| Dataset | Description | Geometry |
|---------|-------------|----------|
| SOI_Roads | Road network polylines | LineString |
| SOI_Tracks | Unpaved tracks and trails | LineString |
| SOI_Bridges | Bridge locations | Point/LineString |
| SOI_Tolls | Toll locations | Point |
| SOI_Passes | Mountain pass locations | Point |
| SOI_Causeways | Causeway structures | Point/LineString |
| SOI_Culverts | Culvert structures | Point |
| SOI_Viaducts | Viaduct structures | Point/LineString |
| SOI_Fords | River ford crossings | Point |
| SOI_Routes_over_glaciers | Routes traversing glaciers | LineString |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~31 files, ~2.8 GB

## Download

```bash
gh release download infra/soi-roads --repo yashveeeeeer/india-geodata
```

## Sources

- **Survey of India** — https://indiamaps.gov.in/
- **indian_transport** by ramSeraph — https://github.com/ramSeraph/indian_transport

## License

**CC0 1.0** (Public Domain)
