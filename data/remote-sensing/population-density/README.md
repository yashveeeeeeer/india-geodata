# Gridded Population Density (WorldPop)

1 km resolution gridded population density for India (2020) from WorldPop. Modeled from Census 2011 data and remotely-sensed landcover using random forest-based dasymetric redistribution. Values represent estimated people per square kilometre.

## Data

### GitHub Release: `remote-sensing/population-density` (~17 MB)

| File | Format | Size | Description |
|------|--------|------|-------------|
| `ind_pd_2020_1km.tif` | GeoTIFF | 17 MB | 1 km gridded population density (people/km²) |

**Download:**

```bash
gh release download remote-sensing/population-density --repo yashveeeeeer/india-geodata
```

## Technical details

- **Resolution:** ~1 km (30 arc-seconds)
- **Projection:** WGS 84 (EPSG:4326)
- **Unit:** People per square kilometre
- **Year:** 2020
- **Method:** Random forest-based dasymetric redistribution of Census 2011 population counts, informed by satellite-derived landcover, roads, settlement patterns, and other ancillary data

## Sources

- **WorldPop** — https://hub.worldpop.org/geodata/summary?id=41746 (University of Southampton)

## License

[Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
