# India Pincode Boundaries

Pincode (postal code) boundaries for India from DataMeet. A single comprehensive
shapefile covering all postal codes, distributed as a split ZIP archive.

Download every file here into one folder. `india_pincodes.shp.zip` with the
`.z01`-`.z05` parts is one split archive: open the `.shp.zip` with 7-Zip, Keka or
The Unarchiver to get `india_pincodes.shp`. The `.dbf`, `.shx`, `.prj`, `.cpg`,
`.sbn` and `.sbx` are separate zips; unzip each of them into the same folder.

This is the file exactly as DataMeet published it, so Pakistan-occupied Kashmir,
Gilgit-Baltistan and Aksai Chin are blank: they have no PIN codes. The
`DataMeet_Pincodes` files in the `postal/boundaries` release are the same data as
single files (Shapefile, Parquet, GeoJSONL), with those areas filled in as
"No PIN code" shapes so Jammu & Kashmir and Ladakh follow India's official
boundary. See
[the postal README](../README.md#datameet_pincodes-and-indias-official-boundary).

- **Format:** Shapefile (`india_pincodes.shp` and associated files), split ZIP
- **Source:** DataMeet

## Columns

| Column | What it holds |
|--------|---------------|
| `pincode` | The 6-digit PIN code. One shape per PIN code. |
| `state` | State name. A few list more than one, e.g. "Dadra & Nagar Haveli, Gujarat" |
| `district` | District name. A few list more than one |
| `officename` | Name of the post office the PIN code belongs to |
| `officetype` | Mostly `H.O` head office, `S.O` sub office or `B.O` branch office |

These columns are as DataMeet published them; a handful of rows have odd values.

## Labelling by PIN code in QGIS

QGIS labels a layer with the first column that has "name" in it. Here that is
`officename`, so turning labels on shows post office names, not PIN codes.

`india_pincodes.qml` fixes this. Keep it in the same folder as
`india_pincodes.shp` and QGIS applies it when you add the layer: it opens
labelled by `pincode`, with labels showing once you zoom in past 1:5,000,000.
A layer already saved in a QGIS project keeps its old style; use Layer
Properties > Style > Load Style to apply it there.

Without the style file, open Layer Properties > Labels, pick Single Labels and
set Value to `pincode`.

See the [repository README](../../../README.md) for full documentation.
