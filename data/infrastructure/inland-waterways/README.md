# Inland Waterways

Inland waterway routes, navigation infrastructure, and ferry services from WRIS and Survey of India.

All files are distributed via GitHub Releases.

## Release Tag

`infra/inland-waterways`

## Datasets

| Dataset | Description | Source |
|---------|-------------|--------|
| WRIS_Waterways | Inland waterway routes | WRIS |
| WRIS_Waterways_with_depth | Waterways with minimum depth | WRIS |
| WRIS_Navigation_Canals | Navigation canals | WRIS |
| WRIS_Waterway_facilities | Terminals, lighthouses, jetties, beacons | WRIS |
| WRIS_Spurs | Spur structures | WRIS |
| SOI_Navigation_Locks | Navigation lock locations | Survey of India |
| SOI_Ferries | Ferry route lines | Survey of India |
| SOI_Steamer_service | Steamer service routes | Survey of India |
| SOI_Waterway_facilities | Lighthouses, jetties, buoys, beacons | Survey of India |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~500 MB

## Download

```bash
gh release download infra/inland-waterways --repo yashveeeeeer/india-geodata
```

## Sources

- **Water Resources Information System (WRIS)** — https://indiawris.gov.in/
- **Survey of India** — https://indiamaps.gov.in/
- **indian_transport** by ramSeraph — https://github.com/ramSeraph/indian_transport

## License

**CC0 1.0** (Public Domain)
