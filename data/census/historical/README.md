# Historical District Boundaries (1941--2001)

District-level administrative boundaries for India across decadal census years from 1941 to 2001,
along with reference datasets tracking district creation, splits, and name changes from 1951 to 2024.

## In-repo Files

| File | Description |
|------|-------------|
| `District_Timeseries_1951-2024.csv` | District-level timeseries of administrative changes |
| `District_splits_and_carveouts_1951_to_2024.csv` | Record of district splits and carve-outs |
| `New_districts_created_1951_to_2024.csv` | Newly created districts by year |
| `District_name_changes_1951_to_2021.csv` | District name changes over time |

## Release Files

**Tag:** `census/historical`

For each census year (1941, 1951, 1961, 1971, 1981, 1991, 2001), the following files are available:

| Dataset Pattern | Format |
|-----------------|--------|
| `India-State-Districts-{year}` | Parquet, PMTiles, GeoJSONL.7z |

**Total:** 21 release files + 4 in-repo CSV files

### Download

```bash
gh release download census/historical --repo <owner>/india-geodata
```

To download a specific year:

```bash
gh release download census/historical --repo <owner>/india-geodata --pattern "India-State-Districts-1971*"
```

## Sources

- Census of India (decadal census records)
- Government of India gazette notifications (district creation orders)

## License

**CC0** (Public Domain)
