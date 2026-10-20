# District-Level Nighttime Lights, DMSP + VIIRS Harmonized (1992–2025)

A long district-by-year panel of nighttime lights for **641 Census 2011 districts**, **1992 to 2025**.

Two satellites have measured night lights over India. **DMSP-OLS** covers 1992–2013. **VIIRS** covers 2012 onward. Their numbers are on different scales, so they cannot be joined as they are. One has to be converted to look like the other.

Two published datasets do this, in opposite directions. This panel puts both side by side, summed over the same districts as the [VIIRS nightlights panel](../nightlights/).

| Columns | Scale | Years | How the years were made |
|---|---|---|---|
| `dmsp_like_*` | DMSP digital number, 0–63, ~1 km pixels | 1992–2024 | **1992–2013:** real DMSP, calibrated so the satellites match each other. **2014–2024:** VIIRS converted to the DMSP scale. (Li et al. 2020) |
| `viirs_like_*` | VIIRS radiance, nW/cm²/sr, ~500 m pixels | 1992–2025 | **2013–2025:** from VIIRS. **1992–2012:** estimated from DMSP by a deep-learning model trained where the two satellites overlap. (Chen et al. 2021, Version 2) |

## Which one to use

- **`dmsp_like`** — the early years are real observations. But it is coarse, and bright city centres hit the 63 ceiling, so growth in big cities is understated.
- **`viirs_like`** — finer, no ceiling, and it reaches 2025. But 1992–2012 are model estimates of what VIIRS would have seen, not measurements.

Running both and checking that a result holds in each is the safest use.

## Files

| File | Format | Size | Description |
|------|--------|------|-------------|
| `nightlights_dmsp_viirs_district_panel.csv` | CSV | 2.4 MB | 21,794 rows: 641 districts × 34 years (1992–2025) |

## Columns

| Column | Type | Description |
|--------|------|-------------|
| `district_id` | integer | Census 2011 district code — same as the [VIIRS panel](../nightlights/), so the two join directly |
| `district_name` | string | District name |
| `state_name` | string | State or Union Territory |
| `year` | integer | 1992–2025 |
| `dmsp_like_source` | string | `dmsp` (1992–2013) or `viirs_converted` (2014 on) |
| `dmsp_like_sum` | integer | Sum of digital numbers over all the district's pixels |
| `dmsp_like_sum_gt7` | integer | Sum over pixels **above 7** only — use this one for trends (see notes) |
| `dmsp_like_mean` | float | Mean digital number per pixel |
| `dmsp_like_max` | integer | Brightest pixel. The top of the scale (59–63, depending on the satellite) means saturated |
| `dmsp_like_lit_share_gt7` | float | Share of the district's pixels above 7 |
| `dmsp_like_pixels` | integer | Number of ~1 km pixels in the district |
| `viirs_like_source` | string | `dmsp_reconstructed` (1992–2012) or `viirs` (2013 on) |
| `viirs_like_sum` | float | Sum of radiance over the district's pixels (nW/cm²/sr) |
| `viirs_like_mean` | float | Mean radiance per pixel |
| `viirs_like_median` | float | Median radiance per pixel |
| `viirs_like_max` | float | Brightest pixel |
| `viirs_like_pixels` | integer | Number of ~500 m pixels in the district |

`dmsp_like_*` is empty for 2025: Li et al. have not published that year yet.

## Usage notes

- **Use `dmsp_like_sum_gt7` for trends across 2013 → 2014.** In the converted VIIRS years every pixel below 7 is already zero; the DMSP years still have them. So `dmsp_like_sum` steps at the join, and the above-7 sum does not. Li et al. recommend the same cut-off.
- **Check the `*_source` column** to see whether a year is observed or converted.
- **A pixel belongs to a district when its centre falls inside it.** Sums are plain sums of pixel values, with no adjustment for pixel area. A pixel covers about a sixth less ground in Kashmir than in Kerala, which does not matter for change over time within a district.
- **`district_id` 0, "Data Not Available"**, is the part of Jammu & Kashmir that the Census 2011 map leaves without a district. It is kept so the panel matches the VIIRS panel row for row.
- Boundaries are fixed at Census 2011 for every year, so the panel is balanced. Districts created later sit inside their 2011 parent.

## How well it checks out

Compared with this repository's own [VIIRS panel](../nightlights/), which is built separately from NOAA's monthly VIIRS data:

- **District averages match.** For 2013–2024, `viirs_like_mean` and the VIIRS panel's `mean` correlate at 0.998–0.999 across districts, every year. Hyderabad, for example, is 48.4 here and 47.4 there in 2019.
- **District sums differ, as they should.** `viirs_like_sum` adds up 500 m pixels, four for every 1 km pixel in the VIIRS panel. The VIIRS panel also keeps a faint glow in unlit pixels, which this source sets to zero; in large dark districts such as Leh that glow adds up.
- **The two series here agree with each other.** The log of `dmsp_like_sum_gt7` and the log of `viirs_like_sum` correlate at 0.90–0.95 across districts in most years.

## Known steps in the series

Where a method changes, some districts jump. Check results that hinge on these years.

| Series | Years | What happens |
|---|---|---|
| `viirs_like` | 2012 → 2013 | The model hands over to real VIIRS. Most districts move little, but the brightest cities jump, because DMSP saturates there and the model cannot see how bright they really are. Kolkata's mean goes from 23.7 to 42.1. |
| `dmsp_like` | 2013 → 2014 | Real DMSP hands over to converted VIIRS. Use `dmsp_like_sum_gt7` here, not `dmsp_like_sum`. |
| all VIIRS-based | 2016 → 2017 | A sharp one-year rise: the median district goes up by about a quarter in `viirs_like` and by more in `dmsp_like`. The VIIRS panel in this repository shows it too, so it comes from the VIIRS input data, not from either conversion. |

## Rebuild

```bash
python scripts/build-nightlights-dmsp-viirs.py --download
```

This downloads the source rasters (~4.4 GB) into `.cache/ntl/` (or `--cache DIR`) and rewrites the CSV. The file lists are read from the publishers, so a newly published year is picked up by re-running it.

## Sources and citation

If you use this panel, please cite the two source datasets:

- Li, X., Zhou, Y., Zhao, M., & Zhao, X. (2020). A harmonized global nighttime light dataset 1992–2018. *Scientific Data*, 7, 168. https://doi.org/10.1038/s41597-020-0510-y — data: figshare, version 10 (1992–2024), https://doi.org/10.6084/m9.figshare.9828827.v10
- Chen, Z., Yu, B., Yang, C., Zhou, Y., Yao, S., Qian, X., Wang, C., Wu, B., & Wu, J. (2021). An extended time series (2000–2018) of global NPP-VIIRS-like nighttime light data from a cross-sensor calibration. *Earth System Science Data*, 13, 889–906. https://doi.org/10.5194/essd-13-889-2021 — Version 2 (1992–2025) described in *Journal of Remote Sensing* (2026), https://doi.org/10.34133/remotesensing.0874 — data: Harvard Dataverse, https://doi.org/10.7910/DVN/YGIVCD

District boundaries: [DataMeet](https://github.com/datameet/maps), Census 2011.

## License

CC BY 4.0, following the Li et al. data (CC BY 4.0). The Chen et al. data are CC0 1.0. District boundaries are CC BY 4.0 (DataMeet).
