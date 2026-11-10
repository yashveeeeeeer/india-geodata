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

QGIS labels a layer by the first column with "name" in it, so the DataMeet and
data.gov.in files show post office names when labels are turned on. To show PIN
codes, set the label Value to `pincode` (DataMeet) or `Pincode` (data.gov.in
Parquet and GeoJSONL; PMTiles layers have no such setting). The DataMeet folder
ships `india_pincodes.qml`, which does this for you.

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
  codes) or `DataMeet_Pincodes`.
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

- Release files: **CC0** (Public Domain)
- DataMeet in-repo files: see DataMeet project license
