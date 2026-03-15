# Infrastructure Data

Transport and infrastructure geospatial datasets for India — roads, railways, and inland waterways.

## Sub-datasets

| Directory | Description | Source |
|-----------|-------------|--------|
| `rural-roads/` | PMGSY rural road network, habitations, and facilities (Shapefiles) | Ministry of Rural Development (GeoSadak) |
| `national-highways/` | National highway network, toll plazas, and MMLP | MoRTH via GatiShakti, datta07 |
| `soi-roads/` | SOI road network, tracks, bridges, tolls, passes, and structures | Survey of India |
| `nic-roads/` | NIC/Bharatmaps road network | NIC |
| `ml-roads/` | ML-detected roads (Microsoft + Facebook) | Microsoft, Meta |
| `urban-roads/` | Urban road center-lines and bridges (AMRUT, Bhuvan, TS CDMA) | MoHUA, ISRO, CDMA Telangana |
| `pmgsy-roads/` | Enhanced PMGSY road data (Parquet, PMTiles, GeoJSONL) with proposals and bridges | PMGSY GeoSadak, GatiShakti |
| `railways/` | Railway tracks, stations, sidings, metros, freight corridors, goods sheds, bridges | IR GeoPortal, SOI, GatiShakti, Bhuvan, datta07 |
| `inland-waterways/` | Waterway routes, navigation canals, facilities, locks, ferries | WRIS, Survey of India |

## Sources

- **Ministry of Rural Development** — Pradhan Mantri Gram Sadak Yojana (PMGSY) via GeoSadak portal
- **Ministry of Road Transport and Highways (MoRTH)** — via PM GatiShakti
- **Survey of India** — Topographic maps (roads and transport structures)
- **National Informatics Centre (NIC)** — Bharatmaps
- **Microsoft Road Detections** / **Facebook MapWithAI** — ML satellite-derived roads
- **AMRUT / Bhuvan NUIS / CDMA Telangana** — Urban road networks
- **Indian Railways GeoPortal** — Rail tracks, stations, POIs
- **WRIS** — Inland waterways
- **indian_transport** by ramSeraph — https://github.com/ramSeraph/indian_transport
- **INDIAN-SHAPEFILES** by datta07 — https://github.com/datta07/INDIAN-SHAPEFILES

## License

See individual sub-dataset READMEs for licensing details.
