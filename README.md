# India Geodata

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-blue.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Data validation](https://img.shields.io/badge/metadata-validated-brightgreen.svg)](#)

A unified, structured collection of India's openly-licensed geospatial data — administrative boundaries, electoral maps, census geometries, environmental zones, infrastructure networks, urban municipal data, and more.

Browse and download at **[india-geodata](https://yashveeeeeer.github.io/india-geodata)**

---

## What's here

| Category | Coverage | Formats | Size |
|---|---|---|---|
| [Administrative boundaries](data/administrative/) | Country, States, Districts, Subdistricts, Blocks, Panchayats, Villages, Habitations | Parquet, PMTiles, GeoJSONL, Shapefile | ~27 GB |
| [Electoral boundaries](data/electoral/) | Assembly Constituencies, Parliamentary Constituencies | Shapefile, GeoJSON, Parquet, PMTiles | ~300 MB |
| [Census](data/census/) | 2011 admin units, Historical districts (1941–2024) | Parquet, PMTiles, CSV | ~1.1 GB |
| [Environment](data/environment/) | Forests, Coastal Regulation Zones, Land use | Parquet, PMTiles, GeoJSON | ~7.7 GB |
| [Infrastructure](data/infrastructure/) | Rural roads (PMGSY), Block boundaries, Habitations | Shapefile (ZIP) | ~1.3 GB |
| [Urban](data/urban/) | Municipal wards (28 cities), Slums, ULB boundaries | GeoJSON, KML, Parquet, PMTiles | ~430 MB |
| [Postal](data/postal/) | Pincode boundaries | Shapefile, Parquet, PMTiles | ~700 MB |
| [Police](data/police/) | Station jurisdictions (select states) | Parquet, PMTiles | ~96 MB |
| [Survey of India](data/survey-of-india/) | Index maps, Outline maps, Reference boundaries | Shapefile, PDF | ~119 MB |
| [Remote Sensing](data/remote-sensing/) | District-level VIIRS nighttime lights (2012–2024) | CSV, GeoJSON | ~353 MB |
| [External Datasets](data/external/) | SHRUG: socioeconomic data for 500K+ villages | CSV, Stata, Shapefile | [DDL portal](https://www.devdatalab.org/shrug_download/) |

Total: approximately 1,260 files across 7 aggregated source collections and curated external links.

---

## Quick start

**Small files** are stored directly in this repository under [`data/`](data/).
Clone or download individual directories as needed.

**Large files** (administrative boundaries, forests, coastal zones, etc.)
are distributed through [GitHub Releases](../../releases).
Each release tag corresponds to a data category.

```bash
# Download all state boundary files
gh release download admin/states --dir ./downloads/states

# Download only parquet files for districts
gh release download admin/districts --pattern "*.parquet" --dir ./downloads/districts

# Download everything for forests
gh release download environment/forests --dir ./downloads/forests

# List all available releases
gh release list
```

To download all release assets at once, use the helper script:

```bash
python scripts/download-releases.py
```

---

## Repository layout

```
data/
  administrative/     States, Districts, Subdistricts, Blocks, Panchayats,
                      Villages, Habitations, Divisions
  electoral/          Assembly and Parliamentary Constituencies
  census/             Census 2011 boundaries, Historical district series
  environment/        Forests, Coastal zones, Land use
  infrastructure/     Rural roads (PMGSY/GeoSadak)
  urban/              Municipal wards, Slum boundaries, Localities
  postal/             Pincode boundaries
  police/             Police station jurisdictions
  survey-of-india/    SOI index maps and reference boundaries
  remote-sensing/     Satellite nighttime lights (VIIRS)
  external/           Curated links to SHRUG and other platforms

docs/                 GitHub Pages source
scripts/              Validation, build, and download scripts
LICENSES/             License texts for all included data
```

Each data directory contains a `README.md` with dataset documentation
and a `metadata.json` with machine-readable metadata.

---

## Data sources

This repository consolidates data from the following open-data projects and government portals:

| Source | Maintainer | License | Data |
|---|---|---|---|
| [indian_admin_boundaries](https://github.com/ramSeraph/indian_admin_boundaries) | ramSeraph | CC0 1.0 | Administrative boundaries from LGD, SOI, Bhuvan, PMGSY, FSI, NCSCM |
| [datameet/maps](https://github.com/datameet/maps) | DataMeet | CC BY 4.0 | Country, State, District, Constituency boundaries, SOI index maps |
| [datameet/pmgsy-geosadak](https://github.com/datameet/pmgsy-geosadak) | DataMeet | India OGL | Rural road network and habitation data |
| [datameet/landuse_maps](https://github.com/datameet/landuse_maps) | DataMeet | CC-BY-SA 2.5 | Land use classification maps |
| [datameet/INDIA_PINCODES](https://github.com/datameet/INDIA_PINCODES) | DataMeet | — | Postal code boundaries |
| [datameet/Municipal_Spatial_Data](https://github.com/datameet/Municipal_Spatial_Data) | DataMeet | CC BY 4.0 | Municipal ward boundaries for 27 cities |
| [NOAA VIIRS DNB](https://eogdata.mines.edu/products/vnl/) | NOAA / EOG | Public domain | Nighttime light satellite imagery |
| [india-district-nightlights-viirs](https://github.com/yashveeeeeer/india-district-nightlights-viirs) | yashveeeeeer | MIT | District-level nightlight statistics pipeline |
| [SHRUG](https://www.devdatalab.org/shrug) | Development Data Lab | CC BY-NC-SA 4.0 | Socioeconomic data for 500K+ villages (external link) |

Government data sources include: Survey of India, Local Government Directory (MoPR), ISRO Bhuvan, Forest Survey of India, National Centre for Sustainable Coastal Management, GatiShakti, eGramSwaraj, Swachh Bharat Mission, the Election Commission of India, and NOAA Earth Observation Group.

---

## Formats

| Format | Extension | Use case |
|---|---|---|
| **Parquet** | `.parquet` | Columnar analysis in Python, R, DuckDB, QGIS |
| **PMTiles** | `.pmtiles` | Browser-based map viewing, cloud-optimized tiles |
| **GeoJSONL** | `.geojsonl.7z` | Streaming GeoJSON processing (7z compressed) |
| **Shapefile** | `.shp` `.dbf` `.shx` `.prj` | Legacy GIS software (QGIS, ArcGIS, MapInfo) |
| **GeoJSON** | `.geojson` | Web mapping, GitHub preview, lightweight analysis |
| **TopoJSON** | `.topo.json` | Compact web maps with topology preservation |
| **KML** | `.kml` | Google Earth, Google Maps |
| **CSV** | `.csv` | Tabular data, spreadsheets |

---

## License

This repository is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Individual datasets carry their own licenses as documented in their
`metadata.json` files. See the [`LICENSES/`](LICENSES/) directory for full license texts.

---

## Citation

```bibtex
@misc{india_geodata,
  title = {India Geodata: Unified Geospatial Data Repository},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/yashveeeeeer/india-geodata}
}
```

See [`CITATION.cff`](CITATION.cff) for machine-readable citation metadata.

---

## Contributing

Corrections, dataset suggestions, and documentation improvements are welcome.
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Legal notice

For official political maps of India, the Survey of India maps are the
authoritative reference. This repository aggregates publicly available
geospatial data under open licenses and is intended for research,
analysis, and educational purposes.

Relevant policy documents:
- [National Data Sharing and Access Policy 2012](https://dst.gov.in/sites/default/files/gazetteNotificationNDSAP.pdf)
- [Indian Geospatial Guidelines 2021](https://dst.gov.in/sites/default/files/Final%20Approved%20Guidelines%20on%20Geospatial%20Data_0.pdf)
- [National Geospatial Policy 2022](https://www.surveyofindia.gov.in/webroot/UserFiles/files/National%20Geospatial%20Policy.pdf)
