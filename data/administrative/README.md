# Administrative Boundaries

This directory contains administrative boundary datasets for India at multiple
levels of the administrative hierarchy.

## Administrative Hierarchy

```
Country
  +-- States / Union Territories
        +-- Divisions
        +-- Districts
              +-- Subdistricts (Tehsils / Taluks)
              +-- Blocks
                    +-- Panchayats
                          +-- Villages
                                +-- Habitations
```

## Sub-directories

| Directory | Level | Description |
|-----------|-------|-------------|
| [country/](country/) | L0 | India national boundary |
| [states/](states/) | L1 | State and Union Territory boundaries |
| [divisions/](divisions/) | -- | State administrative divisions |
| [districts/](districts/) | L2 | District boundaries |
| [subdistricts/](subdistricts/) | L3 | Subdistrict / Tehsil / Taluk boundaries |
| [blocks/](blocks/) | L3 | Block boundaries |
| [panchayats/](panchayats/) | L4 | Panchayat boundaries |
| [villages/](villages/) | L5 | Village boundaries |
| [habitations/](habitations/) | L6 | Habitation and settlement data |

## Coordinate Reference System

All datasets use **WGS 84 (EPSG:4326)** unless otherwise noted.

## File Storage

- **Small files** (shapefiles, GeoJSON under GitHub's size limit) are stored
  directly in the repository.
- **Large files** (Parquet, PMTiles, compressed GeoJSONL) are distributed via
  **GitHub Releases**. Each sub-directory's README includes the relevant release
  tag and download instructions.

## Sources

Data is sourced from the Local Government Directory (LGD), Survey of India (SOI),
Bhuvan, Census of India, DataMeet, and other government portals. See individual
sub-directory READMEs for specific attribution and licensing.
