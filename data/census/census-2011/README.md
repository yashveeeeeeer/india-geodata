# Census 2011 Administrative Boundaries

Administrative boundary datasets at village, sub-district, and district levels from Census 2011.
All files are distributed via GitHub Releases only (not stored in the repository).

## Release Tag

`census/2011`

## Datasets

| Dataset | Description | Format |
|---------|-------------|--------|
| Census_Villages | Village boundaries (Census 2011) | Parquet, PMTiles, GeoJSONL.7z |
| Districts_2011 | District boundaries | Parquet, PMTiles, GeoJSONL.7z |
| SubDistricts_2011 | Sub-district (tehsil/taluk) boundaries | Parquet, PMTiles, GeoJSONL.7z |
| shrug-village-pc11 | SHRUG village-level boundaries | Parquet, PMTiles, GeoJSONL.7z |
| shrug-subdistrict-pc11 | SHRUG sub-district-level boundaries | Parquet, PMTiles, GeoJSONL.7z |
| shrug-district-pc11 | SHRUG district-level boundaries | Parquet, PMTiles, GeoJSONL.7z |
| PC11_TV_DIR.csv.7z | Census 2011 town/village directory | CSV (7z compressed) |
| shrug-readme.md | SHRUG dataset documentation | Markdown |

**Total:** ~20 files, ~1 GB

## Download

```bash
gh release download census/2011 --repo <owner>/india-geodata
```

## Sources

- **Census of India** -- Official 2011 administrative boundaries
- **Development Data Lab** -- SHRUG (Socioeconomic High-resolution Rural-Urban Geographic) dataset

## License

- SHRUG data: **CC-BY-NC-SA 4.0** (Development Data Lab)
- All other data: **CC0** (Public Domain)
