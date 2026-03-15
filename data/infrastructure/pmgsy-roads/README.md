# PMGSY Roads (Enhanced Formats)

PMGSY/GeoSadak rural road network in modern geospatial formats. This complements the existing shapefile-based `rural-roads/` dataset with Parquet, PMTiles, and GeoJSONL versions, plus road proposals by phase and bridge data.

All files are distributed via GitHub Releases.

## Release Tag

`infra/pmgsy-roads`

## Datasets

| Dataset | Description |
|---------|-------------|
| pmgsy_roads | Constructed rural road network (DRRP) |
| pmgsy_roads_candidates | Candidate road proposals |
| pmgsy_roads_proposals_i | PMGSY-I road proposals |
| pmgsy_roads_proposals_ii | PMGSY-II road proposals |
| pmgsy_roads_proposals_iii | PMGSY-III road proposals |
| pmgsy_roads_proposals_rcplwea | RCPLWEA road proposals |
| GatiShakti_PMGSY_Bridges | PMGSY bridges via GatiShakti |
| GatiShakti_MORD_Bridges | MoRD bridges via GatiShakti |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~3.4 GB

## Download

```bash
gh release download infra/pmgsy-roads --repo yashveeeeeer/india-geodata
```

## Sources

- **PMGSY GeoSadak Open Data** — https://geosadak-pmgsy.nic.in/OpenData
- **PM GatiShakti National Master Plan** — https://bharatmaps.gov.in/
- **indian_transport** by ramSeraph — https://github.com/ramSeraph/indian_transport

## License

**GODL** (Government Open Data License - India)
