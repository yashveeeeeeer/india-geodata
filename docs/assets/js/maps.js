(function () {
  'use strict';

  var root = document.getElementById('mapMaker');
  if (!root || !window.d3 || !window.topojson) return;

  var BASE = root.dataset.base;
  var STORE_KEY = 'igd-mapmaker-v1';

  function $(id) { return document.getElementById(id); }

  var ui = {
    regionState: $('regionState'), regionDistrict: $('regionDistrict'), districtField: $('districtField'), level: $('level'),
    paste: $('paste'), fileInput: $('fileInput'), fileDrop: $('fileDrop'),
    applyData: $('applyData'), clearData: $('clearData'), sampleData: $('sampleData'),
    matchStatus: $('matchStatus'), unmatched: $('unmatched'), tableSearch: $('tableSearch'), valueTable: $('valueTable'),
    ramp: $('ramp'), scaleMode: $('scaleMode'), customColours: $('customColours'), colourLow: $('colourLow'), colourHigh: $('colourHigh'),
    buckets: $('buckets'), noData: $('noData'), reverse: $('reverse'),
    borderColour: $('borderColour'), borderStyle: $('borderStyle'), borderWidth: $('borderWidth'),
    outlineColour: $('outlineColour'), outlineStyle: $('outlineStyle'), outlineWidth: $('outlineWidth'), scaleHint: $('scaleHint'),
    northArrow: $('northArrow'), northField: $('northField'), northPos: $('northPos'), northSize: $('northSize'),
    background: $('background'), canvas: $('canvas'),
    showNames: $('showNames'), showValues: $('showValues'), showLegend: $('showLegend'),
    labelSize: $('labelSize'), decimals: $('decimals'), numberStyle: $('numberStyle'), prefix: $('prefix'), suffix: $('suffix'),
    legendTitle: $('legendTitle'), legendPos: $('legendPos'), legendSize: $('legendSize'), labelColour: $('labelColour'),
    title: $('title'), titleSize: $('titleSize'), titlePos: $('titlePos'), subtitle: $('subtitle'), subtitleSize: $('subtitleSize'),
    source: $('source'), sourceSize: $('sourceSize'), textColour: $('textColour'), font: $('font'),
    stage: $('stage'), tip: $('mapTip')
  };

  var SETTING_IDS = ['level', 'ramp', 'scaleMode', 'colourLow', 'colourHigh', 'buckets', 'noData', 'reverse',
    'borderColour', 'borderStyle', 'borderWidth', 'outlineColour', 'outlineStyle', 'outlineWidth', 'background', 'canvas',
    'showNames', 'showValues', 'showLegend', 'northArrow', 'northPos', 'northSize',
    'labelSize', 'decimals', 'numberStyle', 'prefix', 'suffix', 'legendTitle', 'legendPos', 'legendSize', 'labelColour',
    'title', 'titleSize', 'titlePos', 'subtitle', 'subtitleSize', 'source', 'sourceSize', 'textColour', 'font'];

  var SCALE_HINTS = {
    quantile: 'Same number of regions in each colour. Suits skewed data such as population, income or GDP, where a few regions dwarf the rest.',
    equal: 'Same value range for each colour. Suits evenly spread data such as literacy rate, vote share or sex ratio, where the ranges themselves matter.',
    continuous: 'One smooth gradient, no groups. Suits gradual change such as rainfall, temperature or elevation, when the overall pattern matters more than exact ranks.'
  };

  var LEVEL_LABEL = { states: 'states', districts: 'districts', subdistricts: 'sub-districts' };

  var layers = {};                       // level -> { topo, object, features }
  var values = { states: {}, districts: {}, subdistricts: {} };   // level -> id -> value
  var valueHeader = '';
  var region = { state: '', district: '' };
  var current = { level: 'districts', features: [], object: null, topo: null };
  var lastMatch = null;

  // ---------------------------------------------------------------------------
  //  Data loading
  // ---------------------------------------------------------------------------
  function loadLayer(level) {
    if (layers[level]) return Promise.resolve(layers[level]);
    ui.stage.classList.add('loading');
    return fetch(BASE + level + '.topo.json')
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (topo) {
        var object = topo.objects[level];
        var fc = topojson.feature(topo, object);
        fc.features.forEach(function (f, i) { f.id = String(object.geometries[i].id); });
        layers[level] = { topo: topo, object: object, features: fc.features };
        return layers[level];
      })
      .finally(function () { ui.stage.classList.remove('loading'); });
  }

  function filterFeatures(layer, level) {
    var feats = layer.features;
    var geoms = layer.object.geometries;
    var keep = [];
    var keepGeoms = [];
    feats.forEach(function (f, i) {
      var p = f.properties;
      if (level === 'states') {
        if (region.state && String(p.lgd) !== region.state) return;
      } else {
        if (region.state && String(p.state_lgd) !== region.state) return;
        if (region.district) {
          if (level === 'districts' && String(p.lgd) !== region.district) return;
          if (level === 'subdistricts' && String(p.dist_lgd) !== region.district) return;
        }
      }
      keep.push(f);
      keepGeoms.push(geoms[i]);
    });
    return { features: keep, object: { type: 'GeometryCollection', geometries: keepGeoms } };
  }

  function refresh() {
    var level = ui.level.value;
    return loadLayer(level).then(function (layer) {
      var sub = filterFeatures(layer, level);
      current = { level: level, features: sub.features, object: sub.object, topo: layer.topo };
      buildTable();
      render();
      save();
    }).catch(function (err) {
      setStatus('Could not load boundaries: ' + err.message);
    });
  }

  function populateStates(layer) {
    var opts = layer.features.map(function (f) { return { lgd: String(f.properties.lgd), name: f.properties.name }; })
      .sort(function (a, b) { return a.name.localeCompare(b.name); });
    opts.forEach(function (o) {
      var el = document.createElement('option');
      el.value = o.lgd; el.textContent = o.name;
      ui.regionState.appendChild(el);
    });
  }

  function populateDistricts() {
    ui.regionDistrict.innerHTML = '<option value="">All districts</option>';
    if (!region.state) { ui.districtField.hidden = true; return; }
    return loadLayer('districts').then(function (layer) {
      var opts = layer.features.filter(function (f) { return String(f.properties.state_lgd) === region.state; })
        .map(function (f) { return { lgd: String(f.properties.lgd), name: f.properties.name }; })
        .sort(function (a, b) { return a.name.localeCompare(b.name); });
      opts.forEach(function (o) {
        var el = document.createElement('option');
        el.value = o.lgd; el.textContent = o.name;
        ui.regionDistrict.appendChild(el);
      });
      ui.regionDistrict.value = region.district;
      if (ui.regionDistrict.value !== region.district) { region.district = ''; }
      ui.districtField.hidden = false;
    });
  }

  // ---------------------------------------------------------------------------
  //  Name matching
  // ---------------------------------------------------------------------------
  var ALIASES = {
    bangalore: 'bengaluru', bangaloreurban: 'bengaluruurban', bangalorerural: 'bengalururural',
    mysore: 'mysuru', belgaum: 'belagavi', gulbarga: 'kalaburagi', bijapur: 'vijayapura', bellary: 'ballari',
    tumkur: 'tumakuru', shimoga: 'shivamogga', chikmagalur: 'chikkamagaluru', hospet: 'vijayanagara',
    allahabad: 'prayagraj', faizabad: 'ayodhya', hoshangabad: 'narmadapuram', orissa: 'odisha',
    pondicherry: 'puducherry', uttaranchal: 'uttarakhand', bombay: 'mumbai', calcutta: 'kolkata', madras: 'chennai',
    poona: 'pune', baroda: 'vadodara', cochin: 'ernakulam', trivandrum: 'thiruvananthapuram', calicut: 'kozhikode',
    cannanore: 'kannur', quilon: 'kollam', alleppey: 'alappuzha', trichur: 'thrissur', palghat: 'palakkad',
    tuticorin: 'thoothukudi', tanjore: 'thanjavur', trichy: 'tiruchirappalli', tiruchirapalli: 'tiruchirappalli',
    nctofdelhi: 'delhi', nationalcapitalterritoryofdelhi: 'delhi', telengana: 'telangana', chattisgarh: 'chhattisgarh',
    andamanandnicobar: 'andamanandnicobarislands', aandnislands: 'andamanandnicobarislands',
    dadraandnagarhaveli: 'dadraandnagarhavelianddamananddiu', damananddiu: 'dadraandnagarhavelianddamananddiu',
    dnhanddd: 'dadraandnagarhavelianddamananddiu', jandk: 'jammuandkashmir', jk: 'jammuandkashmir',
    up: 'uttarpradesh', mp: 'madhyapradesh', hp: 'himachalpradesh', ap: 'andhrapradesh', tn: 'tamilnadu', wb: 'westbengal'
  };

  function compact(s) {
    return String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/&/g, ' and ').replace(/\b(district|dist|distt|dt)\b\.?/g, '').replace(/[^a-z0-9]+/g, '');
  }
  function digitsOnly(s) { return /^\d+$/.test(String(s).trim()); }

  function levenshtein(a, b) {
    if (Math.abs(a.length - b.length) > 2) return 99;
    var prev = [], cur = [], i, j;
    for (j = 0; j <= b.length; j++) prev[j] = j;
    for (i = 1; i <= a.length; i++) {
      cur = [i];
      for (j = 1; j <= b.length; j++) {
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      }
      prev = cur;
    }
    return prev[b.length];
  }

  function buildIndex(feats) {
    var byName = {}, byCode = {};
    feats.forEach(function (f) {
      var p = f.properties;
      var k = compact(p.name);
      (byName[k] = byName[k] || []).push(f);
      byCode[String(p.lgd)] = f;
      if (p.census) byCode[String(p.census).replace(/^0+/, '')] = f;
    });
    return { byName: byName, byCode: byCode, keys: Object.keys(byName) };
  }

  var stateKeys = null;
  function isStateName(v) {
    if (!v || !layers.states) return false;
    if (!stateKeys) {
      stateKeys = {};
      layers.states.features.forEach(function (f) { stateKeys[compact(f.properties.name)] = true; });
    }
    var k = compact(v);
    return !!stateKeys[ALIASES[k] || k];
  }

  function pickByState(cands, stateHint) {
    if (!stateHint) return null;
    var h = compact(stateHint);
    h = ALIASES[h] || h;
    var hits = cands.filter(function (f) { return compact(f.properties.state || '') === h; });
    return hits.length === 1 ? hits[0] : null;
  }

  function matchName(raw, stateHint, idx) {
    var name = String(raw).trim();
    if (!name) return null;
    if (digitsOnly(name)) return idx.byCode[name.replace(/^0+/, '')] || null;

    // "Bilaspur, Himachal Pradesh" or "Bilaspur (HP)"
    var m = name.match(/^(.*?)[\s]*[,(]\s*([^)]+)\)?\s*$/);
    if (m && !stateHint) { name = m[1]; stateHint = m[2]; }

    var k = compact(name);
    k = ALIASES[k] || k;
    var cands = idx.byName[k];
    if (!cands) {
      var pref = idx.keys.filter(function (key) { return key.indexOf(k) === 0 || k.indexOf(key) === 0; });
      if (pref.length === 1) cands = idx.byName[pref[0]];
    }
    if (!cands && k.length >= 5) {
      var close = idx.keys.filter(function (key) { return levenshtein(k, key) <= (k.length > 8 ? 2 : 1); });
      if (close.length === 1) cands = idx.byName[close[0]];
    }
    if (!cands) return null;
    if (cands.length === 1) return cands[0];
    return pickByState(cands, stateHint) || { ambiguous: cands };
  }

  // ---------------------------------------------------------------------------
  //  Parsing pasted / uploaded data
  // ---------------------------------------------------------------------------
  function parseText(text) {
    var lines = text.split(/\r?\n/).filter(function (l) { return l.trim(); });
    if (!lines.length) return [];
    var useTab = lines.some(function (l) { return l.indexOf('\t') !== -1; });
    return useTab ? d3.tsvParseRows(lines.join('\n')) : d3.csvParseRows(lines.join('\n'));
  }

  function toNumber(v) {
    if (typeof v === 'number') return isFinite(v) ? v : NaN;
    var s = String(v).trim().replace(/[₹$,%\s]/g, '').replace(/^\((.*)\)$/, '-$1');
    if (s === '' || s === '-') return NaN;
    return Number(s);
  }

  function applyRows(rows) {
    rows = rows.map(function (r) { return r.map(function (c) { return c == null ? '' : String(c).trim(); }); })
      .filter(function (r) { return r.some(function (c) { return c !== ''; }); });
    if (!rows.length) return;

    var level = current.level;
    var ncol = d3.max(rows, function (r) { return r.length; });
    var nameCol = 0, stateCol = -1, valueCol = ncol - 1;
    if (ncol < 2) { setStatus('Need at least two columns: name and value.'); return; }

    // header detection
    var header = null;
    var numericRows = rows.filter(function (r) { return !isNaN(toNumber(r[valueCol])); }).length;
    if (numericRows >= 1 && isNaN(toNumber(rows[0][valueCol]))) {
      header = rows[0];
      valueHeader = header[valueCol];
      rows = rows.slice(1);
    }

    // with three or more columns, work out which of the first two holds the state
    if (ncol >= 3 && level !== 'states') {
      var headerState = header ? [0, 1].filter(function (c) { return /^(state|ut|state\/ut|st)$/.test(compact(header[c] || '')); }) : [];
      if (headerState.length === 1) {
        stateCol = headerState[0]; nameCol = stateCol === 0 ? 1 : 0;
      } else {
        var hits = [0, 1].map(function (c) { return rows.filter(function (r) { return isStateName(r[c]); }).length; });
        if (hits[0] || hits[1]) { stateCol = hits[0] >= hits[1] ? 0 : 1; nameCol = stateCol === 0 ? 1 : 0; }
      }
    }

    var idx = buildIndex(current.features);
    var vals = values[level];
    var matched = 0, unmatched = [], ambiguous = [];
    rows.forEach(function (r) {
      var f = matchName(r[nameCol], stateCol >= 0 ? r[stateCol] : '', idx);
      if (!f) { unmatched.push(r[nameCol]); return; }
      if (f.ambiguous) { ambiguous.push(r[nameCol]); return; }
      var n = toNumber(r[valueCol]);
      vals[f.id] = isNaN(n) ? r[valueCol] : n;
      matched++;
    });
    lastMatch = { matched: matched, unmatched: unmatched, ambiguous: ambiguous };
    reportMatch();
    buildTable();
    render();
    save();
  }

  function reportMatch() {
    if (!lastMatch) { ui.matchStatus.textContent = ''; ui.unmatched.innerHTML = ''; return; }
    var parts = ['<strong>' + lastMatch.matched + '</strong> matched'];
    if (lastMatch.unmatched.length) parts.push('<strong>' + lastMatch.unmatched.length + '</strong> not found');
    if (lastMatch.ambiguous.length) parts.push('<strong>' + lastMatch.ambiguous.length + '</strong> ambiguous (add a state column)');
    ui.matchStatus.innerHTML = parts.join(' · ');
    ui.unmatched.innerHTML = lastMatch.unmatched.concat(lastMatch.ambiguous).map(function (n) {
      return '<span>' + escapeHtml(n) + '</span>';
    }).join('');
  }

  function setStatus(msg) { ui.matchStatus.textContent = msg; ui.unmatched.innerHTML = ''; }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function readFile(file) {
    if (!file) return;
    var name = file.name.toLowerCase();
    if (/\.(xlsx|xls)$/.test(name)) {
      if (!window.XLSX) { setStatus('Excel support is still loading, try again in a second.'); return; }
      var fr = new FileReader();
      fr.onload = function () {
        var wb = XLSX.read(new Uint8Array(fr.result), { type: 'array' });
        var ws = wb.Sheets[wb.SheetNames[0]];
        applyRows(XLSX.utils.sheet_to_json(ws, { header: 1, raw: true, defval: '' }));
      };
      fr.readAsArrayBuffer(file);
    } else {
      var tr = new FileReader();
      tr.onload = function () { ui.paste.value = tr.result; applyRows(parseText(tr.result)); };
      tr.readAsText(file);
    }
  }

  // ---------------------------------------------------------------------------
  //  Value table
  // ---------------------------------------------------------------------------
  function buildTable() {
    var level = current.level;
    var vals = values[level];
    var q = compact(ui.tableSearch.value);
    var feats = current.features.slice().sort(function (a, b) { return a.properties.name.localeCompare(b.properties.name); });
    var showParent = !region.state && level !== 'states';
    var html = '';
    feats.forEach(function (f) {
      var p = f.properties;
      if (q && compact(p.name).indexOf(q) === -1 && compact(p.state || '').indexOf(q) === -1) return;
      var v = vals[f.id];
      html += '<tr><td title="' + escapeHtml(p.name) + '">' + escapeHtml(p.name) +
        (showParent ? ' <small>' + escapeHtml(level === 'subdistricts' ? p.district : p.state) + '</small>' : '') +
        '</td><td><input type="text" data-id="' + f.id + '" value="' + (v == null ? '' : escapeHtml(v)) + '"></td></tr>';
    });
    ui.valueTable.innerHTML = html || '<tr><td colspan="2"><small>No regions</small></td></tr>';
  }

  ui.valueTable.addEventListener('change', function (e) {
    var input = e.target.closest('input[data-id]');
    if (!input) return;
    var vals = values[current.level];
    var raw = input.value.trim();
    if (raw === '') delete vals[input.dataset.id];
    else { var n = toNumber(raw); vals[input.dataset.id] = isNaN(n) ? raw : n; }
    render();
    save();
  });

  // ---------------------------------------------------------------------------
  //  Number formatting
  // ---------------------------------------------------------------------------
  function indianGroup(intStr) {
    if (intStr.length <= 3) return intStr;
    var last3 = intStr.slice(-3), rest = intStr.slice(0, -3);
    return rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + last3;
  }

  function fmt(v) {
    if (v == null || v === '') return '';
    if (typeof v !== 'number') return String(v);
    var d = +ui.decimals.value || 0;
    var style = ui.numberStyle.value;
    var neg = v < 0 ? '-' : '';
    var a = Math.abs(v);
    var s;
    if (style === 'lakh' && a >= 1e5) {
      s = a >= 1e7 ? (a / 1e7).toFixed(Math.max(d, 1)) + ' Cr' : (a / 1e5).toFixed(Math.max(d, 1)) + ' L';
    } else if (style === 'metric' && a >= 1e3) {
      s = a >= 1e9 ? (a / 1e9).toFixed(Math.max(d, 1)) + 'B' : a >= 1e6 ? (a / 1e6).toFixed(Math.max(d, 1)) + 'M' : (a / 1e3).toFixed(Math.max(d, 1)) + 'K';
    } else {
      var fixed = a.toFixed(d).split('.');
      var intPart = fixed[0];
      if (style === 'indian') intPart = indianGroup(intPart);
      else if (style === 'metric') intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
      s = intPart + (fixed[1] ? '.' + fixed[1] : '');
    }
    return (ui.prefix.value || '') + neg + s + (ui.suffix.value || '');
  }

  // ---------------------------------------------------------------------------
  //  Colour scale
  // ---------------------------------------------------------------------------
  var CLAMPED = { Greys: 1, Blues: 1, Greens: 1, Oranges: 1, Reds: 1, Purples: 1, YlOrRd: 1, YlGnBu: 1 };

  function interpolator() {
    var name = ui.ramp.value;
    var base;
    if (name === 'custom') base = d3.interpolateLab(ui.colourLow.value, ui.colourHigh.value);
    else {
      var fn = d3['interpolate' + name];
      base = CLAMPED[name] ? function (t) { return fn(0.08 + 0.87 * t); } : fn;
    }
    return ui.reverse.checked ? function (t) { return base(1 - t); } : base;
  }

  function buildScale(vals) {
    var entries = current.features.map(function (f) { return vals[f.id]; }).filter(function (v) { return v != null && v !== ''; });
    if (!entries.length) return null;
    var nums = entries.filter(function (v) { return typeof v === 'number'; });
    var interp = interpolator();

    if (nums.length < entries.length / 2) {
      var cats = Array.from(new Set(entries.map(String))).sort();
      var colours = d3.quantize(interp, Math.max(cats.length, 2)).slice(0, cats.length);
      var ord = d3.scaleOrdinal().domain(cats).range(colours);
      return { type: 'categorical', scale: function (v) { return ord(String(v)); }, categories: cats, colours: colours };
    }

    var ext = d3.extent(nums);
    var mode = ui.scaleMode.value;
    if (mode === 'continuous' || ext[0] === ext[1]) {
      var seq = d3.scaleSequential(interp).domain(ext);
      return { type: 'continuous', scale: function (v) { return typeof v === 'number' ? seq(v) : null; }, extent: ext, interp: interp };
    }
    var k = Math.min(9, Math.max(2, +ui.buckets.value || 5));
    var range = d3.quantize(interp, k);
    var sc = mode === 'quantile' ? d3.scaleQuantile().domain(nums).range(range) : d3.scaleQuantize().domain(ext).range(range);
    var thresholds = mode === 'quantile' ? sc.quantiles() : sc.thresholds();
    return { type: 'buckets', scale: function (v) { return typeof v === 'number' ? sc(v) : null; }, thresholds: thresholds, extent: ext, colours: range };
  }

  // ---------------------------------------------------------------------------
  //  Render
  // ---------------------------------------------------------------------------
  var svgNode = null;
  var offsets = {};          // drag offsets per overlay: { title, source, legend, north } -> { dx, dy }

  function intersects(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }

  function makeDraggable(sel, key, base) {
    var off = offsets[key] || { dx: 0, dy: 0 };
    function apply() { sel.attr('transform', 'translate(' + (base.x + off.dx) + ',' + (base.y + off.dy) + ')'); }
    apply();
    sel.attr('class', 'drag');
    sel.call(d3.drag()
      .on('start', function () { off = offsets[key] = offsets[key] || { dx: 0, dy: 0 }; })
      .on('drag', function (e) {
        var k = (+svgNode.getAttribute('width')) / svgNode.getBoundingClientRect().width;
        off.dx += e.dx * k; off.dy += e.dy * k;
        apply();
      })
      .on('end', function () { save(); }));
  }

  function render() {
    var size = ui.canvas.value.split('x').map(Number);
    var W = size[0], H = size[1];
    var pad = Math.round(W * 0.04);
    var font = ui.font.value;
    var textColour = ui.textColour.value;
    var bg = ui.background.value;
    var vals = values[current.level];
    var colour = buildScale(vals);
    var noData = ui.noData.value;

    ui.stage.innerHTML = '';
    var svg = d3.select(ui.stage).append('svg')
      .attr('xmlns', 'http://www.w3.org/2000/svg')
      .attr('viewBox', '0 0 ' + W + ' ' + H)
      .attr('width', W).attr('height', H)
      .attr('font-family', font);
    svgNode = svg.node();

    var defs = svg.append('defs');
    defs.append('pattern').attr('id', 'hatch').attr('width', 6).attr('height', 6).attr('patternUnits', 'userSpaceOnUse')
      .attr('patternTransform', 'rotate(45)')
      .append('line').attr('x1', 0).attr('y1', 0).attr('x2', 0).attr('y2', 6).attr('stroke', '#9ca3af').attr('stroke-width', 1);

    if (bg !== 'transparent') svg.append('rect').attr('width', W).attr('height', H).attr('fill', bg);

    // --- text block: title + subtitle in one draggable group, source in another ---
    var titleSize = +ui.titleSize.value, subSize = +ui.subtitleSize.value, srcSize = +ui.sourceSize.value;
    var tpos = ui.titlePos.value;
    var anchor = tpos[1] === 'l' ? 'start' : tpos[1] === 'c' ? 'middle' : 'end';
    var tx = anchor === 'start' ? pad : anchor === 'middle' ? W / 2 : W - pad;
    var blockH = (ui.title.value ? titleSize * 1.35 : 0) + (ui.subtitle.value ? subSize * 1.4 : 0);
    var srcH = ui.source.value ? srcSize * 1.8 : 0;
    var gap = blockH ? pad * 0.5 : 0;
    var mapTop, mapBottom, blockY;
    if (tpos[0] === 't') {
      blockY = pad;
      mapTop = pad + blockH + gap;
      mapBottom = H - pad - srcH;
    } else {
      mapTop = pad;
      mapBottom = H - pad - srcH - blockH - gap;
      blockY = mapBottom + gap;
    }

    var mapG = svg.append('g');          // map layers
    var overG = svg.append('g');         // overlays, always above the map

    if (ui.title.value || ui.subtitle.value) {
      var tg = overG.append('g');
      var y = blockY;
      if (ui.title.value) {
        y += titleSize;
        tg.append('text').attr('x', tx).attr('y', y).attr('text-anchor', anchor).attr('font-size', titleSize).attr('font-weight', 700).attr('fill', textColour).text(ui.title.value);
        y += titleSize * 0.35;
      }
      if (ui.subtitle.value) {
        y += subSize;
        tg.append('text').attr('x', tx).attr('y', y).attr('text-anchor', anchor).attr('font-size', subSize).attr('fill', textColour).attr('opacity', 0.75).text(ui.subtitle.value);
      }
      makeDraggable(tg, 'title', { x: 0, y: 0 });
    }
    if (ui.source.value) {
      var sg = overG.append('g');
      sg.append('text').attr('x', tx).attr('y', H - pad).attr('text-anchor', anchor).attr('font-size', srcSize).attr('fill', textColour).attr('opacity', 0.65).text(ui.source.value);
      makeDraggable(sg, 'source', { x: 0, y: 0 });
    }

    if (!current.features.length) return;

    // --- projection ---
    var fc = { type: 'FeatureCollection', features: current.features };
    var projection = d3.geoMercator();
    var path = d3.geoPath(projection);
    function fit() { projection.fitExtent([[pad, mapTop], [W - pad, mapBottom]], fc); }
    fit();

    // --- overlay placement: pick a corner that does not cover the map, else make room ---
    var occupied = [];
    function cornerBox(corner, w, h) {
      return {
        x: corner[1] === 'l' ? pad : W - pad - w,
        y: corner[0] === 't' ? mapTop : mapBottom - h,
        w: w, h: h
      };
    }
    function hits(box) {
      if (occupied.some(function (o) { return intersects(o, box); })) return true;
      return current.features.some(function (f) {
        var b = path.bounds(f);
        return intersects({ x: b[0][0], y: b[0][1], w: b[1][0] - b[0][0], h: b[1][1] - b[0][1] }, box);
      });
    }
    function place(key, sel, pref) {
      var bb = sel.node().getBBox();
      var w = bb.width, h = bb.height;
      var origin = { x: -bb.x, y: -bb.y };      // shift so the group's top-left sits on the box
      var box;
      if (offsets[key]) {
        box = cornerBox(pref, w, h);
      } else {
        var order = [pref].concat(['tl', 'tr', 'bl', 'br'].filter(function (c) { return c !== pref; }));
        for (var i = 0; i < order.length && !box; i++) {
          var cand = cornerBox(order[i], w, h);
          if (!hits(cand)) box = cand;
        }
        if (!box) {
          // reserve a band above or below the map, then refit the map
          var band = h + pad * 0.5;
          if (pref[0] === 'b') { mapBottom -= band; fit(); box = { x: cornerBox(pref, w, h).x, y: mapBottom + pad * 0.5, w: w, h: h }; }
          else { mapTop += band; fit(); box = { x: cornerBox(pref, w, h).x, y: mapTop - band, w: w, h: h }; }
        }
      }
      occupied.push(box);
      makeDraggable(sel, key, { x: box.x + origin.x, y: box.y + origin.y });
    }

    var arrow = ui.northArrow.checked ? drawNorthArrow(overG, textColour) : null;
    var legend = (ui.showLegend.checked && colour) ? drawLegend(overG, colour, textColour) : null;
    if (arrow) place('north', arrow, ui.northPos.value);
    if (legend) place('legend', legend, ui.legendPos.value);

    // --- map ---
    var bw = ui.borderStyle.value === 'none' ? 0 : +ui.borderWidth.value;
    var ow = ui.outlineStyle.value === 'none' ? 0 : +ui.outlineWidth.value;
    var bc = ui.borderColour.value, oc = ui.outlineColour.value;
    function dash(style, w) {
      if (style === 'dashed') return (w * 4) + ' ' + (w * 3);
      if (style === 'dotted') return '0.1 ' + (w * 2);
      return null;
    }
    var borderDash = dash(ui.borderStyle.value, Math.max(bw, 0.5));
    var outlineDash = dash(ui.outlineStyle.value, Math.max(ow, 0.5));

    mapG.selectAll('path').data(current.features).enter().append('path')
      .attr('class', 'region')
      .attr('d', path)
      .attr('data-id', function (d) { return d.id; })
      .attr('fill', function (d) {
        var v = vals[d.id];
        var c = colour && v != null && v !== '' ? colour.scale(v) : null;
        if (c) return c;
        if (noData === 'hatch') return 'url(#hatch)';
        if (noData === 'none') return 'none';
        return noData;
      })
      .attr('stroke', bc).attr('stroke-width', bw).attr('stroke-linejoin', 'round')
      .attr('stroke-dasharray', borderDash).attr('stroke-linecap', ui.borderStyle.value === 'dotted' ? 'round' : null)
      .on('mousemove', function (e, d) {
        var p = d.properties;
        var label = p.name + (p.state && current.level !== 'states' ? ', ' + (current.level === 'subdistricts' ? p.district : p.state) : '');
        var v = vals[d.id];
        ui.tip.textContent = label + ' · ' + (v == null || v === '' ? 'no data' : fmt(v));
        ui.tip.style.display = 'block';
        ui.tip.style.left = e.clientX + 'px'; ui.tip.style.top = e.clientY + 'px';
      })
      .on('mouseleave', function () { ui.tip.style.display = 'none'; });

    // --- boundary meshes ---
    var topo = current.topo, obj = current.object;
    function outline(filter, width) {
      if (!width) return;
      mapG.append('path').attr('d', path(topojson.mesh(topo, obj, filter)))
        .attr('fill', 'none').attr('stroke', oc).attr('stroke-width', width).attr('stroke-linejoin', 'round')
        .attr('stroke-dasharray', outlineDash).attr('stroke-linecap', ui.outlineStyle.value === 'dotted' ? 'round' : null);
    }
    if (current.level === 'subdistricts' && !region.district) {
      outline(function (a, b) { return a !== b && a.properties.dist_lgd !== b.properties.dist_lgd; }, ow * 0.5);
    }
    if (current.level !== 'states' && !region.state) {
      outline(function (a, b) { return a !== b && a.properties.state_lgd !== b.properties.state_lgd; }, ow * 0.8);
    }
    outline(function (a, b) { return a === b; }, ow);

    // --- labels ---
    if (ui.showNames.checked || ui.showValues.checked) {
      var ls = +ui.labelSize.value;
      var halo = bg === 'transparent' ? '#ffffff' : bg;
      var lg = mapG.append('g').attr('font-size', ls).attr('fill', ui.labelColour.value).attr('text-anchor', 'middle')
        .attr('paint-order', 'stroke').attr('stroke', halo).attr('stroke-width', ls * 0.25).attr('stroke-linejoin', 'round');
      current.features.forEach(function (d) {
        var v = vals[d.id];
        if (noData === 'none' && (v == null || v === '')) return;
        var lines = [];
        if (ui.showNames.checked) lines.push(d.properties.name);
        if (ui.showValues.checked && v != null && v !== '') lines.push(fmt(v));
        if (!lines.length) return;
        var b = path.bounds(d);
        var bwid = b[1][0] - b[0][0], bhei = b[1][1] - b[0][1];
        var widest = d3.max(lines, function (l) { return l.length; }) * ls * 0.58;
        if (bwid < widest * 0.85 || bhei < ls * 1.2 * lines.length) return;
        var c = path.centroid(d);
        if (isNaN(c[0])) return;
        var t = lg.append('text').attr('x', c[0]).attr('y', c[1] - (lines.length - 1) * ls * 0.6);
        lines.forEach(function (l, i) {
          t.append('tspan').attr('x', c[0]).attr('dy', i ? ls * 1.15 : 0).attr('font-weight', i === 0 && lines.length > 1 ? 600 : 400).text(l);
        });
      });
    }
  }

  // North arrow: the letter N over a half-filled triangle. Built at the origin; render() positions it.
  function drawNorthArrow(parent, textColour) {
    var s = +ui.northSize.value || 60;
    var g = parent.append('g')
      .attr('fill', textColour).attr('stroke', textColour).attr('stroke-width', Math.max(0.75, s * 0.02)).attr('stroke-linejoin', 'round');
    var tip = s * 0.34, base = s * 0.98, notch = s * 0.86, hw = s * 0.2;
    g.append('text').attr('y', s * 0.26).attr('text-anchor', 'middle').attr('font-size', s * 0.3).attr('font-weight', 700).attr('stroke', 'none').text('N');
    g.append('path').attr('d', 'M0,' + tip + ' L' + (-hw) + ',' + base + ' L0,' + notch + ' Z');
    g.append('path').attr('d', 'M0,' + tip + ' L' + hw + ',' + base + ' L0,' + notch + ' Z').attr('fill', 'none');
    return g;
  }

  // Legend: built at the origin; render() positions it.
  function drawLegend(parent, colour, textColour) {
    var fs = +ui.legendSize.value;
    var sw = fs * 1.3, gap = fs * 0.35;
    var title = ui.legendTitle.value || valueHeader || '';
    var items = [];
    if (colour.type === 'buckets') {
      var edges = [colour.extent[0]].concat(colour.thresholds, [colour.extent[1]]);
      colour.colours.forEach(function (c, i) {
        items.push({ colour: c, label: fmt(edges[i]) + ' – ' + fmt(edges[i + 1]) });
      });
    } else if (colour.type === 'categorical') {
      colour.categories.forEach(function (cat, i) { items.push({ colour: colour.colours[i], label: cat }); });
    }

    var lg = parent.append('g').attr('font-size', fs).attr('fill', textColour);
    var y = 0;
    if (title) { lg.append('text').attr('x', 0).attr('y', fs).attr('font-weight', 600).text(title); y = fs * 1.6; }

    if (colour.type === 'continuous') {
      var grad = d3.select(svgNode).select('defs').append('linearGradient').attr('id', 'legendGrad');
      d3.range(0, 1.001, 0.1).forEach(function (t) { grad.append('stop').attr('offset', (t * 100) + '%').attr('stop-color', colour.interp(t)); });
      var width = fs * 14;
      lg.append('rect').attr('x', 0).attr('y', y).attr('width', width).attr('height', fs * 0.9).attr('fill', 'url(#legendGrad)');
      lg.append('text').attr('x', 0).attr('y', y + fs * 2).text(fmt(colour.extent[0]));
      lg.append('text').attr('x', width).attr('y', y + fs * 2).attr('text-anchor', 'end').text(fmt(colour.extent[1]));
      y += fs * 2.2;
    } else {
      items.forEach(function (it) {
        lg.append('rect').attr('x', 0).attr('y', y).attr('width', sw).attr('height', sw).attr('fill', it.colour).attr('stroke', '#00000022');
        lg.append('text').attr('x', sw + gap * 2).attr('y', y + sw * 0.72).text(it.label);
        y += sw + gap;
      });
    }
    if (ui.noData.value !== 'none' && current.features.some(function (f) { var v = values[current.level][f.id]; return v == null || v === ''; })) {
      var nd = ui.noData.value === 'hatch' ? 'url(#hatch)' : ui.noData.value;
      lg.append('rect').attr('x', 0).attr('y', y).attr('width', sw).attr('height', sw).attr('fill', nd).attr('stroke', '#00000033');
      lg.append('text').attr('x', sw + gap * 2).attr('y', y + sw * 0.72).text('No data');
    }
    return lg;
  }

  // ---------------------------------------------------------------------------
  //  Export
  // ---------------------------------------------------------------------------
  function slug() {
    var s = (ui.title.value || 'india-' + current.level).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    return s || 'map';
  }

  function svgString() {
    var clone = svgNode.cloneNode(true);
    clone.querySelectorAll('[data-id], [class]').forEach(function (el) { el.removeAttribute('data-id'); el.removeAttribute('class'); });
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(clone);
  }

  function download(blob, name) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 200);
  }

  function rasterize(scale) {
    return new Promise(function (resolve, reject) {
      var W = +svgNode.getAttribute('width'), H = +svgNode.getAttribute('height');
      var url = URL.createObjectURL(new Blob([svgString()], { type: 'image/svg+xml;charset=utf-8' }));
      var img = new Image();
      img.onload = function () {
        var c = document.createElement('canvas');
        c.width = Math.round(W * scale); c.height = Math.round(H * scale);
        var ctx = c.getContext('2d');
        ctx.drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url);
        resolve(c);
      };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error('Could not render image')); };
      img.src = url;
    });
  }

  function exportPng(scale) {
    rasterize(scale).then(function (c) {
      c.toBlob(function (b) { download(b, slug() + (scale > 1 ? '@' + scale + 'x' : '') + '.png'); }, 'image/png');
    });
  }

  function exportPdf() {
    if (!window.jspdf) { alert('PDF support is still loading, try again in a second.'); return; }
    rasterize(3).then(function (c) {
      var W = +svgNode.getAttribute('width'), H = +svgNode.getAttribute('height');
      var doc = new window.jspdf.jsPDF({ orientation: W >= H ? 'landscape' : 'portrait', unit: 'px', format: [W, H], hotfixes: ['px_scaling'] });
      doc.addImage(c.toDataURL('image/png'), 'PNG', 0, 0, W, H);
      doc.save(slug() + '.pdf');
    });
  }

  function exportCsv() {
    var vals = values[current.level];
    var rows = [['name', 'parent', 'lgd_code', 'value']];
    current.features.forEach(function (f) {
      var p = f.properties;
      var v = vals[f.id];
      rows.push([p.name, current.level === 'subdistricts' ? p.district : (p.state || ''), p.lgd, v == null ? '' : v]);
    });
    download(new Blob([d3.csvFormatRows(rows)], { type: 'text/csv' }), slug() + '.csv');
  }

  document.querySelectorAll('[data-export]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!svgNode) return;
      var kind = btn.dataset.export;
      if (kind === 'png') exportPng(+btn.dataset.scale || 1);
      else if (kind === 'svg') download(new Blob([svgString()], { type: 'image/svg+xml' }), slug() + '.svg');
      else if (kind === 'pdf') exportPdf();
      else if (kind === 'csv') exportCsv();
    });
  });

  // ---------------------------------------------------------------------------
  //  Persistence
  // ---------------------------------------------------------------------------
  var saveTimer = null;
  function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      var settings = {};
      SETTING_IDS.forEach(function (id) { var el = ui[id]; settings[id] = el.type === 'checkbox' ? el.checked : el.value; });
      try {
        localStorage.setItem(STORE_KEY, JSON.stringify({ settings: settings, region: region, values: values, valueHeader: valueHeader, offsets: offsets }));
      } catch (e) { /* storage unavailable */ }
    }, 300);
  }

  function restore() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (!raw) return;
      var data = JSON.parse(raw);
      Object.keys(data.settings || {}).forEach(function (id) {
        var el = ui[id];
        if (!el) return;
        if (el.type === 'checkbox') el.checked = !!data.settings[id]; else el.value = data.settings[id];
      });
      if (data.values) values = Object.assign({ states: {}, districts: {}, subdistricts: {} }, data.values);
      if (data.region) region = data.region;
      valueHeader = data.valueHeader || '';
      offsets = data.offsets || {};
    } catch (e) { /* ignore */ }
  }

  // ---------------------------------------------------------------------------
  //  Events
  // ---------------------------------------------------------------------------
  ui.regionState.addEventListener('change', function () {
    region.state = ui.regionState.value;
    region.district = '';
    if (region.state && ui.level.value === 'states') ui.level.value = 'districts';
    Promise.resolve(populateDistricts()).then(refresh);
  });
  ui.regionDistrict.addEventListener('change', function () {
    region.district = ui.regionDistrict.value;
    if (region.district && ui.level.value !== 'subdistricts') ui.level.value = 'subdistricts';
    refresh();
  });
  ui.level.addEventListener('change', function () {
    if (ui.level.value === 'districts' && region.district) { region.district = ''; ui.regionDistrict.value = ''; }
    refresh();
  });

  ui.applyData.addEventListener('click', function () { applyRows(parseText(ui.paste.value)); });
  ui.paste.addEventListener('paste', function () { setTimeout(function () { applyRows(parseText(ui.paste.value)); }, 0); });
  ui.clearData.addEventListener('click', function () {
    values[current.level] = {};
    ui.paste.value = ''; lastMatch = null; valueHeader = '';
    reportMatch(); buildTable(); render(); save();
  });
  ui.sampleData.addEventListener('click', function () {
    var vals = values[current.level] = {};
    current.features.forEach(function (f, i) {
      var seed = Math.sin(i * 12.9898 + f.properties.lgd) * 43758.5453;
      vals[f.id] = Math.round((seed - Math.floor(seed)) * 1000) / 10;
    });
    valueHeader = 'Sample values';
    lastMatch = null; reportMatch(); buildTable(); render(); save();
  });
  ui.fileInput.addEventListener('change', function () { readFile(ui.fileInput.files[0]); ui.fileInput.value = ''; });
  ['dragenter', 'dragover'].forEach(function (ev) {
    ui.fileDrop.addEventListener(ev, function (e) { e.preventDefault(); ui.fileDrop.classList.add('over'); });
  });
  ['dragleave', 'drop'].forEach(function (ev) {
    ui.fileDrop.addEventListener(ev, function (e) { e.preventDefault(); ui.fileDrop.classList.remove('over'); });
  });
  ui.fileDrop.addEventListener('drop', function (e) { readFile(e.dataTransfer.files[0]); });
  ui.tableSearch.addEventListener('input', buildTable);
  $('resetLayout').addEventListener('click', function () { offsets = {}; render(); save(); });
  var POS_KEYS = { titlePos: ['title', 'source'], legendPos: ['legend'], northPos: ['north'] };
  Object.keys(POS_KEYS).forEach(function (id) {
    ui[id].addEventListener('change', function () { POS_KEYS[id].forEach(function (k) { delete offsets[k]; }); });
  });

  SETTING_IDS.forEach(function (id) {
    if (id === 'level') return;
    var el = ui[id];
    var ev = (el.tagName === 'INPUT' && (el.type === 'text' || el.type === 'number')) ? 'input' : 'change';
    el.addEventListener(ev, function () {
      syncUi();
      render(); save();
    });
    if (ev === 'input') el.addEventListener('change', function () { render(); save(); });
  });

  // ---------------------------------------------------------------------------
  //  Boot
  // ---------------------------------------------------------------------------
  function syncUi() {
    ui.customColours.hidden = ui.ramp.value !== 'custom';
    ui.northField.hidden = !ui.northArrow.checked;
    ui.scaleHint.textContent = SCALE_HINTS[ui.scaleMode.value] || '';
  }

  restore();
  syncUi();
  loadLayer('states').then(function (layer) {
    populateStates(layer);
    ui.regionState.value = region.state;
    if (ui.regionState.value !== region.state) region.state = '';
    return populateDistricts();
  }).then(refresh);
})();
