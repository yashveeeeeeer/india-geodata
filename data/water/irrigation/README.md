# Irrigation Infrastructure

Point, line, and polygon geometries of irrigation infrastructure across India — canals, dams, aqueducts, siphons, sluices, weirs, wells, tube wells, hand pumps, and WRIS anicuts from Survey of India, BharatMaps, and WRIS.

All files are distributed via GitHub Releases.

## Release Tag

`water/irrigation`

## Datasets

| Dataset | Description | Source |
|---------|-------------|--------|
| Bharatmaps_Canals | Canal lines from BharatMaps | BharatMaps |
| Bharatmaps_Canals_with_names | Named canal lines from BharatMaps | BharatMaps |
| Bharatmaps_Canal_Polygons | Canal polygon areas from BharatMaps | BharatMaps |
| Bharatmaps_Dams | Dam locations from BharatMaps | BharatMaps |
| SOI_Aqueducts | Aqueduct lines from Survey of India maps | Survey of India |
| SOI_Canals | Canal lines from Survey of India maps | Survey of India |
| SOI_Drains | Drain lines from Survey of India maps | Survey of India |
| SOI_Hand_Pumps | Hand pump point locations | Survey of India |
| SOI_Siphons | Siphon point locations | Survey of India |
| SOI_Sluices | Sluice point locations | Survey of India |
| SOI_Tube_Wells | Tube well point locations | Survey of India |
| SOI_Weirs | Weir point locations | Survey of India |
| SOI_Weir_Locks | Weir lock point locations | Survey of India |
| SOI_Wells | Well point locations | Survey of India |
| WRIS_Anicuts | Anicut locations from WRIS | India-WRIS |
| WRIS_Dams | Dam locations from WRIS | India-WRIS |
| WRIS_LIFT_Stations | Lift irrigation station locations from WRIS | India-WRIS |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~1.2 GB

## Download

```bash
gh release download water/irrigation --repo yashveeeeeer/india-geodata
```

## Sources

- **Survey of India** — https://indiamaps.gov.in/
- **PM GatiShakti (BharatMaps)** — https://bharatmaps.gov.in/
- **India-WRIS** — https://indiawris.gov.in/

## License

**CC0 1.0** (Public Domain)
