# Coastal Regulation Zone (CRZ) Boundaries

Coastal Regulation Zone boundaries, regulation lines, and coastal zone management plan data.
All files are distributed via GitHub Releases only.

## Release Tag

`environment/coastal`

## Datasets

| Dataset | Source | Description |
|---------|--------|-------------|
| NCSCM_CRZ_Regulation_Lines | NCSCM | CRZ regulation lines (HTL/LTL) |
| NCSCM_CRZ_Regulation_Zones | NCSCM | CRZ zone classifications |
| Bharatmaps_Parivesh_CRZ | Bharatmaps/Parivesh | CRZ regulatory zones |
| Bharatmaps_Parivesh_CRZ_Lines | Bharatmaps/Parivesh | CRZ regulation lines |
| Bharatmaps_Parivesh_CRZ_2019 | Bharatmaps/Parivesh | CRZ 2019 notification zones |
| NCSCM_Goa_CRZ_Map | NCSCM | Goa CRZ map |
| CZMP-2019-Landuse-Goa | NCSCM | Goa CZMP 2019 land use classification |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~21 files, ~3.2 GB

## Download

```bash
gh release download environment/coastal --repo <owner>/india-geodata
```

To download a specific dataset:

```bash
gh release download environment/coastal --repo <owner>/india-geodata --pattern "NCSCM_CRZ_Regulation_Zones*"
```

## Sources

- **National Centre for Sustainable Coastal Management (NCSCM)** -- CRZ mapping and CZMP data
- **Bharatmaps / Parivesh (MoEFCC)** -- CRZ regulatory boundaries

## License

**CC0** (Public Domain)
