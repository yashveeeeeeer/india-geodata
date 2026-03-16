# Rivers & Streams

Polyline and polygon geometries of rivers, streams, and water channels across India — including SOI topographic streams, WRIS river networks, and NCOG compiled stream data with river names, basins, and flow attributes.

All files are distributed via GitHub Releases.

## Release Tag

`water/rivers`

## Datasets

| Dataset | Description | Source |
|---------|-------------|--------|
| NCOG_SOI_Streams (split: part1, part2) | Compiled stream network from NCOG/SOI | NCOG / Survey of India |
| SOI_Streams | Stream lines from Survey of India topographic maps | Survey of India |
| SOI_Water_Channels | Water channel lines | Survey of India |
| SOI_Water_Channel_Polygons | Water channel polygon areas | Survey of India |
| WRIS_Rivers | River lines from WRIS | India-WRIS |
| WRIS_River_Polygons | River polygon areas from WRIS | India-WRIS |
| WRIS_Streams | Stream lines from WRIS | India-WRIS |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats. NCOG_SOI_Streams Parquet is split into 2 parts.

**Total:** ~11.7 GB

## Download

```bash
gh release download water/rivers --repo yashveeeeeer/india-geodata
```

## Sources

- **India-WRIS** — https://indiawris.gov.in/
- **Survey of India** — https://indiamaps.gov.in/
- **NCOG (BharatMaps)** — https://bharatmaps.gov.in/

## License

**CC0 1.0** (Public Domain)
