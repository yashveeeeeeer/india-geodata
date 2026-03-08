# Forest Boundaries

Forest administrative divisions, reserved forest areas, wildlife sanctuaries, and eco-sensitive zone
boundaries across India. All files are distributed via GitHub Releases only.

## Release Tag

`environment/forests`

## Datasets

| Dataset | Source | Description |
|---------|--------|-------------|
| FSI_Beats | Forest Survey of India | Forest beat boundaries |
| FSI_Divisions | Forest Survey of India | Forest division boundaries |
| FSI_Ranges | Forest Survey of India | Forest range boundaries |
| FSI_Circles | Forest Survey of India | Forest circle boundaries |
| Bharatmaps_RFA | Bharatmaps | Reserved Forest Areas |
| Bharatmaps_Parivesh | Bharatmaps/Parivesh | Wildlife areas, Eco Sensitive Zones |
| GatiShakti_Forests | PM GatiShakti | Forest boundaries |
| GatiShakti_Wildlife_Sanctuaries | PM GatiShakti | Wildlife sanctuary boundaries |
| GatiShakti_Eco_Sensitive_Zones | PM GatiShakti | Eco-sensitive zone boundaries |
| NCOG_Eco_Sensitive_Zones | NCOG | Eco-sensitive zone boundaries |
| SOI_Forests | Survey of India | Forest boundaries |

Each dataset is available in Parquet, PMTiles, and GeoJSONL.7z formats.

**Total:** ~39 files, ~4.4 GB

## Download

```bash
gh release download environment/forests --repo <owner>/india-geodata
```

To download a specific dataset:

```bash
gh release download environment/forests --repo <owner>/india-geodata --pattern "FSI_Divisions*"
```

## Sources

- **Forest Survey of India (FSI)** -- Administrative forest divisions
- **Bharatmaps / Parivesh** -- MoEFCC regulated areas
- **PM GatiShakti National Master Plan** -- Infrastructure planning layers
- **Survey of India (SOI)** -- Topographic forest boundaries
- **National Centre for Geo-informatics (NCOG)** -- Eco-sensitive zones

## License

**CC0** (Public Domain)
