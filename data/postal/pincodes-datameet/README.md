# India Pincode Boundaries

Pincode (postal code) boundaries for India from DataMeet. A single comprehensive
shapefile covering all postal codes, distributed as a split ZIP archive.

Reassemble all `.zip` and `.z01`-`.z05` parts before extracting.

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
