# Ward Boundary Data

Ward and Urban Local Body (ULB) boundary data from national-level sources.
All files are distributed via GitHub Releases only.

## Release Tag

`urban/boundaries`

## Datasets

| Dataset | Description |
|---------|-------------|
| SBM_Wards | Ward boundaries from Swachh Bharat Mission |
| SBM_Areas | Area boundaries from Swachh Bharat Mission |
| SBM_ULBs | Urban Local Body boundaries from Swachh Bharat Mission |
| LivingAtlas_Wards | Ward boundaries from Living Atlas of the World |
| WB_AMRUT_Wards | Ward boundaries from World Bank AMRUT dataset |
| WB_AMRUT_ULBs | ULB boundaries from World Bank AMRUT dataset |
| Shillong_Wards | Ward boundaries for Shillong |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

## Download

```bash
gh release download urban/boundaries --repo <owner>/india-geodata --pattern "*Wards*"
gh release download urban/boundaries --repo <owner>/india-geodata --pattern "*ULBs*"
```

## Sources

- **Swachh Bharat Mission (SBM)** -- Urban ward and area boundaries
- **World Bank AMRUT** -- Urban Local Body and ward datasets
- **Living Atlas of the World (Esri)** -- Ward boundary layers

## License

**CC0** (Public Domain)
