# Changelog

All notable changes to this dataset repository will be documented here.

## [1.1.0] - 2026-09-09

### Added
- Map Maker (`docs/maps/`): paste or upload a spreadsheet and get a choropleth of India, one state, or one district at state, district or sub-district level; PNG, SVG, PDF and CSV export
- Map Maker text assets (title, subtitle, note, source) with per-item font, size, style, colour and position; map zoom and pan; frame styles; draggable overlays with collision-free initial placement
- Map Maker name matching: common spelling variants resolve automatically, and unmatched or ambiguous names get a picker with suggestions; chosen matches are remembered and listed; guessed matches show with an undo; an unmatched-count badge sits on the map; a region list with names and codes can be downloaded
- Map Maker on phones: preview pinned to the top of the screen that shrinks while typing, touch-sized controls, pinch and Ctrl-scroll zoom, touch tooltips, share-sheet exports, an Upload button for CSV and spreadsheet files with wider file type support, spreadsheet files with title rows, percent and date cells
- Map Maker boundary layers grouped by type: administrative (states, districts, sub-districts, blocks) and electoral (parliamentary and assembly constituencies), built from the LGD release files
- Map Maker: template CSV with region codes that matches exactly when filled in and uploaded; sheet and value-column pickers for workbooks with several; project files that save and reopen a whole map; level switches to match the names pasted
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
