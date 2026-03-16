# Soil Map of India (FAO DSMW)

Polygon-based soil classification map of India extracted from the FAO-UNESCO Digital Soil Map of the World (DSMW).

## Data

| File | Format | Size | Features |
|------|--------|------|----------|
| INDIA_SOIL_MAP_FAO.geojson | GeoJSON | 2.5 MB | 634 polygons |

## Attributes

| Column | Description |
|--------|-------------|
| SNUM | Soil mapping unit number |
| FAOSOIL | Full FAO soil classification code (e.g. `Be76-2b`) |
| DOMSOI | Dominant soil type code (e.g. `Be` = Eutric Cambisols) |
| PHASE1 | Primary soil phase modifier |
| PHASE2 | Secondary soil phase modifier |
| MISCLU1 | Miscellaneous land unit 1 |
| MISCLU2 | Miscellaneous land unit 2 |
| PERMAFROST | Permafrost indicator |
| CNTCODE | Country code |
| SQKM | Area in square kilometres |

## Major Soil Types in India

| Code | FAO Soil Name | Coverage |
|------|---------------|----------|
| I | Lithosols | Mountain and hill regions |
| Vc | Chromic Vertisols | Deccan Plateau (black cotton soils) |
| GL | Glaciers | Himalayan glacial areas |
| Rd | Dystric Regosols | Sandy and gravelly soils |
| Be | Eutric Cambisols | Alluvial plains |
| Lf | Ferric Luvisols | Laterite regions |
| Lc | Chromic Luvisols | Red soils of peninsular India |
| Je | Eutric Fluvisols | River floodplains |
| Ne | Eutric Nitosols | Tropical red earths |
| Lo | Orthic Luvisols | Semi-arid plateau regions |

## Source

**FAO Digital Soil Map of the World (DSMW)**
- Scale: 1:5,000,000
- Original source: FAO-UNESCO Soil Map of the World
- URL: https://data.apps.fao.org/map/catalog/srv/search?keyword=DSMW
- India features extracted from the global dataset using GeoPandas

## License

FAO Open Access — attribution required. Source: Land and Water Development Division, FAO, Rome.
