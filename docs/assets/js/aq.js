/* India Air Quality — projects/air-quality/
   City proportional symbols over the state boundaries, plus the period line chart.
   Colour and breakpoints follow CPCB's AQI bands, so a reading carries its own
   yardstick without a legend lookup. */
(function () {
  'use strict';

  var root = document.getElementById('aq');
  if (!root || !window.d3 || !window.topojson) return;

  var MAPS = root.dataset.maps;
  var DATA = root.dataset.data;

  // CPCB AQI breakpoints (concentration), the 24-hour national standard, and units.
  var POLLUTANTS = {
    'PM2.5': { unit: 'µg/m³', naaqs: 60,  breaks: [30, 60, 90, 120, 250] },
    'PM10':  { unit: 'µg/m³', naaqs: 100, breaks: [50, 100, 250, 350, 430] },
    'NO2':   { unit: 'µg/m³', naaqs: 80,  breaks: [40, 80, 180, 280, 400] },
    'CO':    { unit: 'mg/m³', naaqs: 2,   breaks: [1, 2, 10, 17, 34] },
    'OZONE': { unit: 'µg/m³', naaqs: 100, breaks: [50, 100, 168, 208, 748] },
    'NH3':   { unit: 'µg/m³', naaqs: 400, breaks: [200, 400, 800, 1200, 1800] }
  };
  var BAND_COLOUR = ['#55a84f', '#a3c853', '#f7e83f', '#f29c33', '#e93f33', '#af2d24'];
  var BAND_NAME = ['Good', 'Satisfactory', 'Moderate', 'Poor', 'Very poor', 'Severe'];

  var ui = {
    map: document.getElementById('aqMap'),
    stamp: document.getElementById('aqStamp'),
    scale: document.getElementById('aqScale'),
    tip: document.getElementById('aqTip'),
    pollutants: document.getElementById('aqPollutants'),
    place: document.getElementById('aqPlace'),
    value: document.getElementById('aqValue'),
    unit: document.getElementById('aqUnit'),
    versus: document.getElementById('aqVersus'),
    stats: document.getElementById('aqStats'),
    where: document.getElementById('aqWhere'),
    panel: document.getElementById('aqPanel'),
    chart: document.getElementById('aqChart'),
    chartBtn: document.getElementById('aqChartBtn'),
    when: document.getElementById('aqWhen'),
    hint: document.getElementById('aqHint'),
    cycle: document.getElementById('aqCycle'),
    cycleBlock: document.getElementById('aqCycleBlock'),
    exceed: document.getElementById('aqExceed'),
    exceedBlock: document.getElementById('aqExceedBlock'),
    panelTabs: document.getElementById('aqPanelTabs'),
    levels: document.getElementById('aqLevels'),
    strip: document.getElementById('aqStrip'),
    prev: document.getElementById('aqPrev'),
    next: document.getElementById('aqNext'),
    download: document.getElementById('aqDownloadBtn'),
    gauge: document.getElementById('aqGauge'),
    dl: document.getElementById('aqDl'),
    dlScope: document.getElementById('aqDlScope'),
    dlPick: document.getElementById('aqDlPick'),
    dlSearch: document.getElementById('aqDlSearch'),
    dlOptions: document.getElementById('aqDlOptions'),
    dlRows: document.getElementById('aqDlRows'),
    dlRowsWrap: document.getElementById('aqDlRowsWrap'),
    dlFrom: document.getElementById('aqDlFrom'),
    dlTo: document.getElementById('aqDlTo'),
    dlGo: document.getElementById('aqDlGo'),
    find: document.getElementById('aqFind'),
    findList: document.getElementById('aqFindList')
  };

  var current = { pollutant: 'PM2.5', level: 'cities', city: null, range: null,
                 zoomState: null, zoomStateId: null, panelView: 'line', day: null, year: null };
  var cities = [];
  var stations = [];
  var statesFeat = [];
  var values = {};
  var latest = null;
  var seriesIndex = {};      // city id -> true when a built series exists
  var seriesCache = {};      // place key -> stitched doc
  var placeIndex = {};       // place key -> { name, years, cycle }
  var placeYears = {};       // place key -> year -> { pollutant: {t,v,n} }
  var coverage = null;
  var layerCache = {};
  var dailyCache = {};
  var dailyIndex = null;

  // Local calendar date. toISOString() would convert to UTC and, anywhere east of
  // Greenwich, hand back the previous day for anything before 05:30 IST.
  function isoDay(d) {
    return d.getFullYear() + '-' +
      String(d.getMonth() + 1).padStart(2, '0') + '-' +
      String(d.getDate()).padStart(2, '0');
  }

  function esc(v) {
    return String(v).replace(/[&<>"]/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch];
    });
  }

  function band(v, p) {
    var b = POLLUTANTS[p].breaks;
    for (var i = 0; i < b.length; i++) if (v <= b[i]) return i;
    return b.length;
  }
  function cfg() { return POLLUTANTS[current.pollutant]; }
  function cfg_() { return POLLUTANTS[current.pollutant]; }

  // ---------------------------------------------------------------------------
  //  Data
  // ---------------------------------------------------------------------------
  function getJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    });
  }

  var statesTopo = null;
  function loadStates() {
    return getJSON(MAPS + 'states.topo.json').then(function (topo) {
      statesTopo = topo;
      statesFeat = topojson.feature(topo, topo.objects.states).features;
    });
  }

  function loadCities() {
    return getJSON(DATA + 'cities.json').then(function (rows) { cities = rows; });
  }

  function loadStations() {
    return getJSON(DATA + 'stations.json').then(function (rows) { stations = rows; })
      .catch(function () { stations = []; });
  }

  function loadSeriesIndex() {
    return getJSON(DATA + 'series/index.json').then(function (j) {
      (j.cities || []).forEach(function (id) { seriesIndex[id] = true; });
    }).catch(function () { /* none built yet */ });
  }

  function loadCoverage() {
    return getJSON(DATA + 'coverage.json').then(function (j) { coverage = j; })
      .catch(function () { coverage = null; });
  }

  // Boundary layers are a megabyte each, so they load only when a level needs them.
  function loadLayer(level) {
    if (layerCache[level]) return Promise.resolve(layerCache[level]);
    return getJSON(MAPS + level + '.topo.json').then(function (topo) {
      var obj = topo.objects[level];
      var fc = topojson.feature(topo, obj);
      fc.features.forEach(function (f, i) { f.id = String(obj.geometries[i].id); });
      layerCache[level] = fc.features;
      return fc.features;
    });
  }

  // A unit's value is the mean of its cities, not of its stations: otherwise
  // Mumbai's 33 monitors would speak for the whole of Maharashtra.
  function unitValues(level, p) {
    if (!coverage || !coverage.stationUnit) return {};
    var key = level === 'states' ? 'state' : 'district';
    var sv = stationValues(p);
    // stage 1: average the monitors of one city inside one unit
    var groups = {};
    Object.keys(sv).forEach(function (sid) {
      var u = coverage.stationUnit[sid];
      if (!u || !u[key] || sv[sid] == null) return;
      var gk = u[key] + '|' + (u.city || sid);
      (groups[gk] = groups[gk] || { unit: u[key], vals: [] }).vals.push(sv[sid]);
    });
    // stage 2: the unit is the average of those cities, so a monitor-dense city
    // does not speak for the whole unit
    var byUnit = {};
    Object.keys(groups).forEach(function (gk) {
      var g = groups[gk];
      (byUnit[g.unit] = byUnit[g.unit] || []).push(d3.mean(g.vals));
    });
    var out = {};
    Object.keys(byUnit).forEach(function (k) {
      out[k] = { v: d3.mean(byUnit[k]), cities: byUnit[k].length };
    });
    return out;
  }

  function unitMeta(level, id) {
    var t = coverage && coverage[level === 'states' ? 'states' : 'districts'];
    return (t && t[id]) || null;
  }

  // Confidence rides on saturation: a well-monitored unit reads vivid, a thinly
  // monitored one washes out, and one with nothing measured stays blank.
  function coverOpacity(cover) {
    return 0.22 + 0.78 * Math.min(1, (cover || 0) / 60);
  }

  var dailySpan = null;
  var national = null;   // the national daily mean across every year
  // One small file holding the national daily mean for the whole record. The
  // strip is drawn from this, so it can span every year without pulling a
  // matrix per year just to draw a line.
  function loadNational() {
    return getJSON(DATA + 'daily/national.json').then(function (j) { national = j; })
      .catch(function () { national = null; });
  }

  function loadDailyIndex() {
    return getJSON(DATA + 'daily/index.json').then(function (j) {
      dailyIndex = j.pollutants || {};
      dailySpan = (j.from && j.to) ? [j.from, j.to] : null;
      var yrs = dailyIndex[current.pollutant] || [];
      current.year = yrs.length ? yrs[yrs.length - 1] : null;
    }).catch(function () { dailyIndex = null; });
  }

  function loadDaily(p, year) {
    var k = p + '-' + year;
    if (dailyCache[k]) return Promise.resolve(dailyCache[k]);
    return getJSON(DATA + 'daily/' + k + '.json').then(function (j) {
      j.index = {};
      j.t.forEach(function (d, i) { j.index[d] = i; });
      dailyCache[k] = j;
      return j;
    });
  }

  function dayStationValues(p, day) {
    var m = dailyCache[p + '-' + day.slice(0, 4)];
    if (!m) return null;
    var i = m.index[day];
    if (i == null) return null;
    var row = m.v[i], out = {};
    for (var j = 0; j < m.stations.length; j++) {
      if (row[j] != null) out[m.stations[j]] = row[j];
    }
    return out;
  }

  // Monitors rolled up to cities, so the symbol map and the historical view are
  // built from exactly the same numbers as the unit choropleth.
  function citiesFromStations(sv) {
    if (!coverage || !coverage.stationUnit) return {};
    var acc = {};
    Object.keys(sv).forEach(function (sid) {
      var u = coverage.stationUnit[sid];
      if (!u || !u.city) return;
      (acc[u.city] = acc[u.city] || []).push(sv[sid]);
    });
    var out = {};
    Object.keys(acc).forEach(function (c) { out[c] = Math.round(d3.mean(acc[c]) * 10) / 10; });
    return out;
  }

  function loadLatest() {
    return getJSON(DATA + 'latest.json').then(function (j) {
      latest = (j && j.pollutants) ? j : null;
    }).catch(function () {
      latest = null;        // feed not published yet, or unreachable
    });
  }

  function valuesFor(p) {
    var byStation = stationValues(p);
    if (Object.keys(byStation).length) return citiesFromStations(byStation);
    // Either the day's readings have not arrived yet or that fetch failed. Show
    // the live hour rather than an empty country, which reads as clean air.
    if (latest && latest.pollutants && latest.pollutants[p]) return latest.pollutants[p];
    return {};                 // nothing measured: draw nothing rather than invent it
  }

  // Per monitor. Districts need this: Delhi's 41 monitors sit in eleven districts,
  // and a single city point would leave ten of them looking unmonitored.
  function stationValues(p) {
    if (current.day) {
      var d = dayStationValues(p, current.day);
      if (d) return d;
    }
    if (latest && latest.byStation && latest.byStation[p]) return latest.byStation[p];
    return {};
  }

  // Freshness comes from the data itself, so a stalled pipeline is visible here
  // rather than hidden.
  function stampText() {
    if (!latest || !latest.updated) return 'no live readings';
    var d = new Date(latest.updated);
    if (isNaN(d)) return '';
    var age = (Date.now() - d.getTime()) / 36e5;
    var when = d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit',
                                           minute: '2-digit', hour12: false });
    return (age > 6 ? 'last updated ' : 'updated ') + when;
  }

  function loadSeries(id) {
    if (seriesCache[id]) return Promise.resolve(seriesCache[id]);
    return getJSON(DATA + 'series/' + id + '.json').then(function (j) {
      seriesCache[id] = j;
      return j;
    });
  }

  // ---------------------------------------------------------------------------
  //  Map
  // ---------------------------------------------------------------------------
  var view = null;   // { svg, g, path, projection, r, zoom, W, H }
  var spaceHeld = false;
  var pointerOverMap = false;

  function render() {
    if (!statesFeat.length || !cities.length) return;
    var W = ui.map.clientWidth, H = ui.map.clientHeight;
    if (!W || !H) return;

    var keep = view && view.t;                 // survive a re-render at the same zoom
    ui.map.innerHTML = '';
    var svg = d3.select(ui.map).append('svg')
      .attr('width', W).attr('height', H)
      .attr('viewBox', '0 0 ' + W + ' ' + H);

    var fc = { type: 'FeatureCollection', features: statesFeat };
    var projection = d3.geoMercator().fitExtent([[8, 8], [W - 8, H - 8]], fc);
    var path = d3.geoPath(projection);

    // click the empty sea to go back out
    svg.append('rect').attr('width', W).attr('height', H).attr('fill', 'transparent')
      .on('click', function () { zoomToIndia(); });

    var g = svg.append('g');

    // Context only: the land stays pale so colour means exactly one thing — the
    // reading — but it gets a real edge, so the country reads as a shape.
    var ctx = g.append('g').attr('class', 'aq-states');
    ctx.selectAll('path').data(statesFeat).enter().append('path')
      .attr('d', path)
      .attr('fill', '#f4f7fa')
      .attr('stroke', 'none')
      .style('cursor', 'pointer')
      .on('click', function (e, d) { e.stopPropagation(); zoomToState(d); });
    if (statesTopo) {
      ctx.append('path').attr('class', 'aq-inner')
        .attr('d', path(topojson.mesh(statesTopo, statesTopo.objects.states,
                                      function (a, b) { return a !== b; })))
        .attr('fill', 'none').attr('stroke', '#d3dce6').attr('stroke-width', 0.6)
        .attr('stroke-linejoin', 'round').attr('pointer-events', 'none');
      ctx.append('path').attr('class', 'aq-outer')
        .attr('d', path(topojson.mesh(statesTopo, statesTopo.objects.states,
                                      function (a, b) { return a === b; })))
        .attr('fill', 'none').attr('stroke', '#9aa9bb').attr('stroke-width', 1.1)
        .attr('stroke-linejoin', 'round').attr('pointer-events', 'none');
    }

    var p = current.pollutant;
    values = valuesFor(p);

    var defs = svg.append('defs');
    var hatch = defs.append('pattern').attr('id', 'aqHatch')
      .attr('width', 5).attr('height', 5).attr('patternUnits', 'userSpaceOnUse')
      .attr('patternTransform', 'rotate(45)');
    hatch.append('line').attr('x1', 0).attr('y1', 0).attr('x2', 0).attr('y2', 5)
      .attr('stroke', '#ffffff').attr('stroke-width', 2);

    if (current.level !== 'cities') {
      drawUnits(g, path, p);
      finishRender(svg, g, projection, path, W, H, keep);
      return;
    }

    var pts = [];
    cities.forEach(function (c) {
      var xy = projection([c.lon, c.lat]);
      if (xy && values[c.id] != null) pts.push({ c: c, x: xy[0], y: xy[1], v: values[c.id] });
    });

    // Symbols must stay small enough that clustered cities read as separate marks
    // and the coastline underneath stays visible.
    var maxV = d3.max(pts, function (d) { return d.v; }) || 1;
    var rMax = Math.max(5, Math.min(13, Math.min(W, H) / 62));
    var r = d3.scaleSqrt().domain([0, maxV]).range([0.8, rMax]);   // area ∝ value

    // Largest first, so small symbols stay visible and clickable on top of big ones.
    pts.sort(function (a, b) { return b.v - a.v; });

    g.append('g').attr('class', 'aq-dots').selectAll('circle').data(pts).enter().append('circle')
      .attr('cx', function (d) { return d.x; })
      .attr('cy', function (d) { return d.y; })
      .attr('r', function (d) { return r(d.v); })
      .attr('data-city', function (d) { return d.c.id; })
      .attr('fill', function (d) { return BAND_COLOUR[band(d.v, p)]; })
      .attr('fill-opacity', 0.82)
      // a darker rim marks cities whose series is built, so the map shows what is clickable
      .attr('stroke', function (d) { return seriesIndex[d.c.id] ? '#0f172a' : '#ffffff'; })
      .attr('stroke-width', function (d) { return seriesIndex[d.c.id] ? 1.2 : 0.6; })
      .style('cursor', 'pointer')
      .on('pointerenter pointermove', showTip)
      .on('pointerleave', hideTip)
      .on('click', function (e, d) { e.stopPropagation(); selectCity(d.c); });

    finishRender(svg, g, projection, path, W, H, keep, r);
  }

  // Units carry two things at once: the reading as colour, and how much of the
  // unit a monitor actually speaks for as saturation. Nothing measured stays blank.
  function drawUnits(g, path, p) {
    var level = current.level;
    var feats = layerCache[level] || [];
    var uv = unitValues(level, p);

    var layer = g.append('g').attr('class', 'aq-units');
    layer.selectAll('path').data(feats).enter().append('path')
      .attr('d', path)
      .attr('data-unit', function (d) { return d.id; })
      .attr('fill', function (d) {
        var e = uv[d.id];
        return e ? BAND_COLOUR[band(e.v, p)] : '#f1f5f9';
      })
      .attr('fill-opacity', function (d) {
        var e = uv[d.id];
        if (!e) return 1;
        var m = unitMeta(level, d.id);
        return coverOpacity(m && m.cover);
      })
      .attr('stroke', '#cbd5e1')
      .attr('stroke-width', 0.5)
      .style('cursor', 'pointer')
      .on('pointerenter pointermove', function (e, d) { unitTip(e, d, uv, level, p); })
      .on('pointerleave', hideTip)
      .on('click', function (e, d) { e.stopPropagation(); zoomToFeature(d); });

    // State edges ride over the district fills, so a district is readable as part
    // of somewhere rather than a loose tile.
    if (level === 'districts' && statesTopo) {
      layer.append('path')
        .attr('d', path(topojson.mesh(statesTopo, statesTopo.objects.states,
                                      function (a, b) { return a !== b; })))
        .attr('fill', 'none').attr('stroke', '#94a3b8').attr('stroke-width', 0.8)
        .attr('stroke-linejoin', 'round').attr('pointer-events', 'none');
    }

    // Thinly covered units get hatching on top, so low confidence is legible even
    // where the colour alone might still look convincing.
    layer.selectAll('path.aq-thin').data(feats.filter(function (d) {
      var m = unitMeta(level, d.id);
      return uv[d.id] && m && m.cover < 25;
    })).enter().append('path')
      .attr('class', 'aq-thin')
      .attr('d', path)
      .attr('fill', 'url(#aqHatch)')
      .attr('pointer-events', 'none');
  }

  function unitTip(e, d, uv, level, p) {
    var entry = uv[d.id];
    var m = unitMeta(level, d.id);
    var name = (m && m.name) || d.properties.name || '';
    if (!entry) {
      ui.tip.innerHTML = '<b>' + esc(name) + '</b>' +
        '<i>no monitor within ' + (coverage ? coverage.radius_km : 50) + ' km</i>';
      placeTip(e);
      return;
    }
    var bi = band(entry.v, p);
    ui.tip.innerHTML =
      '<b>' + esc(name) + '</b>' +
      '<u>' + entry.v.toFixed(entry.v < 10 ? 1 : 0) + ' <s>' + POLLUTANTS[p].unit + '</s></u>' +
      '<em style="color:' + BAND_COLOUR[bi] + '">' + BAND_NAME[bi] + '</em>' +
      '<i>' + (m ? m.stations : '?') + (m && m.stations === 1 ? ' monitor' : ' monitors') + ' in ' + entry.cities +
      (entry.cities === 1 ? ' city' : ' cities') + '</i>' +
      '<i>' + (m ? m.cover : '?') + '% of area within reach</i>';
    placeTip(e);
  }

  function finishRender(svg, g, projection, path, W, H, keep, r) {
    // Hold space and scroll. Ctrl+scroll is Chrome's own page zoom, so using it
    // here fights the browser. Drag and pinch need no modifier.
    var zoom = d3.zoom().scaleExtent([1, 40])
      .wheelDelta(function (e) {
        // gentler than d3's default, so a trackpad does not jump a whole level
        return -e.deltaY * (e.deltaMode === 1 ? 0.03 : e.deltaMode ? 1 : 0.0015);
      })
      .filter(function (e) {
        if (e.type === 'wheel') return spaceHeld;
        return !e.button;
      })
      .on('zoom', function (e) { applyTransform(e.transform); });
    svg.call(zoom).on('dblclick.zoom', null);

    view = { svg: svg, g: g, path: path, projection: projection, r: r || null,
             zoom: zoom, W: W, H: H, t: d3.zoomIdentity };
    if (keep) svg.call(zoom.transform, keep);
    markSelection();
    drawScale();
    drawCrumb();
  }

  // Symbols keep a constant screen size as you zoom, so a dense cluster such as
  // Delhi NCR separates into individual cities instead of growing into one blob.
  function applyTransform(t) {
    if (!view) return;
    if (t.k !== 1 && ui.hint) { ui.hint.hidden = true; }
    view.t = t;
    view.g.attr('transform', t);
    view.g.select('.aq-states').select('.aq-inner').attr('stroke-width', 0.6 / t.k);
    view.g.select('.aq-states').select('.aq-outer').attr('stroke-width', 1.1 / t.k);
    view.g.select('.aq-units').selectAll('path').attr('stroke-width', 0.5 / t.k);
    if (!view.r) return;
    view.g.select('.aq-dots').selectAll('circle')
      .attr('r', function (d) { return view.r(d.v) / t.k; })
      .attr('stroke-width', function (d) {
        var base = current.city && current.city.id === d.c.id ? 2.4 : (seriesIndex[d.c.id] ? 1.2 : 0.6);
        return base / t.k;
      });
  }

  function zoomToBounds(b, pad) {
    if (!view) return;
    var dx = b[1][0] - b[0][0], dy = b[1][1] - b[0][1];
    var x = (b[0][0] + b[1][0]) / 2, y = (b[0][1] + b[1][1]) / 2;
    var k = Math.min(40, (pad || 0.9) / Math.max(dx / view.W, dy / view.H));
    var t = d3.zoomIdentity.translate(view.W / 2 - k * x, view.H / 2 - k * y).scale(k);
    view.svg.transition().duration(700).ease(d3.easeCubicInOut)
      .call(view.zoom.transform, t);
  }

  function zoomToState(f) { zoomToFeature(f); }

  // keepCity is for the one caller that is framing the map around a city it has
  // already chosen, rather than choosing the region itself. Without it, searching
  // for Lucknow zoomed to Uttar Pradesh and then read the whole state's numbers,
  // because framing the state threw the city away on its way past.
  function zoomToFeature(f, keepCity) {
    current.zoomState = f.properties.name;
    // At district level the readings roll up to the state, so name the state in
    // the trail too — otherwise the crumb says Kasaragod while the rail says Kerala.
    current.zoomVia = current.level === 'districts' ? (f.properties.state || null) : null;
    // A district has no series of its own, so the place becomes its state.
    current.zoomStateId = current.level === 'districts' && f.properties.state_lgd != null
      ? String(f.properties.state_lgd)
      : String(f.id);
    if (!keepCity) {
      current.city = null;
      current.range = null;
    }
    // Redraw first, then animate. The other way round starts the zoom on an svg
    // that render() is about to throw away, and the transition rides off on a
    // node that is no longer in the document — so nothing moves.
    render();
    zoomToBounds(view.path.bounds(f));
    drawCrumb();
    if (!keepCity) refreshPlace();   // the city's own caller is already loading it
  }

  function zoomToIndia() {
    current.zoomState = null;
    current.zoomStateId = null;
    current.zoomVia = null;
    current.city = null;
    current.range = null;
    refreshPlace();
    if (view) view.svg.transition().duration(700).ease(d3.easeCubicInOut)
      .call(view.zoom.transform, d3.zoomIdentity);
    drawCrumb();
  }

  // Breadcrumb doubles as the way back out, so the map needs no reset button.
  function drawCrumb() {
    var c = document.getElementById('aqCrumb');
    if (!c) return;
    if (!current.zoomState) { c.innerHTML = ''; return; }
    var trail = '<button type="button">India</button>';
    if (current.zoomVia) {
      trail += '<span>›</span><i>' + esc(current.zoomVia) + '</i>';
    }
    trail += '<span>›</span><b>' + esc(current.zoomState) + '</b>';
    c.innerHTML = trail;
    c.querySelector('button').addEventListener('click', zoomToIndia);
  }

  function markSelection() {
    if (!current.city || !view) return;
    var node = ui.map.querySelector('circle[data-city="' + current.city.id + '"]');
    if (node) {
      node.setAttribute('stroke', '#0f172a');
      node.setAttribute('stroke-width', 2.4 / view.t.k);
    }
  }

  // Direct-labelled band strip, so the map needs no separate legend.
  function drawScale() {
    ui.scale.innerHTML = '';
    var W = ui.scale.clientWidth || 320;
    var svg = d3.select(ui.scale).append('svg').attr('width', W).attr('height', 20);
    var x = 2;
    cfg().breaks.concat([null]).forEach(function (b, i) {
      svg.append('rect').attr('x', x).attr('y', 2).attr('width', 26).attr('height', 8)
        .attr('fill', BAND_COLOUR[i]);
      if (b != null) {
        svg.append('text').attr('x', x + 26).attr('y', 19).attr('text-anchor', 'middle')
          .attr('font-size', 8.5).attr('fill', '#64748b').text(b);
      }
      x += 30;
    });
    svg.append('text').attr('x', x + 6).attr('y', 8).attr('font-size', 9).attr('fill', '#64748b')
      .attr('dominant-baseline', 'middle').text(cfg().unit);
  }

  function showTip(e, d) {
    var i = band(d.v, current.pollutant);
    ui.tip.innerHTML =
      '<b>' + esc(d.c.name) + '</b>' +
      '<i>' + esc(d.c.state) + '</i>' +
      '<u>' + d.v + ' <s>' + cfg().unit + '</s></u>' +
      '<em style="color:' + BAND_COLOUR[i] + '">' + BAND_NAME[i] + '</em>' +
      '<i>' + (d.v / cfg().naaqs).toFixed(1) + '× NAAQS</i>';
    placeTip(e);
  }

  // Flip to the other side near the window edge so the tooltip is never clipped.
  function placeTip(e) {
    var t = ui.tip;
    t.style.display = 'block';
    t.style.left = '0px';
    t.style.top = '0px';
    var w = t.offsetWidth, h = t.offsetHeight;
    var x = e.clientX, y = e.clientY;
    t.style.transform = (x + w + 20 > window.innerWidth)
      ? 'translate(calc(-100% - 12px), -50%)'
      : 'translate(12px, -50%)';
    y = Math.min(Math.max(y, h / 2 + 4), window.innerHeight - h / 2 - 4);
    t.style.left = x + 'px';
    t.style.top = y + 'px';
  }
  function hideTip() { ui.tip.style.display = 'none'; }


  // ---------------------------------------------------------------------------
  //  Current place
  // ---------------------------------------------------------------------------
  // One idea the whole right-hand side follows, resolved by falling back: the
  // city you picked, else the state you zoomed into, else the country. Without
  // this the strip, the rail and the chart sat empty unless a city dot had been
  // clicked, which is most of the time.
  function placeKey() {
    if (current.city) return current.city.id;
    if (current.zoomStateId) return 'state-' + current.zoomStateId;
    return 'india';
  }

  function placeName() {
    if (current.city) return current.city.name;
    var idx = placeIndex[placeKey()];
    if (idx && idx.name) return idx.name;
    return current.zoomState || 'All India';
  }

  function placeSub() {
    if (current.city) return current.city.state;
    if (current.zoomStateId) return '';
    return '';
  }

  function placeDoc() { return seriesCache[placeKey()]; }

  // A place's record is split by year, so Delhi's whole history is not fetched to
  // draw one chart. The index says which years exist; the years themselves load
  // as they are needed and are stitched into the shape the rest of the code reads.
  function wantedYears(key) {
    var idx = placeIndex[key];
    if (!idx || !idx.years.length) return [];
    // Whatever window is in force, including the default one — a trailing month
    // in early January reaches back into the year before, and the rail would
    // otherwise summarise the two days that had landed since the first.
    var w = activeWindow();
    if (w) {
      var a = w[0].slice(0, 4), b = w[1].slice(0, 4);
      var span = idx.years.filter(function (y) { return y >= a && y <= b; });
      if (span.length) return span;
    }
    if (current.day) {
      var y = current.day.slice(0, 4);
      if (idx.years.indexOf(y) !== -1) return [y];
    }
    return [idx.years[idx.years.length - 1]];   // the most recent year by default
  }

  // Only the years being looked at, not every year that happens to be cached —
  // otherwise scrubbing back to 2009 would leave the chart drawing a line from
  // 2009 to today across a seventeen-year hole.
  function stitch(key) {
    var idx = placeIndex[key] || {};
    var loaded = placeYears[key] || {};
    var want = wantedYears(key);
    var series = {};
    Object.keys(loaded).sort().filter(function (y) {
      return want.indexOf(y) !== -1;
    }).forEach(function (y) {
      Object.keys(loaded[y]).forEach(function (p) {
        var src = loaded[y][p];
        var dst = series[p] || (series[p] = { t: [], v: [], n: [] });
        dst.t = dst.t.concat(src.t);
        dst.v = dst.v.concat(src.v);
        dst.n = dst.n.concat(src.n);
      });
    });
    seriesCache[key] = { id: key, name: idx.name || key, series: series, cycle: idx.cycle || {} };
    return seriesCache[key];
  }

  function refreshPlace() {
    var key = placeKey();
    ui.place.textContent = placeName();
    ui.where.textContent = placeSub();

    var haveIndex = placeIndex[key]
      ? Promise.resolve(placeIndex[key])
      : getJSON(DATA + 'series/' + key + '/index.json').then(function (j) {
          placeIndex[key] = j;
          return j;
        });

    return haveIndex.then(function () {
      var years = wantedYears(key);
      placeYears[key] = placeYears[key] || {};
      var need = years.filter(function (y) { return !placeYears[key][y]; });
      return Promise.all(need.map(function (y) {
        return getJSON(DATA + 'series/' + key + '/' + y + '.json').then(function (j) {
          placeYears[key][y] = j;
        }).catch(function () { placeYears[key][y] = {}; });
      })).then(function () {
        stitch(key);
        if (placeKey() === key) paintPlace();
      });
    }).catch(function () {
      if (placeKey() === key) paintPlace();
    });
  }

  function paintPlace() {
    ui.place.textContent = placeName();
    ui.where.textContent = placeSub();
    updateRail();
    updateStrip();
    drawRailCycles();
    if (!ui.panel.hidden) drawChart(placeDoc());
  }

  // ---------------------------------------------------------------------------
  //  Selection and rail
  // ---------------------------------------------------------------------------
  var selectSeq = 0;
  function selectCity(c) {
    var seq = ++selectSeq;
    current.city = c;
    current.range = null;
    render();
    refreshPlace().then(function () {
      if (seq !== selectSeq) return;            // a newer selection superseded this one
      if (!placeDoc()) { showRailFromMap(c); drawChart(null); }
    });
  }

  // Figures read as an aligned row, the same shape the site already uses on the
  // home page, rather than a dot-joined sentence.

  // Where the reading sits against the standard. Bands are equal width rather
  // than to scale, otherwise the top band swamps the strip; the boundary numbers
  // carry the real spacing, and the national limit gets its own mark.
  function drawGauge(value) {
    var el = ui.gauge;
    el.innerHTML = '';
    var W = el.clientWidth, H = 30;
    if (!W) return;
    var cfg = cfg_();
    var svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    var n = BAND_COLOUR.length;
    var bw = W / n;

    for (var i = 0; i < n; i++) {
      svg.append('rect').attr('x', i * bw).attr('y', 9).attr('width', bw + 0.5).attr('height', 7)
        .attr('fill', BAND_COLOUR[i]);
    }
    cfg.breaks.forEach(function (b, i) {
      svg.append('text').attr('x', (i + 1) * bw).attr('y', H - 1).attr('text-anchor', 'middle')
        .attr('font-size', 7.5).attr('fill', '#94a3b8').text(b);
    });

    // the national 24-hour standard
    var nb = cfg.breaks.indexOf(cfg.naaqs);
    var nx = nb >= 0 ? (nb + 1) * bw : null;
    if (nx != null) {
      svg.append('line').attr('x1', nx).attr('x2', nx).attr('y1', 6).attr('y2', 19)
        .attr('stroke', '#0f172a').attr('stroke-width', 1.5);
    }

    // the current reading
    if (value != null && isFinite(value)) {
      var bi = band(value, current.pollutant);
      var lo = bi === 0 ? 0 : cfg.breaks[bi - 1];
      var hi = bi < cfg.breaks.length ? cfg.breaks[bi] : cfg.breaks[cfg.breaks.length - 1] * 1.5;
      var frac = hi > lo ? Math.min(1, Math.max(0, (value - lo) / (hi - lo))) : 0.5;
      var vx = Math.min(W - 1, bi * bw + frac * bw);
      svg.append('path')
        .attr('d', 'M' + vx + ',8 l-4,-6 l8,0 Z')
        .attr('fill', '#0f172a');
    }
  }

  function drawStats(rows) {
    ui.stats.innerHTML = rows.map(function (r) {
      return '<span class="aq-stat"><b>' + esc(r[0]) + '</b><i>' + esc(r[1]) + '</i></span>';
    }).join('');
  }

  function showRailFromMap(c) {
    var v = values[c.id];
    ui.value.textContent = v == null ? '—' : v;
    ui.unit.textContent = cfg().unit;
    ui.versus.textContent = v == null ? '' : (v / cfg().naaqs).toFixed(1) + '× NAAQS';
    ui.versus.style.color = v == null ? '' : BAND_COLOUR[band(v, current.pollutant)];
    drawGauge(v);
    drawStats([[c.n, c.n === 1 ? 'station' : 'stations']]);
    ui.cycleBlock.hidden = true;
    ui.exceedBlock.hidden = true;
  }

  // The period everything reads when nobody has brushed one: the last thirty
  // days of the record. It used to be the calendar year on screen, which is
  // fine in November and absurd in January — landing on a year two days old
  // gave a rail reading "2 DAYS", sparklines with two points each, and a chart
  // with nothing to draw a line between.
  var WINDOW_DAYS = 30;
  var MAX_LINE_GAP_DAYS = 3;     // further apart than this and the chart breaks the line

  function defaultWindow() {
    if (!dailySpan) return null;
    // Ending on the day the map is showing, not on the end of the record, so
    // the rail describes the period the map sits at the end of.
    var end = new Date((current.day || dailySpan[1]) + 'T00:00:00');
    if (isNaN(end)) return null;
    var start = new Date(end);
    start.setDate(start.getDate() - (WINDOW_DAYS - 1));
    var from = isoDay(start);
    return [from < dailySpan[0] ? dailySpan[0] : from, current.day || dailySpan[1]];
  }

  function activeWindow() {
    return current.range || defaultWindow();
  }

  function between(s, lo, hi) {
    if (!s) return null;
    var t = s.t, v = s.v, n = s.n, i, out = { t: [], v: [], n: [] };
    for (i = 0; i < t.length; i++) {
      if (t[i] < lo || t[i] > hi) continue;
      out.t.push(t[i]); out.v.push(v[i]); out.n.push(n[i]);
    }
    return out.t.length ? out : null;
  }

  function windowed(s) {
    var w = activeWindow();
    return between(s, w ? w[0] : (current.year || '') + '-01-01',
                      w ? w[1] : (current.year || '9999') + '-12-31');
  }

  // The month-by-month block keeps its own twelve months whatever is brushed.
  // It is the one thing on the page asking a seasonal question, and under a
  // thirty-day window every answer fits in a single bar.
  //
  // Twelve months that hold readings, not the last twelve on the calendar: the
  // record has a year-long hole in it where the archive we backfilled from went
  // quiet. Only months already fetched are visible here, so this is the last
  // twelve of what is loaded rather than of the whole record.
  function trailingYear(s) {
    if (!s || !s.t.length) return null;
    var months = [], seen = {};
    for (var i = s.t.length - 1; i >= 0 && months.length < 12; i--) {
      var k = s.t[i].slice(0, 7);
      if (!seen[k]) { seen[k] = true; months.push(k); }
    }
    if (!months.length) return null;
    return between(s, months[months.length - 1] + '-01', months[0] + '-31');
  }

  // The pollutant strip doubles as a six-way comparison: once a city is chosen,
  // each tab carries that city's own sparkline and period mean.
  function updateStrip() {
    var doc = placeDoc();
    [].forEach.call(ui.pollutants.querySelectorAll('.aq-pol'), function (tab) {
      var p = tab.dataset.pol;
      var spark = tab.querySelector('.aq-pol-spark');
      var val = tab.querySelector('.aq-pol-val');
      spark.innerHTML = '';
      val.textContent = '';
      var s = doc && doc.series[p];
      var w = s && windowed(s);
      if (!w) { tab.classList.remove('has-data'); return; }
      tab.classList.add('has-data');

      var mean = d3.mean(w.v);
      val.textContent = mean.toFixed(mean < 10 ? 1 : 0);
      val.style.color = BAND_COLOUR[band(mean, p)];

      var W = spark.clientWidth || 90, H = 18;
      var x = d3.scaleLinear().domain([0, w.v.length - 1]).range([0, W]);
      var y = d3.scaleLinear().domain([0, d3.max(w.v)]).range([H - 1, 1]);
      d3.select(spark).append('svg').attr('width', W).attr('height', H)
        .append('path').datum(w.v)
        .attr('fill', 'none')
        .attr('stroke', BAND_COLOUR[band(mean, p)])
        .attr('stroke-width', 1)
        .attr('d', d3.line().x(function (d, i) { return x(i); }).y(function (d) { return y(d); }));
    });
  }


  // ---------------------------------------------------------------------------
  //  Cycles: the hour-by-month climatology and monthly exceedance
  // ---------------------------------------------------------------------------
  var MONTH_INITIAL = 'JFMAMJJASOND'.split('');
  var MONTH_NAME = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                    'August', 'September', 'October', 'November', 'December'];

  // Every cell is one hour of one month, averaged over the record. The daily and
  // seasonal cycles are both visible in a single image.
  function drawCycle(el, grid, p, big) {
    el.innerHTML = '';
    var W = el.clientWidth, H = el.clientHeight;
    if (!W || !H || !grid) return false;
    var padL = big ? 24 : 13, padB = big ? 15 : 9;
    var cw = (W - padL) / 24, chh = (H - padB) / 12;
    var svg = d3.select(el).append('svg').attr('width', W).attr('height', H);

    for (var m = 0; m < 12; m++) {
      for (var h = 0; h < 24; h++) {
        var v = grid[m] ? grid[m][h] : null;
        svg.append('rect')
          .attr('x', padL + h * cw).attr('y', m * chh)
          .attr('width', Math.ceil(cw) + 0.5).attr('height', Math.ceil(chh) + 0.5)
          .attr('fill', v == null ? '#eef2f7' : BAND_COLOUR[band(v, p)])
          .attr('data-m', m).attr('data-h', h)
          .style('cursor', v == null ? 'default' : 'crosshair')
          .on('pointerenter pointermove', function (e) {
            var mm = +this.getAttribute('data-m'), hh = +this.getAttribute('data-h');
            var val = grid[mm] ? grid[mm][hh] : null;
            if (val == null) return;
            var bi = band(val, p);
            ui.tip.innerHTML = '<b>' + MONTH_NAME[mm] + ', ' +
              String(hh).padStart(2, '0') + ':00</b>' +
              '<u>' + val + ' <s>' + POLLUTANTS[p].unit + '</s></u>' +
              '<em style="color:' + BAND_COLOUR[bi] + '">' + BAND_NAME[bi] + '</em>';
            placeTip(e);
          })
          .on('pointerleave', hideTip);
      }
    }
    MONTH_INITIAL.forEach(function (ch, m) {
      svg.append('text').attr('x', padL - 3).attr('y', m * chh + chh / 2 + 2.5)
        .attr('text-anchor', 'end').attr('font-size', big ? 9 : 7)
        .attr('fill', '#94a3b8').text(ch);
    });
    [0, 6, 12, 18].forEach(function (h) {
      svg.append('text').attr('x', padL + h * cw).attr('y', H - 1)
        .attr('font-size', big ? 9 : 7).attr('fill', '#94a3b8').text(h);
    });
    return true;
  }

  // One bar per month: how many days that month broke the national standard.
  function drawExceed(el, w, p) {
    el.innerHTML = '';
    var W = el.clientWidth, H = el.clientHeight;
    if (!W || !H || !w) return false;
    var naaqs = POLLUTANTS[p].naaqs;
    var byMonth = {};
    w.t.forEach(function (t, i) {
      var k = t.slice(0, 7);
      if (!byMonth[k]) byMonth[k] = { over: 0, days: 0, sum: 0 };
      byMonth[k].days++;
      byMonth[k].sum += w.v[i];
      if (w.v[i] > naaqs) byMonth[k].over++;
    });
    var keys = Object.keys(byMonth).sort();
    // One bar stretched across the block is not a season. Say nothing until
    // there is a shape to see — which, where the record has a hole, means the
    // block stays away rather than implying a year made of one month.
    if (keys.length < 3) return false;

    var svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    var padB = 9;
    var bw = W / keys.length;
    var maxOver = d3.max(keys, function (k) { return byMonth[k].over; }) || 1;
    var y = d3.scaleLinear().domain([0, maxOver]).range([H - padB, 1]);

    keys.forEach(function (k, i) {
      var o = byMonth[k];
      var mean = o.sum / o.days;
      svg.append('rect')
        .attr('x', i * bw + 0.5).attr('y', y(o.over))
        .attr('width', Math.max(1, bw - 1.5)).attr('height', H - padB - y(o.over))
        .attr('fill', BAND_COLOUR[band(mean, p)])
        .style('cursor', 'crosshair')
        .on('pointerenter pointermove', function (e) {
          ui.tip.innerHTML = '<b>' + MONTH_NAME[+k.slice(5, 7) - 1] + ' ' + k.slice(0, 4) + '</b>' +
            '<u>' + o.over + ' <s>of ' + o.days + ' days</s></u>' +
            '<i>above ' + naaqs + ' ' + POLLUTANTS[p].unit + '</i>';
          placeTip(e);
        })
        .on('pointerleave', hideTip);
      if (bw > 13) {
        svg.append('text').attr('x', i * bw + bw / 2).attr('y', H - 1)
          .attr('text-anchor', 'middle').attr('font-size', 7).attr('fill', '#94a3b8')
          .text(MONTH_INITIAL[+k.slice(5, 7) - 1]);
      }
    });
    return true;
  }

  function drawRailCycles() {
    var doc = placeDoc();
    var grid = doc && doc.cycle && doc.cycle[current.pollutant];
    var w = doc && trailingYear(doc.series[current.pollutant]);
    // Reveal before drawing: a hidden block has no layout, so measuring it first
    // would report zero width and it would never un-hide.
    ui.cycleBlock.hidden = !grid;
    ui.exceedBlock.hidden = !w;
    if (grid && !drawCycle(ui.cycle, grid, current.pollutant, false)) ui.cycleBlock.hidden = true;
    if (w && !drawExceed(ui.exceed, w, current.pollutant)) ui.exceedBlock.hidden = true;
  }

  function updateRail() {
    var doc = placeDoc();
    var s = doc && doc.series[current.pollutant];
    var w = windowed(s);
    if (!w) {
      if (current.city) showRailFromMap(current.city);
      return;
    }
    var mean = d3.mean(w.v);
    var over = w.v.filter(function (x) { return x > cfg().naaqs; }).length;
    ui.value.textContent = mean.toFixed(mean < 10 ? 1 : 0);
    ui.unit.textContent = cfg().unit;
    ui.versus.textContent = (mean / cfg().naaqs).toFixed(1) + '× NAAQS';
    ui.versus.style.color = BAND_COLOUR[band(mean, current.pollutant)];
    drawGauge(mean);
    drawStats([[w.t.length, 'days'], [over, 'over NAAQS'],
               [Math.round(d3.median(w.n)), 'stations']]);
    railSpan = w.t.length > 1 ? w.t[0] + ' → ' + w.t[w.t.length - 1] : w.t[0];
    updateWhen();
    updateStrip();
    drawRailCycles();
  }

  // ---------------------------------------------------------------------------
  //  Period line chart
  // ---------------------------------------------------------------------------
  function drawChart(doc) {
    ui.chart.innerHTML = '';
    var W = ui.chart.clientWidth, H = ui.chart.clientHeight;
    if (!W || !H) return;

    if (doc && current.panelView === 'heat') {
      var grid = doc.cycle && doc.cycle[current.pollutant];
      if (grid && drawCycle(ui.chart, grid, current.pollutant, true)) return;
    }

    if (!doc) {
      d3.select(ui.chart).append('svg').attr('width', W).attr('height', H)
        .append('text').attr('x', 10).attr('y', H / 2).attr('font-size', 11).attr('fill', '#94a3b8')
        .text(current.city ? 'No series built for this city yet.' : 'Select a city on the map.');
      return;
    }

    var s = doc.series[current.pollutant];
    if (!s) return;
    var data = s.t.map(function (d, i) {
      return { d: new Date(d + 'T00:00:00'), v: s.v[i], n: s.n[i], key: d };
    });

    var m = { t: 8, r: 10, b: 18, l: 34 };
    var svg = d3.select(ui.chart).append('svg').attr('width', W).attr('height', H);
    var iw = W - m.l - m.r, ih = H - m.t - m.b;
    var g = svg.append('g').attr('transform', 'translate(' + m.l + ',' + m.t + ')');

    var x = d3.scaleTime().domain(d3.extent(data, function (d) { return d.d; })).range([0, iw]);
    var yMax = d3.max(data, function (d) { return d.v; }) * 1.05;
    var y = d3.scaleLinear().domain([0, yMax]).range([ih, 0]);

    // The CPCB bands ride on the y-axis as a slim colour rail rather than washing
    // the plot: same colour language as the map, none of the muddiness.
    var lo = 0;
    cfg().breaks.concat([yMax]).forEach(function (hi, i) {
      if (lo >= yMax) return;
      var top = Math.min(hi, yMax);
      g.append('rect').attr('x', -5).attr('y', y(top)).attr('width', 4)
        .attr('height', Math.max(0, y(lo) - y(top)))
        .attr('fill', BAND_COLOUR[i]);
      lo = hi;
    });

    // NAAQS line, labelled at the left where the data is thinnest
    if (cfg().naaqs <= yMax) {
      g.append('line').attr('x1', 0).attr('x2', iw).attr('y1', y(cfg().naaqs)).attr('y2', y(cfg().naaqs))
        .attr('stroke', '#0f172a').attr('stroke-width', 1).attr('stroke-dasharray', '3 3').attr('opacity', 0.45);
      g.append('text').attr('x', 3).attr('y', y(cfg().naaqs) - 4)
        .attr('font-size', 9).attr('fill', '#0f172a').attr('opacity', 0.6).text('NAAQS ' + cfg().naaqs);
    }

    g.append('path').datum(data)
      .attr('fill', 'none').attr('stroke', '#0f172a').attr('stroke-width', 1.1)
      .attr('d', d3.line()
        // Lift the pen across a gap. The record has holes in it — whole months
        // where a source went quiet — and a line drawn straight over one reads
        // as a measurement rather than as the absence of any.
        .defined(function (d, i) {
          return d.v != null &&
            (i === 0 || (d.d - data[i - 1].d) / 864e5 <= MAX_LINE_GAP_DAYS);
        })
        .x(function (d) { return x(d.d); }).y(function (d) { return y(d.v); }));

    g.append('g').attr('transform', 'translate(0,' + ih + ')')
      .call(d3.axisBottom(x).ticks(Math.max(3, Math.floor(iw / 90))).tickSize(0).tickPadding(5))
      .call(function (sel) { sel.select('.domain').attr('stroke', '#e2e8f0'); })
      .selectAll('text').attr('font-size', 9).attr('fill', '#64748b');
    g.append('g').call(d3.axisLeft(y).ticks(3).tickSize(0).tickPadding(4))
      .call(function (sel) { sel.select('.domain').remove(); })
      .selectAll('text').attr('font-size', 9).attr('fill', '#64748b');

    // hover readout, so the resting chart carries no extra labels
    var focus = g.append('g').style('display', 'none');
    focus.append('line').attr('y1', 0).attr('y2', ih).attr('stroke', '#0f172a').attr('stroke-width', 0.6);
    focus.append('circle').attr('r', 3).attr('fill', '#0f172a');
    var bisect = d3.bisector(function (d) { return d.d; }).left;
    g.append('rect').attr('width', iw).attr('height', ih).attr('fill', 'none').attr('pointer-events', 'all')
      .on('pointerleave', function () { focus.style('display', 'none'); hideTip(); })
      .on('pointerenter pointermove', function (e) {
        var mx = d3.pointer(e, this)[0];
        var d0 = x.invert(mx);
        var i = Math.min(data.length - 1, Math.max(0, bisect(data, d0)));
        var d = data[i];
        focus.style('display', null).attr('transform', 'translate(' + x(d.d) + ',0)');
        focus.select('circle').attr('cy', y(d.v));
        var bi = band(d.v, current.pollutant);
        ui.tip.innerHTML =
          '<b>' + esc(d.key) + '</b>' +
          '<u>' + d.v + ' <s>' + cfg().unit + '</s></u>' +
          '<em style="color:' + BAND_COLOUR[bi] + '">' + BAND_NAME[bi] + '</em>' +
          '<i>' + (d.v / cfg().naaqs).toFixed(1) + '× NAAQS</i>';
        placeTip(e);
      });

    // drag across the chart to set the period; everything else follows it
    var restoring = false;
    var brush = d3.brushX().extent([[0, 0], [iw, ih]]).on('end', function (e) {
      if (restoring) return;                    // programmatic restore, not a user drag
      if (!e.selection) { current.range = null; updateRail(); return; }
      current.range = [isoDay(x.invert(e.selection[0])), isoDay(x.invert(e.selection[1]))];
      refreshPlace();      // the range may reach into a year not yet fetched
      updateRail();
    });
    var bg = g.append('g').attr('class', 'aq-brush').call(brush);
    // Redraws (pollutant switch, resize) rebuild the chart; put the handle back so
    // the visible selection always matches the period the figures are using.
    if (current.range) {
      var a = new Date(current.range[0] + 'T00:00:00');
      var b = new Date(current.range[1] + 'T00:00:00');
      var dom = x.domain();
      if (b >= dom[0] && a <= dom[1]) {
        restoring = true;
        bg.call(brush.move, [x(a < dom[0] ? dom[0] : a), x(b > dom[1] ? dom[1] : b)]);
        restoring = false;
      }
    }
  }




  // ---------------------------------------------------------------------------
  //  City search: the only way to reach a city without a mouse
  // ---------------------------------------------------------------------------
  var findMatches = [];
  var findActive = -1;

  function findClose() {
    ui.findList.hidden = true;
    ui.findList.innerHTML = '';
    ui.find.setAttribute('aria-expanded', 'false');
    ui.find.removeAttribute('aria-activedescendant');
    findMatches = [];
    findActive = -1;
  }

  function findRender(q) {
    var needle = q.trim().toLowerCase();
    if (!needle) { findClose(); return; }
    findMatches = cities.filter(function (c) {
      return (c.name + ' ' + c.state).toLowerCase().indexOf(needle) !== -1;
    }).sort(function (a, b) {
      // a name that starts with the query beats one that merely contains it
      var as = a.name.toLowerCase().indexOf(needle) === 0 ? 0 : 1;
      var bs = b.name.toLowerCase().indexOf(needle) === 0 ? 0 : 1;
      return as - bs || b.n - a.n || a.name.localeCompare(b.name);
    }).slice(0, 8);

    if (!findMatches.length) { findClose(); return; }
    ui.findList.innerHTML = findMatches.map(function (c, i) {
      return '<li role="option" id="aqFindOpt' + i + '" aria-selected="false" data-i="' + i + '">' +
        '<span>' + esc(c.name) + '</span><small>' + esc(c.state) + '</small></li>';
    }).join('');
    ui.findList.hidden = false;
    ui.find.setAttribute('aria-expanded', 'true');
    findActive = 0;
    findHighlight();
  }

  function findHighlight() {
    [].forEach.call(ui.findList.children, function (li, i) {
      li.setAttribute('aria-selected', i === findActive ? 'true' : 'false');
    });
    var el = ui.findList.children[findActive];
    if (el) {
      ui.find.setAttribute('aria-activedescendant', el.id);
      if (el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
    }
  }

  function findChoose(i) {
    var c = findMatches[i];
    if (!c) return;
    findClose();
    ui.find.value = '';
    ui.find.blur();
    selectCity(c);
    // put the city on screen, otherwise the selection ring is lost among 239 dots
    var unit = coverage && coverage.cityUnit && coverage.cityUnit[c.id];
    if (unit && unit.state && view) {
      var f = statesFeat.filter(function (x) {
        return String(x.id) === String(unit.state);
      })[0];
      if (f) zoomToFeature(f, true);   // frame the state, keep the city
    }
  }

  // ---------------------------------------------------------------------------
  //  Download: exactly what is on screen
  // ---------------------------------------------------------------------------
  // A leading =, + or @ makes a spreadsheet treat the cell as a formula.
  function csvSafe(v) {
    if (v == null) return '';
    var t = String(v);
    if (/^[=+@\-]/.test(t) && isNaN(Number(t))) t = "'" + t;
    return /[",\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
  }

  function toCsv(rows) {
    return rows.map(function (r) { return r.map(csvSafe).join(','); }).join('\n');
  }

  function saveCsv(rows, name) {
    var blob = new Blob(['﻿' + toCsv(rows)], { type: 'text/csv;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 30000);
  }

  function slugify(v) {
    return String(v).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  }

  // ---------------------------------------------------------------------------
  //  Download dialog
  // ---------------------------------------------------------------------------
  // Two questions only: which area, and what a row stands for inside it. The
  // second depends on the first — inside one city the only thing below is a
  // monitor, so there is nothing to ask and the control disappears.
  // The level you picked at is itself a valid row, once more than one thing can
  // be picked: three states as three daily rows is a real thing to want.
  var LEVELS_AT_OR_BELOW = {
    india:   [['state', 'State'], ['city', 'City'], ['station', 'Station']],
    state:   [['state', 'State'], ['city', 'City'], ['station', 'Station']],
    city:    [['city', 'City'], ['station', 'Station']],
    station: []
  };

  var dl = { scope: 'india', picks: [], rows: 'state' };

  function dlSetScope(next) {
    dl.scope = next;
    dl.picks = [];
    ui.dlSearch.value = '';
    Array.prototype.forEach.call(ui.dlScope.children, function (b) {
      var on = b.dataset.scope === next;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    ui.dlPick.hidden = next === 'india';
    var levels = LEVELS_AT_OR_BELOW[next];
    dl.rows = levels.length ? levels[0][0] : 'station';
    dlRenderRows();
    dlRenderList();
    dlValidate();
  }

  function dlRenderRows() {
    var levels = LEVELS_AT_OR_BELOW[dl.scope];
    // one option is not a choice; do not make the reader look at it
    ui.dlRowsWrap.hidden = levels.length < 2;
    ui.dlRows.innerHTML = levels.map(function (l) {
      return '<button type="button" role="radio" data-rows="' + l[0] + '" aria-checked="' +
        (l[0] === dl.rows) + '" class="' + (l[0] === dl.rows ? 'is-on' : '') + '">' + l[1] + '</button>';
    }).join('');
  }

  function dlAllChoices() {
    var save = ui.dlSearch.value;
    ui.dlSearch.value = '';
    var all = dlChoices(true);
    ui.dlSearch.value = save;
    return all;
  }

  function dlChoices(all) {
    var q = all ? '' : ui.dlSearch.value.trim().toLowerCase();
    var list = [];
    if (dl.scope === 'state') {
      var seen = {};
      cities.forEach(function (c) { seen[c.state] = true; });
      list = Object.keys(seen).sort().map(function (st) { return { v: st, label: st }; });
    } else if (dl.scope === 'city') {
      list = cities.slice().sort(function (a, b) { return a.name.localeCompare(b.name); })
        .map(function (c) { return { v: c.id, label: c.name + ', ' + c.state }; });
    } else if (dl.scope === 'station') {
      list = stations.slice().sort(function (a, b) { return a.name.localeCompare(b.name); })
        .map(function (st) { return { v: st.id, label: st.name }; });
    }
    if (q) {
      list = list.filter(function (o) { return o.label.toLowerCase().indexOf(q) !== -1; });
    }
    return all ? list : list.slice(0, 300);
  }

  function dlRenderList() {
    if (dl.scope === 'india') { ui.dlOptions.innerHTML = ''; return; }
    var opts = dlChoices();
    var chosen = {};
    dl.picks.forEach(function (v) { chosen[v] = true; });

    // With an empty box, whatever is picked rides at the top so a long list never
    // hides it. While searching it does not, because the results are what you are
    // looking at and a pinned earlier pick would sit in front of them.
    var searching = ui.dlSearch.value.trim() !== '';
    var picked = searching ? [] : dlAllChoices().filter(function (o) { return chosen[o.v]; });
    var rest = searching ? opts : opts.filter(function (o) { return !chosen[o.v]; });

    if (!picked.length && !rest.length) {
      ui.dlOptions.innerHTML = '<p class="aq-dl-none">Nothing matches that.</p>';
      return;
    }
    function row(o, sep) {
      return '<button type="button" role="option" data-v="' + esc(o.v) + '" aria-selected="' +
        (!!chosen[o.v]) + '" class="' + (chosen[o.v] ? 'is-on' : '') + (sep ? ' aq-dl-sep' : '') +
        '" title="' + esc(o.label) + '"><span class="aq-dl-tick"></span><span>' +
        esc(o.label) + '</span></button>';
    }
    ui.dlOptions.innerHTML =
      picked.map(function (o) { return row(o, false); }).join('') +
      rest.map(function (o, i) { return row(o, i === 0 && picked.length > 0); }).join('');
  }

  function dlStations() {
    if (dl.scope === 'india') return stations.map(function (s) { return s.id; });
    if (!dl.picks.length) return [];
    var want = {};
    dl.picks.forEach(function (p) { want[p] = true; });
    if (dl.scope === 'station') return dl.picks.slice();
    if (dl.scope === 'city') {
      return stations.filter(function (s) {
        var u = coverage && coverage.stationUnit && coverage.stationUnit[s.id];
        return u && want[u.city];
      }).map(function (s) { return s.id; });
    }
    return stations.filter(function (s) { return want[s.state]; })
      .map(function (s) { return s.id; });
  }

  function dlValidate() {
    var from = ui.dlFrom.value, to = ui.dlTo.value;
    var ok = from && to && from <= to && dlStations().length > 0;
    ui.dlGo.disabled = !ok;
  }

  // One or two places are named outright; beyond that a name would be unreadable,
  // so it says how many.
  function dlLabelParts() {
    var parts = ['air-quality', 'india'];
    var n = dl.picks.length;
    if (dl.scope === 'india' || !n) return parts;
    var plural = { state: 'states', city: 'cities', station: 'stations' }[dl.scope];
    if (n > 2) return parts.concat([String(n), plural]);

    dl.picks.forEach(function (p) {
      if (dl.scope === 'state') {
        parts.push(slugify(p));
      } else if (dl.scope === 'city') {
        var c = cities.filter(function (x) { return x.id === p; })[0];
        if (c) parts.push(n === 1 ? slugify(c.state) : '', slugify(c.name));
      } else {
        var st = stations.filter(function (x) { return x.id === p; })[0];
        if (st) parts.push(n === 1 ? slugify(st.state) : '', n === 1 ? slugify(st.city) : '',
                           stationTail(st.name));
      }
    });
    return parts.filter(Boolean);
  }

  function stationTail(name) {
    var bits = String(name || '').split(' - ');
    var agency = bits.length > 1 ? bits.pop() : '';
    var place = bits.join(' - ').split(',')[0];
    return slugify(place + (agency ? '-' + agency : ''));
  }

  function dlBuild() {
    var from = ui.dlFrom.value, to = ui.dlTo.value;
    var years = {};
    for (var y = +from.slice(0, 4); y <= +to.slice(0, 4); y++) years[y] = true;
    var pols = Object.keys(POLLUTANTS);
    var jobs = [];
    pols.forEach(function (p) {
      Object.keys(years).forEach(function (y) {
        if (dailyIndex && (dailyIndex[p] || []).indexOf(String(y)) !== -1) {
          jobs.push(loadDaily(p, String(y)).catch(function () { return null; }));
        }
      });
    });

    ui.dlGo.disabled = true;
    return Promise.all(jobs).then(function () {
      var want = {};
      dlStations().forEach(function (sid) { want[sid] = true; });
      var meta = {};
      stations.forEach(function (st) { if (want[st.id]) meta[st.id] = st; });

      var table = {};
      pols.forEach(function (p) {
        Object.keys(years).forEach(function (y) {
          var m = dailyCache[p + '-' + y];
          if (!m) return;
          for (var i = 0; i < m.t.length; i++) {
            var day = m.t[i];
            if (day < from || day > to) continue;
            var row = m.v[i];
            for (var j = 0; j < m.stations.length; j++) {
              var sid = m.stations[j];
              if (!want[sid] || row[j] == null) continue;
              if (!table[day]) table[day] = {};
              if (!table[day][sid]) table[day][sid] = {};
              table[day][sid][p] = row[j];
            }
          }
        });
      });

      var head, out = [];
      if (dl.rows === 'station') {
        head = ['date', 'station_id', 'station', 'city', 'state', 'latitude', 'longitude'].concat(pols);
        Object.keys(table).sort().forEach(function (day) {
          Object.keys(table[day]).sort().forEach(function (sid) {
            var st = meta[sid] || {};
            out.push([day, sid, st.name || '', st.city || '', st.state || '', st.lat, st.lon]
              .concat(pols.map(function (p) {
                return table[day][sid][p] == null ? '' : table[day][sid][p];
              })));
          });
        });
      } else {
        // city or state: average within a city first, then across cities, so a
        // monitor-dense city does not speak for a whole state
        var byState = dl.rows === 'state';
        head = byState ? ['date', 'state', 'cities', 'monitors'].concat(pols)
                       : ['date', 'city', 'state', 'monitors'].concat(pols);
        Object.keys(table).sort().forEach(function (day) {
          var cityAcc = {};
          Object.keys(table[day]).forEach(function (sid) {
            var st = meta[sid];
            if (!st) return;
            var key = st.city + '|' + st.state;
            if (!cityAcc[key]) cityAcc[key] = { n: 0, sums: {}, counts: {} };
            var a = cityAcc[key];
            a.n++;
            pols.forEach(function (p) {
              var v = table[day][sid][p];
              if (v == null) return;
              a.sums[p] = (a.sums[p] || 0) + v;
              a.counts[p] = (a.counts[p] || 0) + 1;
            });
          });
          var cityMeans = {};
          Object.keys(cityAcc).forEach(function (key) {
            var a = cityAcc[key], m2 = { n: a.n, vals: {} };
            pols.forEach(function (p) {
              if (a.counts[p]) m2.vals[p] = a.sums[p] / a.counts[p];
            });
            cityMeans[key] = m2;
          });

          if (!byState) {
            Object.keys(cityMeans).sort().forEach(function (key) {
              var m2 = cityMeans[key], parts = key.split('|');
              out.push([day, parts[0], parts[1], m2.n].concat(pols.map(function (p) {
                return m2.vals[p] == null ? '' : Math.round(m2.vals[p] * 10) / 10;
              })));
            });
          } else {
            var stAcc = {};
            Object.keys(cityMeans).forEach(function (key) {
              var m2 = cityMeans[key], stName = key.split('|')[1];
              if (!stAcc[stName]) stAcc[stName] = { cities: 0, n: 0, sums: {}, counts: {} };
              var a = stAcc[stName];
              a.cities++;
              a.n += m2.n;
              pols.forEach(function (p) {
                if (m2.vals[p] == null) return;
                a.sums[p] = (a.sums[p] || 0) + m2.vals[p];
                a.counts[p] = (a.counts[p] || 0) + 1;
              });
            });
            Object.keys(stAcc).sort().forEach(function (stName) {
              var a = stAcc[stName];
              out.push([day, stName, a.cities, a.n].concat(pols.map(function (p) {
                return a.counts[p] ? Math.round(a.sums[p] / a.counts[p] * 10) / 10 : '';
              })));
            });
          }
        });
      }

      if (!out.length) {
        dlValidate();
        return;
      }
      var name = dlLabelParts().concat([from, 'to', to, 'by-' + dl.rows]).join('-') + '.csv';
      saveCsv([head].concat(out), name);
      ui.dl.close();
      dlValidate();
    });
  }

  function openDownload() {
    var yrs = [];
    Object.keys(dailyIndex || {}).forEach(function (p) {
      (dailyIndex[p] || []).forEach(function (y) { if (yrs.indexOf(y) === -1) yrs.push(y); });
    });
    yrs.sort();
    // the span the data actually covers, not the calendar years it touches
    var min = dailySpan ? dailySpan[0] : (yrs.length ? yrs[0] + '-01-01' : '');
    var max = dailySpan ? dailySpan[1] : (yrs.length ? yrs[yrs.length - 1] + '-12-31' : '');
    ui.dlFrom.min = min; ui.dlFrom.max = max;
    ui.dlTo.min = min; ui.dlTo.max = max;
    // With the whole record available, defaulting to all of it would hand someone
    // a multi-hundred-megabyte pull for pressing the obvious button. Start at the
    // period on screen, else the last month.
    var w = activeWindow();
    ui.dlFrom.value = (w && w[0]) || min;
    ui.dlTo.value = (w && w[1]) || max;

    if (current.city) {
      dlSetScope('city');
      dl.picks = [current.city.id];
      dlRenderList();
      dlValidate();
    } else {
      dlSetScope('india');
    }
    if (ui.dl.showModal) ui.dl.showModal(); else ui.dl.setAttribute('open', '');
  }

  // ---------------------------------------------------------------------------
  //  Time strip: the national series, the playhead and the range in one control
  // ---------------------------------------------------------------------------
  function nationalMeans(m) {
    if (m.means) return m.means;
    m.means = m.v.map(function (row) {
      var sum = 0, n = 0;
      for (var i = 0; i < row.length; i++) if (row[i] != null) { sum += row[i]; n++; }
      return n ? sum / n : null;
    });
    return m.means;
  }

  function stripSeries() {
    var s = national && national[current.pollutant];
    if (s && s.t.length) return s;
    var m = current.year && dailyCache[current.pollutant + '-' + current.year];
    if (!m) return null;
    return { t: m.t, v: nationalMeans(m) };
  }

  function drawStrip() {
    var el = ui.strip;
    el.innerHTML = '';
    var W = el.clientWidth, H = el.clientHeight;
    if (!W || !H) return;
    var s = stripSeries();
    if (!s) return;

    var svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    var x = d3.scaleLinear().domain([0, s.t.length - 1]).range([0, W]);
    var y = d3.scaleLinear().domain([0, d3.max(s.v) || 1]).range([H - 1, 1]);

    svg.append('path').datum(s.v.map(function (v, i) { return { i: i, v: v }; })
        .filter(function (d) { return d.v != null; }))
      .attr('fill', 'none').attr('stroke', '#94a3b8').attr('stroke-width', 1)
      .attr('d', d3.line().x(function (d) { return x(d.i); }).y(function (d) { return y(d.v); }));

    // Year ticks across a long record, month ticks within a single year, so a
    // position on the strip always reads as a time.
    var multiYear = s.t[0].slice(0, 4) !== s.t[s.t.length - 1].slice(0, 4);
    s.t.forEach(function (d, i) {
      var mark = multiYear ? (d.slice(5) === '01-01') : (d.slice(8) === '01');
      if (!mark) return;
      svg.append('line').attr('x1', x(i)).attr('x2', x(i)).attr('y1', H - 4).attr('y2', H)
        .attr('stroke', '#cbd5e1');
      if (multiYear && d.slice(0, 4) % 4 === 0) {
        svg.append('text').attr('x', x(i) + 2).attr('y', H - 6).attr('font-size', 7.5)
          .attr('fill', '#94a3b8').text(d.slice(0, 4));
      }
    });

    var at = current.day ? s.t.indexOf(current.day) : -1;
    if (at !== -1) {
      svg.append('line').attr('x1', x(at)).attr('x2', x(at)).attr('y1', 0).attr('y2', H)
        .attr('stroke', '#f59e0b').attr('stroke-width', 1.5);
    }

    svg.append('rect').attr('width', W).attr('height', H).attr('fill', 'transparent')
      .style('cursor', 'ew-resize')
      .on('pointerdown pointermove', function (e) {
        if (e.type === 'pointermove' && !e.buttons) return;
        var px = d3.pointer(e, this)[0];
        var i = Math.max(0, Math.min(s.t.length - 1, Math.round(x.invert(px))));
        setDay(s.t[i]);
      });
  }

  function setDay(day) {
    var wasYear = current.day && current.day.slice(0, 4);
    var year = day.slice(0, 4);
    current.day = day;
    // A brushed range belongs to the period you brushed it in. Carrying it along
    // as you scrub leaves the rail describing one year and the map another.
    current.range = null;
    updateWhen();
    if (year !== wasYear) {
      current.year = year;
      // the map reads a matrix per pollutant-year, so fetch it before drawing
      loadDaily(current.pollutant, year).then(function () {
        render();
        drawStrip();
      }).catch(function () { render(); drawStrip(); });
    } else {
      render();
      drawStrip();
    }
    // Always, not only when the year changes. The period summarised beside the
    // map is now the thirty days ending on this day, so moving a day within a
    // year moves it too — and the rail sat frozen on the old one.
    refreshPlace();
  }

  function clearDay() {
    current.day = null;
    current.range = null;
    updateWhen();
    render();
    drawStrip();
    refreshPlace();      // the window moves with the day, so the rail must follow
  }

  function stepDay(delta) {
    var s = stripSeries();
    if (!s) return;
    if (!current.day) { setDay(s.t[s.t.length - 1]); return; }
    var i = s.t.indexOf(current.day);
    if (i === -1) return;
    i += delta;
    if (i < 0 || i >= s.t.length) return;
    setDay(s.t[i]);
  }

  var railSpan = '';
  function updateWhen() {
    if (!current.day) {
      ui.when.textContent = railSpan;
      return;
    }
    ui.when.innerHTML = esc(current.day) +
      ' <button type="button" class="aq-clear" aria-label="Back to latest">&times;</button>';
    var b = ui.when.querySelector('.aq-clear');
    if (b) b.addEventListener('click', clearDay);
  }

  // The strip only makes sense once a pollutant-year matrix is loaded.
  function ensureDaily() {
    if (!dailyIndex) return Promise.resolve(null);
    var yrs = dailyIndex[current.pollutant] || [];
    if (!yrs.length) return Promise.resolve(null);
    if (!current.year || yrs.indexOf(current.year) === -1) current.year = yrs[yrs.length - 1];
    return loadDaily(current.pollutant, current.year).then(function (m) {
      drawStrip();
      return m;
    }).catch(function () { return null; });
  }

  // ---------------------------------------------------------------------------
  //  Events and boot
  // ---------------------------------------------------------------------------
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && current.zoomState) zoomToIndia();
    if (e.code !== 'Space' && e.key !== ' ') return;
    var tag = (document.activeElement && document.activeElement.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'BUTTON') return;
    spaceHeld = true;
    document.body.classList.add('aq-zooming');
    // space scrolls the page by default; suppress that only over the map
    if (pointerOverMap) e.preventDefault();
  });
  document.addEventListener('keyup', function (e) {
    if (e.code === 'Space' || e.key === ' ') {
      spaceHeld = false;
      document.body.classList.remove('aq-zooming');
    }
  });
  window.addEventListener('blur', function () {
    spaceHeld = false;
    document.body.classList.remove('aq-zooming');
  });
  ui.map.addEventListener('pointerenter', function () { pointerOverMap = true; });
  ui.map.addEventListener('pointerleave', function () { pointerOverMap = false; });

  var resizeTimer = null;
  function redraw() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      render();
      paintPlace();
      drawStrip();
    }, 150);
  }
  window.addEventListener('resize', redraw);

  // The stage can start at zero width — a hidden tab, a collapsed pane, a panel
  // that opens later — in which case there is nothing to draw yet. Watch for it
  // gaining size and draw then, instead of leaving the map blank.
  if (window.ResizeObserver) {
    var seen = 0;
    new ResizeObserver(function (entries) {
      var w = entries[0].contentRect.width;
      if (w > 0 && w !== seen) { seen = w; redraw(); }
    }).observe(ui.map);

    var seenRail = 0;
    new ResizeObserver(function (entries) {
      var w = entries[0].contentRect.width;
      if (w > 0 && w !== seenRail) {
        seenRail = w;
        if (current.city && seriesCache[current.city.id]) drawRailCycles();
      }
    }).observe(document.querySelector('.aq-rail'));
  }

  ui.pollutants.addEventListener('click', function (e) {
    var b = e.target.closest('[data-pol]');
    if (!b) return;
    current.pollutant = b.dataset.pol;
    [].forEach.call(ui.pollutants.querySelectorAll('.aq-pol'), function (x) {
      var on = x === b;
      x.classList.toggle('is-on', on);
      x.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    ensureDaily().then(function () {
      render();
      paintPlace();
    });
  });

  ui.find.addEventListener('input', function () { findRender(this.value); });
  ui.find.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (!findMatches.length) return;
      e.preventDefault();
      findActive = (findActive + (e.key === 'ArrowDown' ? 1 : -1) + findMatches.length) % findMatches.length;
      findHighlight();
    } else if (e.key === 'Enter') {
      if (findActive >= 0) { e.preventDefault(); findChoose(findActive); }
    } else if (e.key === 'Escape') {
      findClose();
      this.value = '';
    }
  });
  ui.findList.addEventListener('click', function (e) {
    var li = e.target.closest('[data-i]');
    if (li) findChoose(+li.dataset.i);
  });
  document.addEventListener('click', function (e) {
    if (!ui.findList.hidden && !e.target.closest('.aq-find')) findClose();
  });

  ui.download.addEventListener('click', openDownload);
  ui.dlScope.addEventListener('click', function (e) {
    var b = e.target.closest('[data-scope]');
    if (b) dlSetScope(b.dataset.scope);
  });
  ui.dlRows.addEventListener('click', function (e) {
    var b = e.target.closest('[data-rows]');
    if (!b) return;
    dl.rows = b.dataset.rows;
    dlRenderRows();
  });
  ui.dlOptions.addEventListener('click', function (e) {
    var b = e.target.closest('[data-v]');
    if (!b) return;
    var v = b.dataset.v;
    var i = dl.picks.indexOf(v);
    if (i === -1) dl.picks.push(v); else dl.picks.splice(i, 1);
    // Update this row in place. Re-rendering the list would rebuild every button
    // under the pointer, lose the scroll position, and drop rapid picks.
    var on = dl.picks.indexOf(v) !== -1;
    b.classList.toggle('is-on', on);
    b.setAttribute('aria-selected', on ? 'true' : 'false');
    dlValidate();
  });
  ui.dlSearch.addEventListener('input', dlRenderList);
  ui.dlFrom.addEventListener('change', dlValidate);
  ui.dlTo.addEventListener('change', dlValidate);
  ui.dlGo.addEventListener('click', function () { dlBuild(); });
  document.getElementById('aqDlCancel').addEventListener('click', function () { ui.dl.close(); });
  document.getElementById('aqDlClose').addEventListener('click', function () { ui.dl.close(); });

  ui.prev.addEventListener('click', function () { stepDay(-1); });
  ui.next.addEventListener('click', function () { stepDay(1); });

  ui.levels.addEventListener('click', function (e) {
    var b = e.target.closest('[data-level]');
    if (!b || b.disabled || b.dataset.level === current.level) return;
    var level = b.dataset.level;
    [].forEach.call(ui.levels.querySelectorAll('button'), function (x) {
      var on = x === b;
      x.classList.toggle('is-on', on);
      x.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    var ready = level === 'cities' ? Promise.resolve() : loadLayer(level);
    ready.then(function () {
      current.level = level;
      render();
    }).catch(function () {
      current.level = 'cities';
      render();
    });
  });

  ui.panelTabs.addEventListener('click', function (e) {
    var b = e.target.closest('[data-view]');
    if (!b || b.disabled) return;
    current.panelView = b.dataset.view;
    [].forEach.call(ui.panelTabs.querySelectorAll('button'), function (x) {
      var on = x === b;
      x.classList.toggle('is-on', on);
      x.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    drawChart(placeDoc());
  });

  ui.chartBtn.addEventListener('click', function () {
    var open = ui.panel.hidden;
    ui.panel.hidden = !open;
    ui.chartBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) drawChart(placeDoc());
  });

  loadStates()
    .then(loadCities)
    .then(loadStations)
    .then(loadSeriesIndex)
    .then(loadCoverage)
    .then(loadDailyIndex)
    .then(loadNational)
    .then(loadLatest)
    .then(function () {
      ui.stamp.textContent = stampText();
      ui.stamp.classList.toggle('is-stale', !latest || !latest.updated);
      // Open on the newest day we hold rather than on the live hour. The hour is
      // a partial sweep — mid-collection it covers a third of the network — and
      // it left the map describing one hour while the rail beside it described a
      // period, with neither agreeing on how much of India was being measured.
      if (dailySpan && dailySpan[1]) current.day = dailySpan[1];
      updateWhen();
      render();
      refreshPlace();
      // The map needs that day's matrix to draw anything, and it arrives after
      // this first paint, so draw again once it is here.
      ensureDaily().then(function () { render(); });
    })
    .catch(function (err) {
      ui.stamp.textContent = 'Could not load: ' + err.message;
    });
})();
