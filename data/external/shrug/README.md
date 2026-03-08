# SHRUG — Socioeconomic High-resolution Rural-Urban Geographic Platform for India

The SHRUG is an open-access data platform maintained by [Development Data Lab](https://www.devdatalab.org/) (DDL), led by Sam Asher (Johns Hopkins SAIS) and Paul Novosad (Dartmouth College). It brings together dozens of datasets covering India's 500,000+ villages and 8,000+ towns over 25 years, all linked with consistent geographic identifiers.

**This dataset is not hosted in this repository.** Download it directly from DDL's portal.

## Quick links

- **Download**: [devdatalab.org/shrug_download](https://www.devdatalab.org/shrug_download/)
- **Documentation**: [docs.devdatalab.org](https://docs.devdatalab.org/)
- **Interactive Atlas**: [devdatalab.org/atlas](https://www.devdatalab.org/atlas)

## What SHRUG contains

| Module | Years | Description |
|--------|-------|-------------|
| Population Census | 1991, 2001, 2011 | Village/town demographics, amenities, public goods |
| Economic Census | 1990, 1998, 2005, 2013 | Non-farm enterprise locations and employment |
| SECC 2012 | 2012 | Socio-economic and caste census, consumption estimates |
| Nighttime Lights | 1992–2021 | DMSP (1992–2013) and VIIRS (2012–2021) luminosity |
| Forest Cover | 2000–2019 | Satellite-derived forest cover change |
| PM2.5 Pollution | multiple years | Air quality estimates |
| Elections | 1980–2018 | Legislative election results |
| PMGSY Roads | multiple years | Rural road construction program data |
| Bank Branches | multiple years | RBI bank branch locations |
| Open Polygons | 2011 | Village and town boundary geometries |

## Geographic identifiers

The SHRUG uses a unit called the **shrid** — a village or town with consistent boundaries since 1991. Villages and towns merge and split over time; shrids are aggregated to maintain consistent areas across all time periods.

Data is available at multiple levels: **village, town, subdistrict, district, and constituency**.

## Joining with india-geodata

SHRUG data can be linked to india-geodata datasets using Census 2011 district codes (`district_id` in our nightlights dataset) or village-level codes. The SHRUG documentation describes the identifier mapping in detail.

## License

**CC BY-NC-SA 4.0** — Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International. Free for non-commercial use; commercial use requires permission from DDL.

## Citation

> Asher, Sam, Tobias Lunt, Ryu Matsuura, and Paul Novosad. "Development Research at High Geographic Resolution: An Analysis of Night Lights, Firms, and Poverty in India using the SHRUG Open Data Platform." World Bank Economic Review, 2021.
