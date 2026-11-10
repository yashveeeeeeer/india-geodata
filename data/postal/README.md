# Postal / Pincode Boundary Data

Pincode-level boundary datasets for India, from both community and government sources.

## In-repo Files

### pincodes-datameet/

DataMeet's pincode shapefile as they published it, as one shapefile split into
ZIP parts. For the same data as single files, filled out to India's official
boundary, use `DataMeet_Pincodes` from the release below.

## Release Files

**Tag:** `postal/boundaries`

| Dataset | Description | Format |
|---------|-------------|--------|
| DataMeet_Pincodes | DataMeet pincode boundaries, filled out to India's official boundary (see below) | Parquet, GeoJSONL.7z, Shapefile (.shp.zip), QGIS style (.qml) |
| PincodeBoundaries | Pincode boundary polygons | Parquet, PMTiles, GeoJSONL.7z |
| Datagov_Pincode_Boundaries | data.gov.in pincode boundaries | Parquet, PMTiles, GeoJSONL.7z |
| GSDL_Pincodes | Geospatial Delhi pincode boundaries | Parquet, PMTiles, GeoJSONL.7z |

QGIS labels a layer by the first column with "name" in it, so the DataMeet and
data.gov.in files show post office names when labels are turned on. To show PIN
codes, set the label Value to `pincode` (DataMeet) or `Pincode` (data.gov.in
Parquet and GeoJSONL; PMTiles layers have no such setting). The DataMeet folder
ships `india_pincodes.qml`, and `DataMeet_Pincodes.shp.zip` has the same style
inside, so both do this for you.

### DataMeet_Pincodes and India's official boundary

DataMeet's shapes stop where India Post's PIN codes stop. Pakistan-occupied
Kashmir, Gilgit-Baltistan and Aksai Chin are inside India's official boundary but
have no PIN codes, so plotting the DataMeet file leaves them blank.
`DataMeet_Pincodes` keeps all 19,928 DataMeet shapes exactly as published and adds
two shapes, one for Jammu & Kashmir and one for Ladakh. They cover the parts of
those territories, as drawn in the Survey of India state boundaries
(`SOI_States` in the `admin/states` release), that no pincode shape covers.
Those two rows have an empty `pincode`, `officename` "No PIN code", and a new
`source` column that says "Survey of India outline" (every other row says
"DataMeet"). Slivers under 1 km² where the two sources draw a line slightly
differently are left out.

DataMeet's own rows date from 2018 and give `state` as "Jammu & Kashmir" for Leh
and Kargil too; the two added rows use the current territory names.

Rebuild it with `python scripts/build-datameet-pincodes.py`.

### Download

```bash
gh release download postal/boundaries --repo <owner>/india-geodata
```

## Sources

- **DataMeet** -- Community-sourced pincode boundaries
- **data.gov.in** -- Government open data portal
- **Geospatial Delhi Limited (GSDL)** -- Delhi pincode boundaries

## License

- Release files: **CC0** (Public Domain), except `DataMeet_Pincodes`
- DataMeet in-repo files and `DataMeet_Pincodes`: see DataMeet project license
