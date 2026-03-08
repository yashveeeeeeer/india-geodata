# Contributing to India Geodata

Thanks for your interest in improving this dataset collection.

## Ways to contribute

- **Report data errors** — Incorrect boundaries, misattributed features, outdated information
- **Suggest new datasets** — Open-licensed Indian geospatial data we should include
- **Improve documentation** — Fix typos, add attribute descriptions, clarify source notes
- **Add metadata** — Help fill in `metadata.json` files with attribute tables and coverage details

## Reporting data issues

Use the [Data correction](../../issues/new?template=data_correction.md) issue template. Please include:

1. Which dataset contains the error (path or release tag)
2. The specific feature or geographic area affected
3. What the correct data should be
4. A source reference (government gazette, official notification, etc.) if available

## Suggesting a new dataset

Use the [Dataset request](../../issues/new?template=data_request.md) issue template. Include the data source URL, publisher, license, and geographic coverage.

Requirements for inclusion:
- Must be openly licensed (CC0, CC BY, OGL, or equivalent)
- Must cover Indian geography
- Must be from a verifiable source (government, academic, or established community project)

## Adding data via pull request

1. Fork the repository
2. Add data files under the appropriate `data/{category}/{level}/` directory
3. Create a `metadata.json` following the schema used by existing datasets
4. Create or update the directory `README.md`
5. Run `python scripts/validate-metadata.py` to check your metadata
6. Submit a pull request with a clear description of the dataset

## Style guide

- Directory names: lowercase, hyphen-separated (`census-2011`, `rural-roads`)
- Preserve original filenames from source data
- One `metadata.json` and one `README.md` per leaf data directory
- All coordinates in WGS 84 (EPSG:4326) unless noted
- Keep commit messages descriptive and concise

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful and constructive.
