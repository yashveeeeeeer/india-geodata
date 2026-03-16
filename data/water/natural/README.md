# Natural Water Features

Point and polygon geometries of natural water features across India — springs, waterfalls, geothermal springs, and islands from Survey of India topographic maps, Bhuvan, and the National Geoscience Data Repository.

All files are distributed via GitHub Releases.

## Release Tag

`water/natural`

## Datasets

| Dataset | Description | Source |
|---------|-------------|--------|
| Bhuvan_Islands | Island polygon boundaries from Bhuvan | ISRO Bhuvan |
| NGDR_Geothermal_Springs | Geothermal spring point locations | NGDR (Bhukosh) |
| SOI_Springs | Spring point locations from Survey of India maps | Survey of India |
| SOI_Springs_compiled | Compiled spring locations | Survey of India |
| SOI_Waterfalls | Waterfall point locations from Survey of India maps | Survey of India |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~14 MB

## Download

```bash
gh release download water/natural --repo yashveeeeeer/india-geodata
```

## Sources

- **Survey of India** — https://indiamaps.gov.in/
- **ISRO Bhuvan** — https://bhuvan.nrsc.gov.in/
- **NGDR (Bhukosh)** — https://bhukosh.gsi.gov.in/

## License

**CC0 1.0** (Public Domain)
