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
| `state` | State name |
| `district` | District name |
| `officename` | Name of the post office the PIN code belongs to |
| `officetype` | `H.O` head office, `S.O` sub office, `B.O` branch office |

## Labelling by PIN code in QGIS

QGIS labels a layer with the first column that has "name" in it. Here that is
`officename`, so turning labels on shows post office names, not PIN codes.

`india_pincodes.qml` fixes this. Keep it in the same folder as
`india_pincodes.shp` and QGIS uses it on its own: the layer opens labelled by
`pincode`, with labels showing once you zoom in past 1:5,000,000.

Without the style file, open Layer Properties > Labels, pick Single Labels and
set Value to `pincode`.

See the [repository README](../../../README.md) for full documentation.
