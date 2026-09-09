# Changelog

All notable changes to this dataset repository will be documented here.

## [Unreleased]

### Added
- Map Maker (`docs/maps/`): paste or upload a spreadsheet and get a choropleth of India, one state, or one district at state, district or sub-district level; PNG, SVG, PDF and CSV export
- Map Maker text assets (title, subtitle, note, source) with per-item font, size, style, colour and position; map zoom and pan; frame styles; draggable overlays with collision-free initial placement
- Map Maker name matching: common spelling variants resolve automatically, and unmatched or ambiguous names get a picker with suggestions; chosen matches are remembered
- `scripts/build-map-layers.py` to regenerate the simplified TopoJSON layers from the LGD release files

## [1.0.0] - 2026-03-07

### Added
- Initial release with data from 6 source repositories
- Administrative boundaries: country through habitation level
- Electoral boundaries: assembly and parliamentary constituencies
- Census 2011 boundaries and historical district series (1941-2024)
- Environmental data: forests, coastal regulation zones, land use
- Infrastructure: PMGSY rural roads and habitations
- Urban: municipal ward boundaries for 28 cities
- Postal: pincode boundaries
- Police: station jurisdiction boundaries (select states)
- Survey of India index maps and reference boundaries
- GitHub Pages data catalog
- Machine-readable metadata for all datasets
