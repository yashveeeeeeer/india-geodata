# Postal / Pincode Boundary Data

Pincode-level boundary datasets for India, from both community and government sources.

## In-repo Files

### pincodes-datameet/

DataMeet's pincode shapefile as they published it, as one shapefile split into
ZIP parts. For the same data as single files, with Jammu & Kashmir and Ladakh
filled out to India's official boundary, use `DataMeet_Pincodes` from the
release below.

## Release Files

**Tag:** `postal/boundaries`

| Dataset | Description | Format |
|---------|-------------|--------|
| DataMeet_Pincodes | DataMeet pincode boundaries, with Jammu & Kashmir and Ladakh filled out to India's official boundary (see below) | Parquet, GeoJSONL.7z, Shapefile (.shp.zip), QGIS style (.qml) |
| PincodeBoundaries | Pincode boundary polygons | Parquet, PMTiles, GeoJSONL.7z |
| Datagov_Pincode_Boundaries | data.gov.in pincode boundaries | Parquet, PMTiles, GeoJSONL.7z |
| GSDL_Pincodes | Geospatial Delhi pincode boundaries | Parquet, PMTiles, GeoJSONL.7z |

QGIS labels a layer by the first column with "name" in it, so the DataMeet and
data.gov.in files show post office names when labels are turned on. To show PIN
codes, set the label Value to `pincode` (DataMeet) or `Pincode` (data.gov.in
Parquet and GeoJSONL; PMTiles layers have no such setting). The DataMeet folder
ships `india_pincodes.qml`, which does this for you. For `DataMeet_Pincodes`,
the release has `DataMeet_Pincodes.qml`: keep it in the same folder as the
Parquet, GeoJSONL or `.shp.zip` file. The shapefile zip also has the style
inside, which QGIS uses once you unzip it (not when it opens the zip directly).

### DataMeet_Pincodes and India's official boundary

DataMeet's shapes stop where India Post's PIN codes stop. Pakistan-occupied
Kashmir, Gilgit-Baltistan and Aksai Chin are inside India's official boundary but
have no PIN codes, so plotting the DataMeet file leaves them blank.
`DataMeet_Pincodes` keeps all 19,928 DataMeet shapes as published and adds two
shapes, one for Jammu & Kashmir and one for Ladakh. They cover the parts of
those territories, as drawn in the Survey of India state boundaries
(`SOI_States` in the `admin/states` release), that no pincode shape covers:
Pakistan-occupied Kashmir in Jammu & Kashmir (12,242 km²); Gilgit-Baltistan,
Aksai Chin, the Shaksgam valley, Siachen and a few border strips in Ladakh
(104,617 km²). Those two rows have an empty `pincode`, `officename`
"No PIN code", and a new `source` column that says "Survey of India outline"
(every other row says "DataMeet"). Pieces under 5 km² where the two sources draw
a line slightly differently are left out.

Only Jammu & Kashmir and Ladakh are filled. Elsewhere DataMeet's outer lines and
the Survey of India's differ by about 7,600 km² in all, mostly coastline (the
Sundarbans) and border strips around places that do have PIN codes, so those are
left as they are.

The Parquet and Shapefile keep every DataMeet coordinate unchanged. The GeoJSONL
is text, so a coordinate can differ in its 13th decimal place.

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

- Release files: **CC0** (Public Domain), except the two below
- `Datagov_Pincode_Boundaries`: published by data.gov.in, under the Government
  Open Data License – India
- DataMeet in-repo files and `DataMeet_Pincodes`: the source,
  [datameet/INDIA_PINCODES](https://github.com/datameet/INDIA_PINCODES) (a copy of
  [justinelliotmeyers/INDIA_PINCODES](https://github.com/justinelliotmeyers/INDIA_PINCODES)),
  states no licence. The two shapes `DataMeet_Pincodes` adds are cut from the
  Survey of India state boundaries.
