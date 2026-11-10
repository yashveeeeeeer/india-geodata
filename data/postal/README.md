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

### PincodeBoundaries: most rows are villages with no PIN code

`PincodeBoundaries` is a copy of ramSeraph's
[`postal` release](https://github.com/ramSeraph/indian_admin_boundaries/releases/tag/postal),
which he downloaded from India Post's
[PostalGIS](https://post.nic.in/postalgis/master.aspx) map and left uncleaned.

It has 248,836 rows, but only 16,867 have a PIN code. The other 231,969 have
`PIN_CODE` 0 and a blank `pincode`. Those rows are village outlines, not
pincode areas:

- Half of them share 98.9% or more of their combined area with one village in
  `LGD_Villages` (from the `admin/villages` release), and 82% share at least
  90%. Their median size is 2.1 km², close to the median village (2.4 km²).
  Only 2% are under 0.1 km², so they are not slivers.
- They sit in the gaps between the pincoded rows. The two kinds of row overlap
  by only 42 km².

It looks like PostalGIS makes each pincode shape by joining the villages given
that PIN code, and leaves villages with no PIN code yet as they are. So the
blank rows seem to be villages that had not been given a PIN code when the data
was downloaded. Most are in six states:

| State | Rows with a PIN code | Rows with PIN code 0 | Share of state area with PIN code 0 |
|-------|---------------------:|---------------------:|------------------------------------:|
| Uttar Pradesh | 2,253 | 67,926 | 63% |
| Madhya Pradesh | 161 | 48,186 | 96% |
| Bihar | 1,072 | 28,773 | 58% |
| Maharashtra | 1,564 | 25,273 | 62% |
| Assam | 513 | 14,970 | 76% |
| West Bengal | 1,069 | 7,136 | 12% |

These six hold 192,264 of the 231,969 blank rows. The file leaves out Jammu &
Kashmir, Ladakh, Himachal Pradesh, Sikkim, Chandigarh, and the north-eastern
states other than Assam and Tripura.

Because of the missing villages, many pincode shapes are smaller than the real
pincode area. Against the same PIN code in `Datagov_Pincode_Boundaries`, the
median pincode shape here is 77% as big, and the two shapes share a median of
38% of their combined area. Also, 3,324 of the PIN codes here are not
in data.gov.in's list.

The blank rows can't be filled in reliably from the other two files. About 79%
of them sit at least 90% inside one data.gov.in pincode, and about 80% inside
one DataMeet pincode. But where both files place a village, they agree on its
PIN code only 78% of the time.

What to use:

- For PIN code areas across India, use `Datagov_Pincode_Boundaries` (19,312 PIN
  codes) or `DataMeet_Pincodes`. The data.gov.in file covers all of India's
  official boundary, Jammu & Kashmir and Ladakh included.
- To keep only the pincode shapes from this file, filter on `PIN_CODE != 0`
  (16,867 rows). In QGIS, right-click the layer, choose Filter… and enter
  `"PIN_CODE" != 0`.

Licence: ramSeraph gives his copy as CC0 1.0 and asks that DataMeet and the
original government source be credited. His notes give no licence from India
Post itself.

## Sources

- **DataMeet** -- Community-sourced pincode boundaries
- **data.gov.in** -- Government open data portal
- **Geospatial Delhi Limited (GSDL)** -- Delhi pincode boundaries
- **India Post PostalGIS**, via [ramSeraph](https://github.com/ramSeraph/indian_admin_boundaries/releases/tag/postal) -- `PincodeBoundaries`

## License

- Release files: **CC0** (Public Domain), except the two below
- `Datagov_Pincode_Boundaries`: published by data.gov.in, under the Government
  Open Data License – India
- DataMeet in-repo files and `DataMeet_Pincodes`: the source,
  [datameet/INDIA_PINCODES](https://github.com/datameet/INDIA_PINCODES) (a copy of
  [justinelliotmeyers/INDIA_PINCODES](https://github.com/justinelliotmeyers/INDIA_PINCODES)),
  states no licence. The two shapes `DataMeet_Pincodes` adds are cut from the
  Survey of India state boundaries.
