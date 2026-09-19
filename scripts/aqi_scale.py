#!/usr/bin/env python3
"""Turn CPCB AQI sub-index values back into concentrations.

data.gov.in resource 3b01bcb8 is titled "Real time Air Quality *Index*", and
that is exactly what it reports: `avg_value` is the pollutant's AQI sub-index,
not the concentration. Stored as-is it sits on a different scale from the
seventeen years of concentrations behind it — CO comes out about forty-five
times too high, so the map paints the whole country red.

Checked against the archive, median across ~180 cities for the same September:

    pollutant   raw feed   inverted   archive
    PM2.5          38.9      23.3      25.6
    PM10           52.7      51.7      60.9
    NO2            15.0      12.0      12.7
    CO             28.0       0.56      0.60
    OZONE          16.0      16.0      24.6
    NH3             4.0      16.0      16.3

CO and NH3 settle it. PM10 and ozone are the identity in their lowest bands, so
they neither confirm nor deny.

The sub-index is piecewise linear in concentration, so inverting it is the same
interpolation run backwards. CPCB's own table starts each band one unit above
the last; this uses the continuous form instead, which is monotone, invertible
and within a unit of the published numbers.

Concentrations are µg/m³, except CO in mg/m³ — the units the page already uses.
Above 500 the scale has no defined top, so the last band's slope carries on.
"""

# pollutant -> (concentration breakpoints, matching sub-index breakpoints)
SCALE = {
    "PM2.5": ([0, 30, 60, 90, 120, 250, 380], [0, 50, 100, 200, 300, 400, 500]),
    "PM10":  ([0, 50, 100, 250, 350, 430, 510], [0, 50, 100, 200, 300, 400, 500]),
    "NO2":   ([0, 40, 80, 180, 280, 400, 520], [0, 50, 100, 200, 300, 400, 500]),
    "CO":    ([0, 1, 2, 10, 17, 34, 51], [0, 50, 100, 200, 300, 400, 500]),
    "OZONE": ([0, 50, 100, 168, 208, 748, 1288], [0, 50, 100, 200, 300, 400, 500]),
    "NH3":   ([0, 200, 400, 800, 1200, 1800, 2400], [0, 50, 100, 200, 300, 400, 500]),
}


def to_concentration(pollutant, index):
    """One sub-index value as a concentration. Returns None for anything we
    cannot place, so a caller can drop the reading rather than invent one."""
    scale = SCALE.get(pollutant)
    if scale is None or index is None:
        return None
    try:
        i = float(index)
    except (TypeError, ValueError):
        return None
    if i != i or i < 0:
        return None

    conc, idx = scale
    for k in range(len(idx) - 1):
        if i <= idx[k + 1]:
            span = idx[k + 1] - idx[k]
            frac = (i - idx[k]) / span if span else 0.0
            return conc[k] + frac * (conc[k + 1] - conc[k])

    # off the top of the table: carry the last band's slope
    slope = (conc[-1] - conc[-2]) / (idx[-1] - idx[-2])
    return conc[-1] + (i - idx[-1]) * slope


def series_to_concentration(pollutants, values):
    """The same thing for two aligned pandas Series, kept here so the fetch and
    the rebuild cannot drift apart."""
    return [to_concentration(p, v) for p, v in zip(pollutants, values)]
