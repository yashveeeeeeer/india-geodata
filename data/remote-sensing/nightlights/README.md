# District-Level Nighttime Lights (VIIRS)

Annual nighttime light statistics for **641 Indian districts** across **35 states and Union Territories**, derived from NOAA VIIRS Day/Night Band satellite imagery. Covers **2012–2024** (13 years of annual composites).

Nighttime lights serve as a widely-used proxy for economic activity, urbanization, electrification, and infrastructure development at sub-national scales.

## Files

### In this directory (small files)

| File | Format | Size | Description |
|------|--------|------|-------------|
| `nightlights_district_panel.csv` | CSV | 1.5 MB | Panel dataset — 8,334 rows (641 districts × 13 years) |
| `india-nightlights-timelapse.gif` | GIF | 796 KB | Animated visualization of nightlight changes |

### GitHub Release: `remote-sensing/nightlights` (~351 MB)

Year-wise GeoJSON files containing district polygons with nightlight statistics:

| File | Size |
|------|------|
| `nightlights_districts_2012.geojson` | 27 MB |
| `nightlights_districts_2013.geojson` | 27 MB |
| `nightlights_districts_2014.geojson` | 27 MB |
| `nightlights_districts_2015.geojson` | 27 MB |
| `nightlights_districts_2016.geojson` | 27 MB |
| `nightlights_districts_2017.geojson` | 27 MB |
| `nightlights_districts_2018.geojson` | 27 MB |
| `nightlights_districts_2019.geojson` | 27 MB |
| `nightlights_districts_2020.geojson` | 27 MB |
| `nightlights_districts_2021.geojson` | 27 MB |
| `nightlights_districts_2022.geojson` | 27 MB |
| `nightlights_districts_2023.geojson` | 27 MB |
| `nightlights_districts_2024.geojson` | 27 MB |

**Download:**

```bash
gh release download remote-sensing/nightlights
```

## Attributes

| Column | Type | Description |
|--------|------|-------------|
| `district_id` | string | Census 2011 district code |
| `district_name` | string | District name |
| `state_name` | string | State or Union Territory |
| `year` | integer | Year of observation (2012–2024) |
| `mean` | float | Mean nightlight radiance (nW/cm²/sr) |
| `median` | float | Median nightlight radiance |
| `sum` | float | Total radiance — proxy for economic activity |
| `min` | float | Minimum nightlight radiance |
| `max` | float | Maximum nightlight radiance |
| `std` | float | Standard deviation of radiance |
| `valid_pixel_count` | float | Number of valid satellite pixels in district |
| `log1p_mean` | float | log(1 + mean) for econometric use |
| `log1p_median` | float | log(1 + median) for econometric use |

## Usage notes

- **Prefer `median` over `mean`** — less sensitive to outliers like gas flares or transient light sources.
- **Use `sum`** to measure total light output for a district (correlates with GDP).
- **Log-transformed columns** (`log1p_mean`, `log1p_median`) are provided for right-skewed distributions in regression models.
- **Check `valid_pixel_count`** as a data quality diagnostic — low counts may indicate cloud cover or missing data.
- District boundaries follow **Census 2011** definitions. These can be joined with other india-geodata datasets using `district_id`.

## Data source

- **Satellite**: NOAA VIIRS DNB (Visible Infrared Imaging Radiometer Suite — Day/Night Band)
- **Product**: Monthly composites (VCMCFG), aggregated to annual median
- **Resolution**: 1000 metres
- **Band**: `avg_rad` (average radiance in nW/cm²/sr)
- **Boundaries**: DataMeet Census 2011 district shapefiles
- **Pipeline**: [india-district-nightlights-viirs](https://github.com/yashveeeeeer/india-district-nightlights-viirs)

## Related resources

- [Development Data Lab's SHRUG](https://www.devdatalab.org/shrug_download/) — provides pre-built nightlight data (DMSP 1992–2013 and VIIRS 2012–2021) across 500,000+ villages and 8,000 towns.

## License

MIT License (pipeline code). Satellite data governed by NOAA/EOG terms. District boundaries under CC BY 4.0 (DataMeet).
