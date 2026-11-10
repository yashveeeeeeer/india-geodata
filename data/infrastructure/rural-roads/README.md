# PMGSY Rural Road Data

State-wise rural connectivity datasets from the Pradhan Mantri Gram Sadak Yojana (PMGSY) programme,
sourced via the GeoSadak portal. Files are stored in-repo as state-wise ZIP archives.

## Directory Structure

Data is organized into five subdirectories, each containing ZIP files for 29 states:

| Directory | Description |
|-----------|-------------|
| `block-boundaries/` | Block-level administrative boundaries (29 states) |
| `habitations/` | Rural habitation point locations (29 states) |
| `road-proposals/` | Proposed road alignments (29 states) |
| `road-network/` | Constructed road network (state ZIPs <50 MB in-repo) |
| `facilities/` | Facilities and amenities (29 states) |

## Large Files (Releases)

State-level road network files exceeding 50 MB are distributed via GitHub Releases.

**Tag:** `infra/rural-roads-large`

| State |
|-------|
| Maharashtra |
| Bihar |
| Karnataka |
| Uttarakhand |
| Rajasthan |
| West Bengal |

```bash
gh release download infra/rural-roads-large --repo <owner>/india-geodata
```

Karnataka's road network is `Karnataka.zip` in the release, like the other five
states. It used to come only in two parts: `Karnataka-split.z01` in the release
and `Karnataka-split.zip` in `road-network/`. Either part alone won't open. Both
parts are still there for old links, and together they unzip to the same
`Karnataka.zip` (159,648 roads).

## Source

**Ministry of Rural Development, Government of India** -- via GeoSadak portal

## Citation

> Ministry of Rural Development, 2022. PMGSY Rural Connectivity Datasets.

## License

**India Government Open Data License**
