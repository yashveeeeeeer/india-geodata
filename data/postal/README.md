# Postal / Pincode Boundary Data

Pincode-level boundary datasets for India, from both community and government sources.

## In-repo Files

### pincodes-datameet/

Split shapefile archives from the DataMeet pincode boundaries project.
Each ZIP contains shapefile components for a subset of pincodes.

## Release Files

**Tag:** `postal/boundaries`

| Dataset | Description | Format |
|---------|-------------|--------|
| PincodeBoundaries | Pincode boundary polygons | Parquet, PMTiles, GeoJSONL.7z |
| Datagov_Pincode_Boundaries | data.gov.in pincode boundaries | Parquet, PMTiles, GeoJSONL.7z |
| GSDL_Pincodes | Geospatial Delhi pincode boundaries | Parquet, PMTiles, GeoJSONL.7z |

### Download

```bash
gh release download postal/boundaries --repo <owner>/india-geodata
```

## Sources

- **DataMeet** -- Community-sourced pincode boundaries
- **data.gov.in** -- Government open data portal
- **Geospatial Delhi Limited (GSDL)** -- Delhi pincode boundaries

## License

- Release files: **CC0** (Public Domain)
- DataMeet in-repo files: see DataMeet project license
