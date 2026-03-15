# National Highways (MoRTH)

National highway network, toll plazas, and Multi-Modal Logistics Parks (MMLP) from the Ministry of Road Transport and Highways.

All files are distributed via GitHub Releases.

## Release Tag

`infra/national-highways`

## Datasets

| Dataset | Description | Format | Source |
|---------|-------------|--------|--------|
| GatiShakti_MORTH_National_Highways | National highway polylines | Parquet, PMTiles, GeoJSONL.7z | MoRTH via GatiShakti |
| GatiShakti_MORTH_Toll_Plazas | Toll plaza locations | Parquet, PMTiles, GeoJSONL.7z | MoRTH via GatiShakti |
| GatiShakti_MORTH_MMLP_lines | MMLP line features | Parquet, PMTiles, GeoJSONL.7z | MoRTH via GatiShakti |
| GatiShakti_MORTH_MMLP_polygons | MMLP polygon features | Parquet, PMTiles, GeoJSONL.7z | MoRTH via GatiShakti |
| INDIA_NATIONAL_HIGHWAY | National highway network (GeoJSON) | GeoJSON | datta07/INDIAN-SHAPEFILES |

## Download

```bash
gh release download infra/national-highways --repo yashveeeeeer/india-geodata
```

## Sources

- **Ministry of Road Transport and Highways (MoRTH)** via PM GatiShakti National Master Plan
- **indian_transport** by ramSeraph — https://github.com/ramSeraph/indian_transport
- **INDIAN-SHAPEFILES** by datta07 — https://github.com/datta07/INDIAN-SHAPEFILES

## License

**CC0 1.0** (Public Domain) for GatiShakti data. See individual files for details.
