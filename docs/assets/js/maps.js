(function () {
  'use strict';

  var root = document.getElementById('mapMaker');
  if (!root) return;
  var statusEl = document.getElementById('matchStatus');
  if (!window.fetch || !window.Promise || !Element.prototype.closest || !window.URL) {
    if (statusEl) statusEl.textContent = 'This browser is too old for the map maker. Use a recent Chrome, Firefox, Edge or Safari.';
    return;
  }
  if (!window.d3 || !window.topojson) {
    if (statusEl) statusEl.textContent = 'The map library could not be loaded. Check your connection and reload the page.';
    return;
  }

  if (!window.IGDMapCore) { if (statusEl) statusEl.textContent = 'Part of the map maker did not load. Reload the page.'; return; }
  var Core = window.IGDMapCore;
  var FONTS = Core.FONTS, HEX = Core.HEX, ALIASES = Core.ALIASES, HEADER_WORDS = Core.HEADER_WORDS;
  var CLAMPED = Core.CLAMPED, QUALITATIVE = Core.QUALITATIVE, DIVERGING = Core.DIVERGING;
  var compact = Core.compact, tokenKey = Core.tokenKey, digitsOnly = Core.digitsOnly, editDistance = Core.editDistance;
  var levenshtein = Core.levenshtein, similarity = Core.similarity, isEmptyToken = Core.isEmptyToken, toNumber = Core.toNumber;
  var wrapText = Core.wrapText, indianGroup = Core.indianGroup, computeAutoDecimals = Core.computeAutoDecimals;
  function parseText(text) { return Core.parseText(text, d3); }
  function fmtNumber(v, d) { return Core.fmtNumber(v, d, ui.numberStyle.value); }

  var BASE = root.dataset.base;
  var ASSETS = root.dataset.assets || BASE.replace(/maps\/data\/$/, 'assets/');
  var DATA_V = root.dataset.v ? '?v=' + encodeURIComponent(root.dataset.v) : '';
  var XLSX_URL = ASSETS + 'vendor/xlsx.full.min.js' + DATA_V;
  var JSPDF_URL = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
  var JSPDF_SRI = 'sha384-JcnsjUPPylna1s1fvi1u12X5qjY5OL56iySh75FdtrwhO/SWXgMjoVqcKyIIWOLk';
  var scriptLoads = {};
  function loadScript(url, sriHash) {
    if (scriptLoads[url]) return scriptLoads[url];
    scriptLoads[url] = new Promise(function (resolve, reject) {
      var el = document.createElement('script');
      el.src = url;
      if (sriHash) { el.integrity = sriHash; el.crossOrigin = 'anonymous'; }
      el.onload = resolve;
      el.onerror = function () { delete scriptLoads[url]; reject(new Error('could not load ' + url.split('/').pop().split('?')[0])); };
      document.head.appendChild(el);
    });
    return scriptLoads[url];
  }
  var STORE_KEY = 'igd-mapmaker-v1';

  function $(id) { return document.getElementById(id); }

  var ui = {
    regionState: $('regionState'), regionDistrict: $('regionDistrict'), districtField: $('districtField'), level: $('level'),
    paste: $('paste'), fileInput: $('fileInput'), fileDrop: $('fileDrop'),
    applyData: $('applyData'), clearData: $('clearData'),
    matchStatus: $('matchStatus'), unmatched: $('unmatched'), tableSearch: $('tableSearch'), valueTable: $('valueTable'),
    ramp: $('ramp'), scaleMode: $('scaleMode'), customColours: $('customColours'), colourLow: $('colourLow'), colourHigh: $('colourHigh'),
    buckets: $('buckets'), noData: $('noData'), reverse: $('reverse'),
    borderColour: $('borderColour'), borderStyle: $('borderStyle'), borderWidth: $('borderWidth'),
    outlineColour: $('outlineColour'), outlineStyle: $('outlineStyle'), outlineWidth: $('outlineWidth'), scaleHint: $('scaleHint'),
    northArrow: $('northArrow'), northField: $('northField'), northPos: $('northPos'), northSize: $('northSize'),
    background: $('background'), canvas: $('canvas'), frameStyle: $('frameStyle'), frameColour: $('frameColour'),
    mapZoom: $('mapZoom'), zoomIn: $('zoomIn'), zoomOut: $('zoomOut'), zoomReset: $('zoomReset'), zoomValue: $('zoomValue'),
    showNames: $('showNames'), showValues: $('showValues'), showLegend: $('showLegend'),
    labelSize: $('labelSize'), decimals: $('decimals'), numberStyle: $('numberStyle'), prefix: $('prefix'), suffix: $('suffix'),
    legendTitle: $('legendTitle'), legendPos: $('legendPos'), legendSize: $('legendSize'), labelColour: $('labelColour'), textColour: $('textColour'),
    assetList: $('assetList'), selTools: $('selTools'), selDelete: $('selDelete'),
    unmatchedBadge: $('unmatchedBadge'), regionList: $('regionList'), learnedList: $('learnedList'), learnedBox: $('learnedBox'),
    bucketsField: $('bucketsField'), stageLoading: $('stageLoading'), startOver: $('startOver'), copyImage: $('copyImage'), reportLink: $('reportLink'), exportRow: $('exportRow'),
    sourcePick: $('sourcePick'), sheetField: $('sheetField'), sheetPick: $('sheetPick'), colField: $('colField'), colPick: $('colPick'),
    stage: $('stage'), tip: $('mapTip')
  };

  var SETTING_IDS = ['level', 'ramp', 'scaleMode', 'colourLow', 'colourHigh', 'buckets', 'noData', 'reverse',
    'borderColour', 'borderStyle', 'borderWidth', 'outlineColour', 'outlineStyle', 'outlineWidth', 'background', 'canvas',
    'frameStyle', 'frameColour', 'showNames', 'showValues', 'showLegend', 'northArrow', 'northPos', 'northSize',
    'labelSize', 'decimals', 'numberStyle', 'prefix', 'suffix', 'legendTitle', 'legendPos', 'legendSize', 'labelColour', 'textColour'];

  var SCALE_HINTS = {
    quantile: 'Equal counts per colour. Good for skewed data like population or income.',
    equal: 'Equal value ranges. Good for evenly spread data like rates or shares.',
    continuous: 'Smooth gradient. Good for gradual change like rainfall or temperature.'
  };

  // Colour presets swapped in when the background flips between light and dark.
  var PRESETS = {
    light: { textColour: '#111111', labelColour: '#111111', borderColour: '#333333', outlineColour: '#333333', noData: '#e5e7eb', frameColour: '#111111' },
    dark: { textColour: '#f1f5f9', labelColour: '#f1f5f9', borderColour: '#94a3b8', outlineColour: '#cbd5e1', noData: '#334155', frameColour: '#f1f5f9' }
  };

  // Text assets: each one is added, styled and removed on its own.
  var ASSET_KINDS = {
    title: { label: 'Title', size: 34, weight: 700, pos: 'tl', colour: '#111111', dark: '#f1f5f9', text: 'Map title' },
    subtitle: { label: 'Subtitle', size: 18, weight: 400, pos: 'tl', colour: '#4b5563', dark: '#cbd5e1', text: 'Subtitle' },
    text: { label: 'Text', size: 14, weight: 400, pos: 'br', colour: '#111111', dark: '#f1f5f9', text: 'Your note' },
    source: { label: 'Source', size: 13, weight: 400, pos: 'bl', colour: '#6b7280', dark: '#94a3b8', text: 'Source: ' }
  };
  var BAND_POS = ['tl', 'tc', 'tr', 'bl', 'bc', 'br'];
  var CORNER_POS = ['tl', 'tr', 'bl', 'br'];
  var POS_LABEL = { tl: 'Top left', tc: 'Top centre', tr: 'Top right', bl: 'Bottom left', bc: 'Bottom centre', br: 'Bottom right' };

  // Boundary layers: which parent each one nests under decides the region filters and the outline meshes.
  var LAYERS = {
    states: { label: 'states', parent: null },
    districts: { label: 'districts', parent: 'state' },
    subdistricts: { label: 'sub-districts', parent: 'district' },
    blocks: { label: 'blocks', parent: 'district' },
    parliament: { label: 'parliamentary constituencies', parent: 'state' },
    assembly: { label: 'assembly constituencies', parent: 'district' }
  };
  var LEVEL_KEYS = Object.keys(LAYERS);
  function levelMap(init) { var m = {}; LEVEL_KEYS.forEach(function (k) { m[k] = typeof init === 'function' ? init() : init; }); return m; }
  function parentOf(p, level) { return (LAYERS[level || current.level].parent === 'district' ? p.district : p.state) || ''; }
  function hasDistrictParent(level) { return LAYERS[level || current.level].parent === 'district'; }
  // the district picker only means something for districts and for layers that nest inside districts
  function usesDistricts(level) { return level === 'districts' || hasDistrictParent(level); }
  var layers = {};                       // level -> { topo, object, features }
  var values = levelMap(function () { return {}; });            // level -> id -> value
  var valueHeaders = levelMap('');
  var region = { state: '', district: '' };
  var current = { level: 'districts', features: [], object: null, topo: null };
  var lastMatch = null;
  var pendingFixes = [];                 // rows the user can match by hand: { name, value, kind, cands, count }
  var assumed = [];                      // fuzzy matches accepted automatically: { name, f, value }, shown with an undo
  var userAliases = levelMap(function () { return {}; });       // level -> compact name -> feature id
  var labelSizeAuto = true;              // label size follows the level until the user edits it
  var autoSuffix = false;
  var offsets = {};                      // drag offsets per overlay key -> { dx, dy }
  var meshCache = {};
  var assets = [];
  var assetSeq = 1;
  var view = { k: 1, dx: 0, dy: 0 };     // map zoom and pan
  var TOUCH = window.matchMedia && matchMedia('(hover: none) and (pointer: coarse)').matches;
  var selectedKey = null;                // overlay selected on the canvas (asset-N, legend, north)
  var lastLayout = null;                 // { cx, cy } centre of the map area from the last render

  // ---------------------------------------------------------------------------
  //  Data loading
  // ---------------------------------------------------------------------------
  var loadsInFlight = 0;
  function loadLayer(level) {
    if (layers[level]) return Promise.resolve(layers[level]);
    ui.stage.classList.add('loading');
    loadsInFlight++; ui.stageLoading.hidden = false;
    return fetch(BASE + level + '.topo.json' + DATA_V)
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (topo) {
        var object = topo.objects[level];
        var fc = topojson.feature(topo, object);
        fc.features.forEach(function (f, i) { f.id = String(object.geometries[i].id); });
        layers[level] = { topo: topo, object: object, features: fc.features };
        return layers[level];
      })
      .finally(function () { ui.stage.classList.remove('loading'); if (--loadsInFlight <= 0) { loadsInFlight = 0; ui.stageLoading.hidden = true; } });
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
          if (hasDistrictParent(level) && String(p.dist_lgd) !== region.district) return;
        }
      }
      keep.push(f);
      keepGeoms.push(geoms[i]);
    });
    return { features: keep, object: { type: 'GeometryCollection', geometries: keepGeoms } };
  }

  var refreshSeq = 0;
  function refresh() {
    var level = ui.level.value;
    var seq = ++refreshSeq;
    return loadLayer(level).then(function (layer) {
      if (seq !== refreshSeq) return;                       // a newer choice superseded this one
      var sub = filterFeatures(layer, level);
      current = { level: level, features: sub.features, object: sub.object, topo: layer.topo };
      allOptsCache = null;
      if (labelSizeAuto) ui.labelSize.value = suggestedLabelSize(sub.features.length);
      pendingFixes = []; assumed = []; lastMatch = null; reportMatch();
      buildTable();
      render();
      save();
      // data typed for another level is matched again here, so switching levels keeps the map coloured
      if (!Object.keys(values[level]).length && ui.paste.value.trim() && !suppressRematch) applyRows(parseText(ui.paste.value), true);
    }).catch(function (err) {
      setStatus('Could not load boundaries: ' + err.message);
    });
  }
  var suppressRematch = false;

  function fillSelect(sel, opts, firstLabel) {
    sel.innerHTML = '<option value="">' + firstLabel + '</option>';
    opts.sort(function (a, b) { return a.name.localeCompare(b.name); }).forEach(function (o) {
      var el = document.createElement('option');
      el.value = o.lgd; el.textContent = o.name;
      sel.appendChild(el);
    });
  }

  function populateStates(layer) {
    fillSelect(ui.regionState, layer.features.map(function (f) { return { lgd: String(f.properties.lgd), name: f.properties.name }; }), 'India');
  }

  function populateDistricts() {
    if (!region.state) { fillSelect(ui.regionDistrict, [], 'All districts'); ui.districtField.hidden = true; return; }
    return loadLayer('districts').then(function (layer) {
      var opts = layer.features.filter(function (f) { return String(f.properties.state_lgd) === region.state; })
        .map(function (f) { return { lgd: String(f.properties.lgd), name: f.properties.name }; });
      fillSelect(ui.regionDistrict, opts, 'All districts');
      ui.regionDistrict.value = region.district;
      if (ui.regionDistrict.value !== region.district) { region.district = ''; }
      ui.districtField.hidden = !usesDistricts(ui.level.value);
    });
  }

  function regionLabel() {
    if (region.district) {
      var d = ui.regionDistrict.options[ui.regionDistrict.selectedIndex];
      if (d && d.value) return d.textContent;
    }
    if (region.state) {
      var s = ui.regionState.options[ui.regionState.selectedIndex];
      if (s && s.value) return s.textContent;
    }
    return 'India';
  }

  // ---------------------------------------------------------------------------
  //  Name matching
  // ---------------------------------------------------------------------------
  function suggestFeatures(name, n) {
    var k = compact(name);
    k = ALIASES[k] || k;
    var tk = tokenKey(name);
    return current.features.map(function (f) { return { f: f, s: Math.max(similarity(k, compact(f.properties.name)), similarity(tk, tokenKey(f.properties.name))) }; })
      .filter(function (x) { return x.s >= 0.45; })
      .sort(function (a, b) { return b.s - a.s; })
      .slice(0, n || 3).map(function (x) { return x.f; });
  }
  function buildIndex(feats) {
    var byName = {}, byCode = {}, byId = {}, byTokens = {};
    feats.forEach(function (f) {
      var p = f.properties;
      var k = compact(p.name);
      (byName[k] = byName[k] || []).push(f);
      var tk = tokenKey(p.name);
      (byTokens[tk] = byTokens[tk] || []).push(f);
      byCode[String(p.lgd)] = f;
      byId[f.id] = f;
      if (p.census) byCode[String(p.census).replace(/^0+/, '')] = f;
    });
    return { byName: byName, byCode: byCode, byId: byId, byTokens: byTokens, keys: Object.keys(byName), tokenKeys: Object.keys(byTokens) };
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

  // A "parent" hint is a state name, or a district name when sub-districts are drawn.
  function isParentName(v) {
    if (isStateName(v)) return true;
    if (!hasDistrictParent() || !v) return false;
    var k = compact(v);
    k = ALIASES[k] || k;
    return current.features.some(function (f) { return compact(f.properties.district || '') === k; });
  }

  function pickByParent(cands, hint) {
    if (!hint) return null;
    var h = compact(hint);
    h = ALIASES[h] || h;
    var hits = cands.filter(function (f) {
      return compact(f.properties.state || '') === h || compact(f.properties.district || '') === h;
    });
    return hits.length === 1 ? hits[0] : null;
  }

  var lastMatchKind = 'exact';           // 'exact' | 'learned' | 'alias' | 'fuzzy' for the most recent matchName()

  function matchName(raw, hint, idx) {
    var name = String(raw).trim();
    lastMatchKind = 'exact';
    if (!name) return null;
    if (digitsOnly(name)) return idx.byCode[name.replace(/^0+/, '')] || null;

    // "Bilaspur, Himachal Pradesh" or "Bilaspur (HP)": only split when the tail is a real parent name
    var m = name.match(/^(.*?)[\s]*[,(]\s*([^)]+)\)?\s*$/);
    if (m && !hint && isParentName(m[2])) { name = m[1]; hint = m[2]; }

    var k = compact(name);
    var learned = userAliases[current.level][k];
    if (learned === '') return null;                                   // the user rejected the guess for this name
    if (learned && idx.byId[learned]) { lastMatchKind = 'learned'; return idx.byId[learned]; }
    if (ALIASES[k]) { k = ALIASES[k]; lastMatchKind = 'alias'; }
    var cands = idx.byName[k];
    var tk = tokenKey(name);
    if (!cands && idx.byTokens[tk]) { cands = idx.byTokens[tk]; lastMatchKind = 'fuzzy'; }       // same words, different order
    if (!cands) {
      // one name starts with the other, but only when they are close in length (so "North" never swallows "North 24 Parganas")
      var pref = idx.keys.filter(function (key) {
        var shorter = Math.min(key.length, k.length), longer = Math.max(key.length, k.length);
        return (key.indexOf(k) === 0 || k.indexOf(key) === 0) && shorter >= 5 && shorter / longer >= 0.6;
      });
      if (pref.length === 1) { cands = idx.byName[pref[0]]; lastMatchKind = 'fuzzy'; }
    }
    if (!cands && k.length >= 5) {
      var tol = k.length > 8 ? 2 : 1;
      var close = idx.keys.filter(function (key) { return levenshtein(k, key) <= tol; });
      if (close.length === 1) { cands = idx.byName[close[0]]; lastMatchKind = 'fuzzy'; }
      if (!cands) {
        var closeT = idx.tokenKeys.filter(function (key) { return levenshtein(tk, key) <= tol; });
        if (closeT.length === 1) { cands = idx.byTokens[closeT[0]]; lastMatchKind = 'fuzzy'; }
      }
    }
    if (!cands) return null;
    if (cands.length === 1) return cands[0];
    return pickByParent(cands, hint) || { ambiguous: cands };
  }

  // ---------------------------------------------------------------------------
  //  Parsing pasted / uploaded data
  // ---------------------------------------------------------------------------
  // Do most of the names belong to a different level than the one selected?
  function detectLevel(rows, nameCol) {
    var names = rows.map(function (r) { return r[nameCol] || ''; }).filter(Boolean);
    if (names.length < 2) return null;
    var stateHits = names.filter(function (n) { return isStateName(n); }).length;
    var level = current.level;
    if (level !== 'states' && stateHits >= Math.max(2, names.length * 0.6)) return 'states';
    if (level === 'states' && stateHits <= names.length * 0.2 && layers.districts) {
      var idx = buildIndex(layers.districts.features);
      var districtHits = names.filter(function (n) { var k = compact(n); return !!(idx.byName[ALIASES[k] || k]); }).length;
      if (districtHits >= Math.max(2, names.length * 0.6)) return 'districts';
    }
    return null;
  }

  var lastRows = null;                   // the rows behind the current match, so a column pick can rerun them
  var valueColOverride = -1;
  var sheets = null;                     // [{ name, rows }] when a workbook has more than one usable sheet

  function showPickers(columns, valueCol, header) {
    ui.sheetField.hidden = !(sheets && sheets.length > 1);
    if (!ui.sheetField.hidden) {
      ui.sheetPick.innerHTML = sheets.map(function (sh, i) { return '<option value="' + i + '"' + (sh.active ? ' selected' : '') + '>' + escapeHtml(sh.name) + '</option>'; }).join('');
    }
    ui.colField.hidden = columns.length < 2;
    if (!ui.colField.hidden) {
      ui.colPick.innerHTML = columns.map(function (c) {
        var label = header && header[c] ? header[c] : 'Column ' + (c + 1);
        return '<option value="' + c + '"' + (c === valueCol ? ' selected' : '') + '>' + escapeHtml(label) + '</option>';
      }).join('');
    }
    ui.sourcePick.hidden = ui.sheetField.hidden && ui.colField.hidden;
  }
  ui.colPick.addEventListener('change', function () { valueColOverride = +ui.colPick.value; if (lastRows) applyRows(lastRows); });
  ui.sheetPick.addEventListener('change', function () {
    if (!sheets) return;
    sheets.forEach(function (sh, i) { sh.active = i === +ui.sheetPick.value; });
    valueColOverride = -1;
    var sh = sheets[+ui.sheetPick.value];
    ui.paste.value = sh.rows.map(function (r) { return r.join('\t'); }).join('\n');
    applyRows(sh.rows);
  });

  function applyRows(rows, fromRefresh) {
    lastRows = rows;
    rows = rows.map(function (r) {
      r = r.map(function (c) { return c == null ? '' : String(c).trim(); });
      while (r.length && r[r.length - 1] === '') r.pop();
      return r;
    }).filter(function (r) { return r.length; });
    if (!rows.length) return;

    var level = current.level;
    // title or blank rows above the real header (common in exported sheets)
    while (rows.length > 1 && rows[0].filter(function (c) { return c !== ''; }).length < 2) rows.shift();
    // column count: the widest row that at least two rows reach (a lone trailing note does not count)
    var byLen = {};
    rows.forEach(function (r) { byLen[r.length] = (byLen[r.length] || 0) + 1; });
    var ncol = d3.max(rows, function (r) { return r.length; });
    while (ncol > 2 && (byLen[ncol] || 0) < 2 && rows[0].length !== ncol) ncol--;
    var nameCol = 0, hintCol = -1, valueCol = ncol - 1;
    if (ncol < 2) { setStatus('Need at least two columns: name and value.'); return; }

    // the name column is the first one that mostly holds text (skips blank or row-number columns)
    function textShare(c) {
      var n = 0, t = 0;
      rows.forEach(function (r) { if (r[c] != null && r[c] !== '') { n++; if (isNaN(toNumber(r[c]))) t++; } });
      return n ? t / n : 0;
    }
    var textCols = [];
    for (var c = 0; c < valueCol; c++) if (textShare(c) >= 0.5) textCols.push(c);
    if (textCols.length === 1) nameCol = textCols[0];
    else if (textCols.length > 1 && textCols[0] > 0) nameCol = textCols[0];
    // the value column is the last mostly-numeric column after the name (so a trailing date or note column is skipped)
    var numericCols = [];
    for (var vc = ncol - 1; vc > nameCol; vc--) {
      var filled = rows.filter(function (r) { return r[vc] != null && r[vc] !== ''; });
      var numeric = filled.filter(function (r) { return !isNaN(toNumber(r[vc])) || isEmptyToken(r[vc]); });
      if (filled.length && numeric.length / filled.length >= 0.5) numericCols.unshift(vc);
    }
    if (numericCols.length) valueCol = numericCols[numericCols.length - 1];
    if (valueColOverride >= 0 && numericCols.indexOf(valueColOverride) !== -1) valueCol = valueColOverride;

    var idx = buildIndex(current.features);

    // names from another level: switch the level once, then match there
    if (!fromRefresh && !region.state) {
      var better = detectLevel(rows, nameCol);
      if (better && better !== current.level) {
        ui.level.value = better;
        suppressRematch = true;
        refresh().then(function () { suppressRematch = false; applyRows(rows, true); });
        return;
      }
    }

    // header detection: value cell not numeric while others are, or a first cell that reads like a column label
    var header = null;
    var first = rows[0];
    var numericRows = rows.filter(function (r) { return !isNaN(toNumber(r[valueCol])); }).length;
    var firstLooksLikeLabel = HEADER_WORDS.test(compact(first[0] || '')) || HEADER_WORDS.test(compact(first[1] || ''));
    var firstUnmatched = rows.length > 1 && !matchName(first[0], '', idx) && (ncol < 3 || !matchName(first[1], '', idx));
    var firstValueIsText = isNaN(toNumber(first[valueCol])) && !isEmptyToken(first[valueCol]);
    if ((numericRows >= 1 && firstValueIsText) || firstLooksLikeLabel || (firstUnmatched && firstValueIsText)) {
      header = first;
      rows = rows.slice(1);
    }
    // a template or any sheet with a code column matches by code, which is exact
    var codeCol = -1;
    if (header) header.forEach(function (h, c) { if (/^(lgdcode|lgd|code|regioncode)$/.test(compact(h || '')) && c !== valueCol) codeCol = c; });
    var headerValue = header ? (header[valueCol] || '') : '';
    valueHeaders[level] = /^(value|values|val|data|number|numbers|amount|count|figure)$/i.test(headerValue) ? '' : headerValue;
    // codes are not values: keep them out of the column choices
    var choosable = numericCols.filter(function (c) { return c !== codeCol && !(header && /^(lgdcode|lgd|code|regioncode|censuscode|census)$/.test(compact(header[c] || ''))); });
    if (choosable.indexOf(valueCol) === -1 && choosable.length) { valueCol = valueColOverride >= 0 && choosable.indexOf(valueColOverride) !== -1 ? valueColOverride : choosable[choosable.length - 1]; valueHeaders[level] = header && !/^(value|values|val|data|number|numbers|amount|count|figure)$/i.test(header[valueCol] || '') ? (header[valueCol] || '') : ''; }
    showPickers(choosable, valueCol, header);

    // with two or more text columns, work out which one holds the state (or district)
    var pair = textCols.length >= 2 ? textCols.slice(0, 2) : (ncol >= 3 ? [0, 1] : null);
    if (pair && level !== 'states') {
      var headerHint = header ? pair.filter(function (c) { return /^(state|ut|stateut|st|states|district|dist)$/.test(compact(header[c] || '')); }) : [];
      var otherOf = function (c) { return c === pair[0] ? pair[1] : pair[0]; };
      if (headerHint.length === 1 && !(header && HEADER_WORDS.test(compact(header[otherOf(headerHint[0])] || '')) && /^(district|dist)$/.test(compact(header[headerHint[0]])) && level === 'districts')) {
        hintCol = headerHint[0]; nameCol = otherOf(hintCol);
      } else {
        var hits = pair.map(function (c) { return rows.filter(function (r) { return isParentName(r[c]); }).length; });
        if (hits[0] || hits[1]) { hintCol = hits[0] >= hits[1] ? pair[0] : pair[1]; nameCol = otherOf(hintCol); }
      }
    }

    // a paste replaces the level's data
    var vals = values[level] = {};
    var matched = 0, empty = 0, unmatched = [], ambiguous = [];
    var percentCount = 0;
    pendingFixes = [];
    assumed = [];
    function parseValue(raw) { var n = toNumber(raw); return isNaN(n) ? raw : n; }
    function addFix(nm, raw, kind, cands) {
      var key = compact(nm);
      var existing = kind === 'ambiguous' ? null : pendingFixes.filter(function (fx) { return fx.key === key && fx.kind === kind; })[0];
      var value = isEmptyToken(raw) ? null : parseValue(raw);
      if (existing) { existing.count++; if (value != null) existing.value = value; return; }   // repeats fixed together
      pendingFixes.push({ name: nm, key: key, value: value, kind: kind, cands: cands, count: 1 });
    }
    rows.forEach(function (r) {
      var nm = r[nameCol] || '';
      if (!nm) return;
      var raw = r[valueCol];
      var f = null;
      if (codeCol >= 0 && digitsOnly(r[codeCol] || '')) { f = idx.byCode[String(r[codeCol]).replace(/^0+/, '')] || null; lastMatchKind = 'exact'; }
      if (!f) f = matchName(nm, hintCol >= 0 ? (r[hintCol] || '') : '', idx);
      if (!f) { unmatched.push(nm); addFix(nm, raw, 'unmatched', suggestFeatures(nm, 3)); return; }
      if (f.ambiguous) { ambiguous.push(nm); addFix(nm, raw, 'ambiguous', f.ambiguous); return; }
      if (isEmptyToken(raw)) { empty++; return; }
      if (/%\s*$/.test(raw)) percentCount++;
      vals[f.id] = parseValue(raw);
      matched++;
      if (lastMatchKind === 'fuzzy' && compact(nm) !== compact(f.properties.name) && !assumed.some(function (a) { return a.key === compact(nm); })) {
        assumed.push({ name: nm, key: compact(nm), f: f, value: vals[f.id] });
      }
    });
    var isPercent = percentCount && percentCount >= matched / 2;
    if (isPercent && !ui.suffix.value) { ui.suffix.value = '%'; autoSuffix = true; }
    else if (!isPercent && autoSuffix && ui.suffix.value === '%') { ui.suffix.value = ''; autoSuffix = false; }

    lastMatch = { matched: matched, empty: empty, unmatched: unmatched, ambiguous: ambiguous };
    reportMatch();
    buildTable();
    render();
    save();
  }

  function reportMatch() {
    if (!lastMatch) { ui.matchStatus.textContent = ''; ui.unmatched.innerHTML = ''; return; }
    var nUnmatched = pendingFixes.filter(function (fx) { return fx.kind === 'unmatched'; }).length;
    var nAmbiguous = pendingFixes.filter(function (fx) { return fx.kind === 'ambiguous'; }).length;
    var parts = ['<strong>' + lastMatch.matched + '</strong> matched' + (assumed.length ? ' (' + assumed.length + ' guessed)' : '')];
    if (lastMatch.empty) parts.push('<strong>' + lastMatch.empty + '</strong> without a value');
    if (nUnmatched) parts.push('<strong>' + nUnmatched + '</strong> not found');
    if (nAmbiguous) {
      parts.push('<strong>' + nAmbiguous + '</strong> ambiguous (add a ' + (hasDistrictParent() ? 'district' : 'state') + ' column)');
    }
    ui.matchStatus.innerHTML = parts.join(' · ');
    ui.matchStatus.classList.remove('notice');
    renderFixes();
  }

  function updateBadge() {
    var n = pendingFixes.length;
    ui.unmatchedBadge.hidden = !n;
    ui.unmatchedBadge.textContent = n + (n === 1 ? ' name to check' : ' names to check');
  }

  function renderLearned() {
    var m = userAliases[current.level];
    var keys = Object.keys(m);
    ui.learnedBox.hidden = !keys.length;
    if (!keys.length) { ui.learnedList.innerHTML = ''; return; }
    var byId = {};
    ((layers[current.level] && layers[current.level].features) || current.features).forEach(function (f) { byId[f.id] = f; });
    ui.learnedBox.querySelector('summary').textContent = 'Remembered matches · ' + keys.length;
    ui.learnedList.innerHTML = keys.map(function (k) {
      var f = byId[m[k]];
      var target = m[k] === '' ? 'not matched automatically' : (f ? f.properties.name : 'another region');
      return '<div class="learned-row"><span>' + escapeHtml(k) + ' → ' + escapeHtml(target) + '</span>' +
        '<button type="button" class="asset-del" data-forget="' + escapeHtml(k) + '" aria-label="Forget this match">Forget</button></div>';
    }).join('');
  }
  ui.learnedList.addEventListener('click', function (e) {
    var b = e.target.closest('[data-forget]');
    if (!b) return;
    delete userAliases[current.level][b.dataset.forget];
    renderLearned(); save();
  });

  function featureLabel(f) {
    var p = f.properties;
    var parent = current.level === 'states' ? '' : parentOf(p);
    return p.name + (parent && !region.state ? ' (' + parent + ')' : '');
  }

  function renderFixes() {
    updateBadge();
    renderLearned();
    if (!pendingFixes.length && !assumed.length) { ui.unmatched.innerHTML = ''; return; }
    var MAX_ROWS = 60;
    var assumedHtml = assumed.map(function (a, i) {
      return '<div class="fix-row assumed">' +
        '<span class="fix-name" title="' + escapeHtml(a.name) + '">' + escapeHtml(a.name) + ' → ' + escapeHtml(a.f.properties.name) + '</span>' +
        '<span class="fix-val">' + (a.value == null ? '' : escapeHtml(fmt(a.value))) + '</span>' +
        '<button type="button" class="btn-plain secondary fix-undo" data-undo="' + i + '">Undo</button></div>';
    }).join('');
    var shown = pendingFixes.slice(0, MAX_ROWS);
    ui.unmatched.innerHTML = assumedHtml + shown.map(function (fx, i) {
      var sugg = fx.cands.map(function (f) { return '<option value="' + f.id + '">' + escapeHtml(featureLabel(f)) + '</option>'; }).join('');
      return '<div class="fix-row">' +
        '<span class="fix-name" title="' + escapeHtml(fx.name) + '">' + escapeHtml(fx.name) + (fx.count > 1 ? ' <small>×' + fx.count + '</small>' : '') + '</span>' +
        '<span class="fix-val">' + (fx.value == null ? '' : escapeHtml(fmt(fx.value))) + '</span>' +
        '<select data-fix="' + i + '" data-kind="' + fx.kind + '" aria-label="Match ' + escapeHtml(fx.name) + '">' +
          '<option value="">' + (fx.kind === 'ambiguous' ? 'Which one?' : 'Match to…') + '</option>' +
          '<option value="__skip">Skip</option>' +
          (sugg ? '<optgroup label="' + (fx.kind === 'ambiguous' ? 'Candidates' : 'Suggestions') + '">' + sugg + '</optgroup>' : '') +
        '</select></div>';
    }).join('') + (pendingFixes.length > MAX_ROWS ? '<div class="hint">and ' + (pendingFixes.length - MAX_ROWS) + ' more</div>' : '');
  }

  // the full region list is long; add it to a picker only when it is opened
  var allOptsCache = null;
  ui.unmatched.addEventListener('focusin', function (e) {
    var sel = e.target.closest('select[data-fix]');
    if (!sel || sel.dataset.kind === 'ambiguous' || sel.dataset.full) return;
    if (!allOptsCache) {
      allOptsCache = current.features.slice().sort(function (a, b) { return a.properties.name.localeCompare(b.properties.name); })
        .map(function (f) { return '<option value="' + f.id + '">' + escapeHtml(featureLabel(f)) + '</option>'; }).join('');
    }
    sel.insertAdjacentHTML('beforeend', '<optgroup label="All regions">' + allOptsCache + '</optgroup>');
    sel.dataset.full = '1';
  });

  ui.unmatched.addEventListener('change', function (e) {
    var sel = e.target.closest('select[data-fix]');
    if (!sel || !sel.value) return;
    var fx = pendingFixes[+sel.dataset.fix];
    if (!fx) return;
    if (sel.value === '__skip') {                            // a total, footnote or stray row: drop it without remembering anything
      pendingFixes.splice(+sel.dataset.fix, 1);
      if (lastMatch) { var l = fx.kind === 'ambiguous' ? lastMatch.ambiguous : lastMatch.unmatched; var at0 = l.indexOf(fx.name); if (at0 !== -1) l.splice(at0, 1); }
      reportMatch(); save();
      return;
    }
    var f = current.features.filter(function (x) { return x.id === sel.value; })[0];
    if (!f) return;
    if (fx.value != null) values[current.level][f.id] = fx.value;
    userAliases[current.level][fx.key] = f.id;   // remembered for next time, including which of two same-named regions
    pendingFixes.splice(+sel.dataset.fix, 1);
    if (lastMatch) {
      lastMatch.matched += fx.value != null ? 1 : 0;
      if (fx.value == null) lastMatch.empty++;
      var list = fx.kind === 'ambiguous' ? lastMatch.ambiguous : lastMatch.unmatched;
      var at = list.indexOf(fx.name); if (at !== -1) list.splice(at, 1);
    }
    reportMatch(); buildTable(); render(); save();
  });

  // undo an assumed match: take the value back, refuse that guess next time, and offer the picker instead
  ui.unmatched.addEventListener('click', function (e) {
    var b = e.target.closest('[data-undo]');
    if (!b) return;
    var a = assumed.splice(+b.dataset.undo, 1)[0];
    if (!a) return;
    delete values[current.level][a.f.id];
    userAliases[current.level][a.key] = '';
    pendingFixes.push({ name: a.name, key: a.key, value: a.value, kind: 'unmatched', cands: suggestFeatures(a.name, 3), count: 1 });
    if (lastMatch) { lastMatch.matched--; lastMatch.unmatched.push(a.name); }
    reportMatch(); buildTable(); render(); save();
  });

  ui.unmatchedBadge.addEventListener('click', function () {
    var panel = ui.unmatched.closest('details'); if (panel) panel.open = true;
    ui.unmatched.scrollIntoView({ block: 'center', behavior: 'smooth' });
    ui.unmatched.classList.add('flash'); setTimeout(function () { ui.unmatched.classList.remove('flash'); }, 1200);
  });

  // region list for the current view, so people can use our names or codes in their sheet
  ui.regionList.addEventListener('click', function () {
    var rows = [['name', 'parent', 'lgd_code', 'value']];
    current.features.slice().sort(function (a, b) { return a.properties.name.localeCompare(b.properties.name); }).forEach(function (f) {
      var p = f.properties;
      var v = values[current.level][f.id];
      rows.push([csvSafe(p.name), csvSafe(current.level === 'states' ? '' : parentOf(p)), p.lgd, v == null ? '' : csvSafe(v)]);
    });
    download(new Blob(['\ufeff' + d3.csvFormatRows(rows)], { type: 'text/csv;charset=utf-8' }), (regionLabel() + ' ' + current.level).toLowerCase().replace(/[^a-z0-9]+/g, '-') + '-template.csv');
  });

  function setStatus(msg) { ui.matchStatus.textContent = msg; ui.matchStatus.classList.toggle('notice', !!msg); }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function readFile(file) {
    if (!file) return;
    var name = file.name.toLowerCase();
    var type = (file.type || '').toLowerCase();
    var isSheet = /\.(xlsx|xls|xlsm|ods)$/.test(name) || /spreadsheet|ms-excel|opendocument/.test(type);
    var isText = /\.(csv|tsv|txt)$/.test(name) || /^text\//.test(type) || type === 'application/csv';
    var isProject = /\.json$/.test(name) || type === 'application/json';
    if (isProject) { openProject(file); return; }
    if (!isSheet && !isText) { setStatus('Use a CSV, TSV, Excel or project file.'); return; }
    sheets = null; valueColOverride = -1;
    if (isSheet) {
      if (!window.XLSX) {
        setStatus('Loading spreadsheet support…');
        loadScript(XLSX_URL).then(function () { setStatus(''); readFile(file); }, function (err) { setStatus('Spreadsheet support could not be loaded (' + err.message + ').'); });
        return;
      }
      var fr = new FileReader();
      fr.onerror = function () { setStatus('Could not read ' + file.name + '.'); };
      fr.onload = function () {
        try {
          var wb = XLSX.read(new Uint8Array(fr.result), { type: 'array', cellDates: true });
          var usable = [];
          wb.SheetNames.forEach(function (sn) {
            // formatted text keeps percentages as "12%" and dates readable; plain numbers still parse
            var cand = XLSX.utils.sheet_to_json(wb.Sheets[sn], { header: 1, raw: false, defval: '' });
            if (cand.some(function (r) { return r.filter(function (c) { return c !== ''; }).length >= 2; })) usable.push({ name: sn, rows: cand, active: !usable.length });
          });
          if (!usable.length) { setStatus('No sheet with a name and value column in ' + file.name + '.'); return; }
          sheets = usable.length > 1 ? usable : null;
          var rows = usable[0].rows;
          ui.paste.value = rows.map(function (r) { return r.join('\t'); }).join('\n');
          applyRows(rows);
        } catch (err) { setStatus('Could not read ' + file.name + ': ' + err.message); }
      };
      fr.readAsArrayBuffer(file);
    } else {
      var tr = new FileReader();
      tr.onerror = function () { setStatus('Could not read ' + file.name + '.'); };
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
        (showParent ? ' <small>' + escapeHtml(parentOf(p, level)) + '</small>' : '') +
        '</td><td><input type="text" data-id="' + f.id + '" aria-label="Value for ' + escapeHtml(p.name) + '" value="' + (v == null ? '' : escapeHtml(v)) + '"></td></tr>';
    });
    ui.valueTable.innerHTML = html || '<tr><td colspan="2"><small>No regions</small></td></tr>';
    syncUi();
    var withData = current.features.filter(function (f) { return vals[f.id] != null && vals[f.id] !== ''; }).length;
    $('valuesSummary').textContent = 'Values · ' + withData + ' of ' + current.features.length;
  }

  // Label size that suits the number of regions drawn, used until the user sets one.
  function suggestedLabelSize(n) { return n <= 40 ? 14 : n <= 120 ? 12 : n <= 800 ? 9 : 7; }

  ui.valueTable.addEventListener('change', function (e) {
    var input = e.target.closest('input[data-id]');
    if (!input) return;
    var vals = values[current.level];
    var raw = input.value.trim();
    if (isEmptyToken(raw)) delete vals[input.dataset.id];
    else { var n = toNumber(raw); vals[input.dataset.id] = isNaN(n) ? raw : n; }
    render();
    save();
  });

  // ---------------------------------------------------------------------------
  //  Text assets
  // ---------------------------------------------------------------------------
  function addAsset(kind, text) {
    var d = ASSET_KINDS[kind];
    var dark = ui.background.value === '#0f172a';
    var a = { id: assetSeq++, kind: kind, text: text != null ? text : d.text, size: d.size, font: 'sans', weight: d.weight, italic: false,
      colour: dark ? d.dark : d.colour, pos: d.pos };
    assets.push(a);
    renderAssetList();
    render();
    save();
    var input = ui.assetList.querySelector('[data-asset="' + a.id + '"] input[data-prop="text"]');
    if (input && !TOUCH) { input.focus(); input.select(); }
    return a;
  }

  function removeAsset(id) {
    assets = assets.filter(function (a) { return a.id !== id; });
    delete offsets['asset-' + id];
    renderAssetList();
    render();
    save();
  }

  function assetById(id) { return assets.filter(function (a) { return a.id === id; })[0]; }

  function renderAssetList() {
    var html = '';
    assets.forEach(function (a) {
      var kind = ASSET_KINDS[a.kind];
      var positions = a.kind === 'text' ? CORNER_POS : BAND_POS;
      var idp = 'asset' + a.id + '-';
      html += '<div class="asset" data-asset="' + a.id + '">' +
        '<div class="asset-head"><span>' + kind.label + '</span><button class="asset-del" type="button" data-del="' + a.id + '" aria-label="Remove ' + kind.label.toLowerCase() + '">Remove</button></div>' +
        '<input type="text" data-prop="text" aria-label="' + kind.label + ' text" value="' + escapeHtml(a.text) + '" placeholder="' + escapeHtml(kind.text) + '">' +
        '<div class="row row-3">' +
          '<div class="field"><label for="' + idp + 'size">Size</label><input id="' + idp + 'size" type="number" data-prop="size" min="6" max="160" value="' + a.size + '"></div>' +
          '<div class="field"><label for="' + idp + 'font">Font</label><select id="' + idp + 'font" data-prop="font">' +
            Object.keys(FONTS).map(function (k) { return '<option value="' + k + '"' + (a.font === k ? ' selected' : '') + '>' + FONTS[k].label + '</option>'; }).join('') +
          '</select></div>' +
          '<div class="field"><label for="' + idp + 'colour">Colour</label><input id="' + idp + 'colour" type="color" data-prop="colour" value="' + escapeHtml(a.colour) + '"></div>' +
        '</div>' +
        '<div class="row">' +
          '<div class="field"><label for="' + idp + 'pos">Position</label><select id="' + idp + 'pos" data-prop="pos">' +
            positions.map(function (p) { return '<option value="' + p + '"' + (a.pos === p ? ' selected' : '') + '>' + POS_LABEL[p] + '</option>'; }).join('') +
          '</select></div>' +
          '<div class="field"><span class="field-label">Style</span><div class="checks">' +
            '<label class="check"><input type="checkbox" data-prop="bold"' + (a.weight >= 600 ? ' checked' : '') + '> Bold</label>' +
            '<label class="check"><input type="checkbox" data-prop="italic"' + (a.italic ? ' checked' : '') + '> Italic</label>' +
          '</div></div>' +
        '</div>' +
      '</div>';
    });
    ui.assetList.innerHTML = html;
  }

  function assetFromEvent(e) {
    var box = e.target.closest('[data-asset]');
    if (!box) return null;
    return assetById(+box.dataset.asset);
  }

  function updateAssetProp(a, el, commit) {
    var prop = el.dataset.prop;
    if (prop === 'text') a.text = el.value;
    else if (prop === 'size') { a.size = Math.max(6, Math.min(160, +el.value || a.size)); if (commit && +el.value !== a.size) el.value = a.size; }
    else if (prop === 'font') a.font = el.value;
    else if (prop === 'colour') a.colour = el.value;
    else if (prop === 'pos') { a.pos = el.value; delete offsets['asset-' + a.id]; }
    else if (prop === 'bold') a.weight = el.checked ? 700 : 400;
    else if (prop === 'italic') a.italic = el.checked;
  }

  ui.assetList.addEventListener('input', function (e) {
    var a = assetFromEvent(e);
    if (!a || !e.target.dataset.prop) return;
    updateAssetProp(a, e.target);
    renderSoon();
  });
  ui.assetList.addEventListener('change', function (e) {
    var a = assetFromEvent(e);
    if (!a || !e.target.dataset.prop) return;
    updateAssetProp(a, e.target, true);
    clearTimeout(renderTimer);
    render(); save();
  });
  ui.assetList.addEventListener('click', function (e) {
    var del = e.target.closest('[data-del]');
    if (del) removeAsset(+del.dataset.del);
  });
  document.querySelectorAll('[data-add]').forEach(function (btn) {
    btn.addEventListener('click', function () { addAsset(btn.dataset.add); });
  });

  // ---------------------------------------------------------------------------
  //  Number formatting
  // ---------------------------------------------------------------------------
  var autoDecimals = 0;

  function decimals() {
    var v = ui.decimals.value;
    return v === '' ? autoDecimals : Math.max(0, Math.min(6, +v || 0));
  }

  function fmt(v) {
    if (v == null || v === '') return '';
    if (typeof v !== 'number') return String(v);
    return (ui.prefix.value || '') + fmtNumber(v, decimals()) + (ui.suffix.value || '');
  }

  // ---------------------------------------------------------------------------
  //  Colour scale
  // ---------------------------------------------------------------------------

  function interpolator() {
    var name = ui.ramp.value;
    var base;
    if (name === 'custom') base = d3.interpolateLab(ui.colourLow.value, ui.colourHigh.value);
    else {
      var fn = d3['interpolate' + name];
      base = CLAMPED[name] ? function (t) { return fn(0.15 + 0.8 * t); } : fn;
    }
    return ui.reverse.checked ? function (t) { return base(1 - t); } : base;
  }

  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  function buildScale(vals) {
    var entries = current.features.map(function (f) { return vals[f.id]; }).filter(function (v) { return v != null && v !== ''; });
    if (!entries.length) return null;
    var nums = entries.filter(isNum);
    var interp = interpolator();
    var ramp = ui.ramp.value;

    // --- categorical: text wins the majority ---
    if (nums.length < entries.length / 2) {
      var counts = {}, order = [];
      entries.forEach(function (v) { var k = String(v); if (!(k in counts)) { counts[k] = 0; order.push(k); } counts[k]++; });
      var cats = order.slice();
      var other = null;
      if (cats.length > 10) {
        cats = order.slice().sort(function (a, b) { return counts[b] - counts[a]; }).slice(0, 9);
        cats = order.filter(function (k) { return cats.indexOf(k) !== -1; });
        other = 'Other';
      }
      var colours;
      if (ramp === 'custom' || ramp === 'Greys') colours = d3.quantize(interp, Math.max(cats.length + (other ? 1 : 0), 2));
      else { colours = QUALITATIVE.slice(); if (ui.reverse.checked) colours.reverse(); }
      var lookup = {};
      cats.forEach(function (c, i) { lookup[c] = colours[i % colours.length]; });
      var otherColour = other ? (ramp === 'custom' || ramp === 'Greys' ? colours[cats.length] : '#9ca3af') : null;
      return {
        type: 'categorical',
        has: function (v) { return v != null && v !== ''; },
        scale: function (v) { var k = String(v); return k in lookup ? lookup[k] : otherColour; },
        items: cats.map(function (c) { return { label: c, colour: lookup[c] }; }).concat(other ? [{ label: other, colour: otherColour }] : [])
      };
    }

    // --- numeric ---
    var uniq = Array.from(new Set(nums)).sort(d3.ascending);
    var ext = [uniq[0], uniq[uniq.length - 1]];
    var mode = ui.scaleMode.value;
    var diverging = DIVERGING[ramp] && ext[0] < 0 && ext[1] > 0;

    if (uniq.length === 1) {
      autoDecimals = computeAutoDecimals(nums);
      var one = interp(0.75);
      return { type: 'buckets', has: isNum, scale: function (v) { return isNum(v) ? one : null; }, items: [{ label: fmt(uniq[0]), colour: one }], single: true };
    }

    if (mode === 'continuous') {
      autoDecimals = computeAutoDecimals(nums, ext);
      var seq = diverging ? d3.scaleDiverging(interp).domain([ext[0], 0, ext[1]]) : d3.scaleSequential(interp).domain(ext);
      return { type: 'continuous', has: isNum, scale: function (v) { return isNum(v) ? seq(v) : null; }, extent: ext, interp: interp, mid: diverging ? 0 : null };
    }

    var k = Math.min(9, Math.max(2, +ui.buckets.value || 5), uniq.length);
    if (diverging && mode === 'equal' && k % 2 === 0 && uniq.length > 2) k = k < 9 ? k + 1 : k - 1;
    var thresholds;
    if (mode === 'quantile') {
      var sorted = nums.slice().sort(d3.ascending);
      thresholds = d3.range(1, k).map(function (i) { return d3.quantileSorted(sorted, i / k); });
    } else {
      var lo = diverging ? -Math.max(-ext[0], ext[1]) : ext[0];
      var hi = diverging ? Math.max(-ext[0], ext[1]) : ext[1];
      var step = (hi - lo) / k;
      thresholds = d3.range(1, k).map(function (i) { return lo + step * i; });
    }
    var integers = nums.every(function (v) { return Number.isInteger(v); });
    var symmetric = diverging && mode === 'equal';
    var labLo = symmetric ? -Math.max(-ext[0], ext[1]) : ext[0];
    var labHi = symmetric ? Math.max(-ext[0], ext[1]) : ext[1];
    function tidy(ts) {
      if (integers) ts = ts.map(Math.ceil);      // whole-number data gets whole-number breaks
      return Array.from(new Set(ts)).filter(function (t) { return t > labLo && t <= labHi; }).sort(d3.ascending);
    }
    thresholds = tidy(thresholds);
    if (mode === 'quantile' && thresholds.length < k - 1) {
      // heavy ties (many zeros): spread the classes over the distinct values instead
      thresholds = tidy(d3.range(1, k).map(function (i) { return d3.quantileSorted(uniq, i / k); }));
    }
    var n = thresholds.length + 1;
    var colours = d3.quantize(interp, Math.max(n, 2)).slice(0, n);
    if (n === 1) colours = [interp(0.75)];
    var sc = d3.scaleThreshold().domain(thresholds).range(colours);
    autoDecimals = computeAutoDecimals(nums, [ext[0]].concat(thresholds, [ext[1]]));

    var items = colours.map(function (c, i) {
      var lo2 = i === 0 ? labLo : thresholds[i - 1];
      var hi2 = i === n - 1 ? labHi : thresholds[i];
      var label;
      if (n === 1 || i === n - 1) label = lo2 === hi2 ? fmt(lo2) : fmt(lo2) + ' – ' + fmt(hi2);
      else if (integers) label = hi2 - 1 <= lo2 ? fmt(lo2) : fmt(lo2) + ' – ' + fmt(hi2 - 1);
      else label = fmt(lo2) + ' – <' + fmt(hi2);
      return { label: label, colour: c };
    });
    return { type: 'buckets', has: isNum, scale: function (v) { return isNum(v) ? sc(v) : null; }, items: items };
  }

  // ---------------------------------------------------------------------------
  //  Render
  // ---------------------------------------------------------------------------
  var svgNode = null;

  function intersects(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }

  // base: where the element sits now. anchor: the position its drag offset is measured from
  // (the preferred corner), so a dragged element never jumps when the map re-renders.
  function makeDraggable(sel, key, base, anchor) {
    anchor = anchor || base;
    var off = offsets[key] ? offsets[key] : { dx: base.x - anchor.x, dy: base.y - anchor.y, band: anchor.band || null };
    function apply() {
      sel.attr('transform', 'translate(' + (anchor.x + off.dx) + ',' + (anchor.y + off.dy) + ')');
      if (selectedKey === key) showSelection();          // outline and remove button travel with the element
    }
    apply();
    sel.attr('class', 'drag').attr('data-key', key).attr('tabindex', 0).attr('role', 'button');
    sel.on('click', function (e) { e.stopPropagation(); select(key); });
    sel.on('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(key); } });
    var pending = { dx: 0, dy: 0 }, startPt = null, moving = false;
    function screenPt(e) { var se = e.sourceEvent; var t = se && se.touches && se.touches[0]; return t ? [t.clientX, t.clientY] : [se ? se.clientX : 0, se ? se.clientY : 0]; }
    sel.call(d3.drag()
      .clickDistance(6)
      .on('start', function (e) { pending = { dx: 0, dy: 0 }; startPt = screenPt(e); moving = false; if (selectedKey && selectedKey !== key) deselect(); })
      .on('drag', function (e) {
        pending.dx += e.dx; pending.dy += e.dy;      // d3 reports deltas in canvas units already
        if (!moving) {
          var pt = screenPt(e), ddx = pt[0] - startPt[0], ddy = pt[1] - startPt[1];
          if (ddx * ddx + ddy * ddy < 36) return;       // under 6 screen px is a wobbly tap, not a drag
          moving = true;
        }
        offsets[key] = off;
        off.dx += pending.dx; off.dy += pending.dy;
        pending = { dx: 0, dy: 0 };
        apply();
      })
      .on('end', function () { if (moving) save(); }));
  }

  function cachedMesh(key, object, filter) {
    var k = current.level + '|' + region.state + '|' + region.district + '|' + key + '|' + object.geometries.length;
    if (!meshCache[k]) {
      if (Object.keys(meshCache).length > 40) meshCache = {};
      meshCache[k] = topojson.mesh(current.topo, object, filter);
    }
    return meshCache[k];
  }

  var BAND_ORDER = { title: 0, subtitle: 1, text: 2, source: 3 };

  function render() {
    try { renderInner(); }
    catch (err) {
      ui.stage.innerHTML = '';
      var box = document.createElement('div');
      box.className = 'stage-error';
      box.innerHTML = '<div>Something went wrong while drawing the map.</div>' +
        '<button type="button" class="btn-plain" id="resetSaved">Reset saved settings and reload</button>';
      ui.stage.appendChild(box);
      box.querySelector('#resetSaved').addEventListener('click', function () { try { localStorage.removeItem(STORE_KEY); } catch (e) { /* ignore */ } location.reload(); });
      if (window.console && console.error) console.error(err);
    }
  }

  function renderInner() {
    ui.tip.style.display = 'none';
    var size = ui.canvas.value.split('x').map(Number);
    var W = size[0] || 1000, H = size[1] || 1000;
    var pad = Math.round(W * 0.03);
    var textColour = ui.textColour.value;
    var bg = ui.background.value;
    var vals = values[current.level];
    var colour = buildScale(vals);
    var noData = ui.noData.value;
    var has = colour ? colour.has : function () { return false; };

    ui.stage.innerHTML = '';
    var svg = d3.select(ui.stage).append('svg')
      .attr('xmlns', 'http://www.w3.org/2000/svg')
      .attr('viewBox', '0 0 ' + W + ' ' + H)
      .attr('width', W).attr('height', H)
      .attr('font-family', FONTS.sans.stack);
    svgNode = svg.node();

    var defs = svg.append('defs');
    defs.append('pattern').attr('id', 'hatch').attr('width', 6).attr('height', 6).attr('patternUnits', 'userSpaceOnUse')
      .attr('patternTransform', 'rotate(45)')
      .append('line').attr('x1', 0).attr('y1', 0).attr('x2', 0).attr('y2', 6).attr('stroke', '#9ca3af').attr('stroke-width', 1);
    defs.append('clipPath').attr('id', 'canvasClip').append('rect').attr('width', W).attr('height', H);

    if (bg !== 'transparent') svg.append('rect').attr('width', W).attr('height', H).attr('fill', bg);

    var mapG = svg.append('g').attr('clip-path', 'url(#canvasClip)');   // map layers
    var overG = svg.append('g');                                          // overlays, always above the map

    // --- text bands: titles, subtitles and sources stack at the top or bottom edge ---
    var bandAssets = assets.filter(function (a) { return a.kind !== 'text' && a.text.trim(); });
    var topAssets = bandAssets.filter(function (a) { return a.pos[0] === 't'; }).sort(function (a, b) { return BAND_ORDER[a.kind] - BAND_ORDER[b.kind]; });
    var bottomAssets = bandAssets.filter(function (a) { return a.pos[0] === 'b'; }).sort(function (a, b) { return BAND_ORDER[a.kind] - BAND_ORDER[b.kind]; });
    var lineH = 1.25;
    function assetLines(a, maxWidth) { return wrapText(a.text, a.size, a.font, a.weight, maxWidth); }
    function assetHeight(a) { return assetLines(a, W - 2 * pad).length * a.size * lineH + a.size * 0.1; }
    function textNode(g, a, x, firstBaseline, anchor, maxWidth) {
      var t = g.append('text').attr('x', x).attr('y', firstBaseline).attr('text-anchor', anchor)
        .attr('font-family', (FONTS[a.font] || FONTS.sans).stack).attr('font-size', a.size).attr('font-weight', a.weight)
        .attr('font-style', a.italic ? 'italic' : null).attr('fill', a.colour);
      assetLines(a, maxWidth).forEach(function (l, i) { t.append('tspan').attr('x', x).attr('dy', i ? a.size * lineH : 0).text(l); });
      return t;
    }
    function drawTextAsset(a, top) {
      var anchor = a.pos[1] === 'l' ? 'start' : a.pos[1] === 'c' ? 'middle' : 'end';
      var x = anchor === 'start' ? pad : anchor === 'middle' ? W / 2 : W - pad;
      var g = overG.append('g');
      textNode(g, a, x, top + a.size, anchor, W - 2 * pad);
      return g;
    }
    var minMapHeight = Math.round(H * 0.3);
    var topH = d3.sum(topAssets, assetHeight) + (topAssets.length ? pad * 0.5 : 0);
    var bottomH = d3.sum(bottomAssets, assetHeight) + (bottomAssets.length ? pad * 0.5 : 0);
    var y = pad;
    topAssets.forEach(function (a) {
      var g = drawTextAsset(a, y);
      makeDraggable(g, 'asset-' + a.id, { x: 0, y: 0 });
      y += assetHeight(a);
    });
    var mapTop = pad + topH;
    var mapBottom = H - pad - bottomH;
    if (mapBottom - mapTop < minMapHeight) {   // too much text for the canvas: keep a usable map and let text overlap
      var mid = (mapTop + mapBottom) / 2;
      mapTop = Math.min(H - pad - minMapHeight, Math.max(pad, Math.round(mid - minMapHeight / 2)));
      mapBottom = mapTop + minMapHeight;
    }
    y = H - pad - bottomH + (bottomAssets.length ? pad * 0.5 : 0);
    bottomAssets.forEach(function (a) {
      var g = drawTextAsset(a, y);
      makeDraggable(g, 'asset-' + a.id, { x: 0, y: 0 });
      y += assetHeight(a);
    });

    // free text notes are placed like the legend, in a corner clear of the map
    var noteAssets = assets.filter(function (a) { return a.kind === 'text' && a.text.trim(); });
    var noteGroups = noteAssets.map(function (a) {
      var g = overG.append('g');
      textNode(g, a, 0, a.size, 'start', Math.min(W * 0.4, W - 2 * pad));
      return { asset: a, sel: g };
    });

    if (!current.features.length) {
      var stack = { tl: 0, tr: 0, bl: 0, br: 0 };
      noteGroups.forEach(function (n) {
        var bb = n.sel.node().getBBox();
        var c = n.asset.pos;
        var x = c[1] === 'l' ? pad : W - pad - bb.width;
        var yy = c[0] === 't' ? mapTop + stack[c] : mapBottom - bb.height - stack[c];
        stack[c] += bb.height + pad * 0.3;
        makeDraggable(n.sel, 'asset-' + n.asset.id, { x: x - bb.x, y: yy - bb.y });
      });
      drawFrame(svg, W, H, pad); return;
    }

    // --- which features are drawn: with "Hidden" no-data, only the ones with data ---
    var hideEmpty = noData === 'none' && colour;
    var drawFeats = current.features, drawObj = current.object, meshKey = 'all';
    if (hideEmpty) {
      var keepIds = {};
      current.features.forEach(function (f) { if (has(vals[f.id])) keepIds[f.id] = true; });
      drawFeats = current.features.filter(function (f) { return keepIds[f.id]; });
      drawObj = { type: 'GeometryCollection', geometries: current.object.geometries.filter(function (g) { return keepIds[String(g.id)]; }) };
      meshKey = 'vis' + Object.keys(keepIds).sort().join(',');
      if (!drawFeats.length) { drawFeats = current.features; drawObj = current.object; meshKey = 'all'; hideEmpty = false; }
    }

    // --- projection, with the user's zoom and pan applied around the map area's centre ---
    var fc = { type: 'FeatureCollection', features: drawFeats };
    var projection = d3.geoMercator();
    var path = d3.geoPath(projection);
    function fit() {
      projection.fitExtent([[pad, mapTop], [W - pad, mapBottom]], fc);
      if (view.k !== 1 || view.dx || view.dy) {
        var t = projection.translate(), cx = W / 2, cy = (mapTop + mapBottom) / 2;
        projection.scale(projection.scale() * view.k)
          .translate([cx + (t[0] - cx) * view.k + view.dx, cy + (t[1] - cy) * view.k + view.dy]);
      }
    }
    fit();
    lastLayout = { cx: W / 2, cy: (mapTop + mapBottom) / 2 };
    var boundsCache = null;
    function featureBoxes() {
      if (!boundsCache) {
        boundsCache = drawFeats.map(function (f) {
          var b = path.bounds(f);
          return { x: b[0][0], y: b[0][1], w: b[1][0] - b[0][0], h: b[1][1] - b[0][1] };
        });
      }
      return boundsCache;
    }

    // --- overlay placement: the chosen corner, else the other corner on the same edge, else a band ---
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
      return featureBoxes().some(function (b) { return intersects(b, box); });
    }
    function place(key, sel, pref) {
      var bb = sel.node().getBBox();
      var w = bb.width, h = bb.height;
      var origin = { x: -bb.x, y: -bb.y };
      var prefBox = cornerBox(pref, w, h);
      var box, bandUsed = null;
      function reserveBand() {
        var band = h + pad * 0.5;
        if (mapBottom - mapTop - band < minMapHeight) return null;
        if (pref[0] === 'b') { mapBottom -= band; fit(); boundsCache = null; return { x: prefBox.x, y: mapBottom + pad * 0.5, w: w, h: h }; }
        mapTop += band; fit(); boundsCache = null; return { x: prefBox.x, y: mapTop - band, w: w, h: h };
      }
      if (offsets[key]) {
        if (offsets[key].band) reserveBand();   // keep the room that was made for it before it was dragged
        box = { x: prefBox.x + offsets[key].dx, y: prefBox.y + offsets[key].dy, w: w, h: h };
      } else {
        var sameEdge = pref[0] + (pref[1] === 'l' ? 'r' : 'l');
        [pref, sameEdge].forEach(function (c) {
          if (box) return;
          var cand = cornerBox(c, w, h);
          if (!hits(cand)) box = cand;
        });
        if (!box) {
          var savedTop = mapTop, savedBottom = mapBottom;
          var tries = 0;
          while (!box && tries < 3) {
            var cand = reserveBand();
            if (!cand) break;
            var other = { x: cornerBox(sameEdge, w, h).x, y: cand.y, w: w, h: h };
            if (!occupied.some(function (o) { return intersects(o, cand); })) box = cand;
            else if (!occupied.some(function (o) { return intersects(o, other); })) box = other;
            tries++;
          }
          if (box) bandUsed = pref[0];
          else { mapTop = savedTop; mapBottom = savedBottom; fit(); boundsCache = null; box = prefBox; }   // no room: chosen corner, user can drag
        }
      }
      occupied.push(box);
      makeDraggable(sel, key, { x: box.x + origin.x, y: box.y + origin.y }, { x: prefBox.x + origin.x, y: prefBox.y + origin.y, band: bandUsed });
    }

    var arrow = ui.northArrow.checked ? drawNorthArrow(overG, textColour) : null;
    var showLegend = ui.showLegend.checked && colour && drawFeats.length > 1;
    var legend = showLegend ? drawLegend(overG, colour, textColour, vals) : null;
    if (arrow) place('north', arrow, ui.northPos.value);
    if (legend) place('legend', legend, ui.legendPos.value);
    noteGroups.forEach(function (n) { place('asset-' + n.asset.id, n.sel, n.asset.pos); });

    // --- map ---
    var levelFactor = drawFeats.length > 3000 ? 0.25 : drawFeats.length > 1000 ? 0.5 : 1;   // dense layers get hairline inner borders
    var bw = ui.borderStyle.value === 'none' ? 0 : +ui.borderWidth.value * levelFactor;
    var ow = ui.outlineStyle.value === 'none' ? 0 : +ui.outlineWidth.value;
    var bc = ui.borderColour.value, oc = ui.outlineColour.value;
    function dash(style, w) {
      if (style === 'dashed') return (w * 4) + ' ' + (w * 3);
      if (style === 'dotted') return '0.1 ' + (w * 2);
      return null;
    }
    var borderDash = dash(ui.borderStyle.value, Math.max(bw, 0.5));
    var outlineDash = dash(ui.outlineStyle.value, Math.max(ow, 0.5));

    var layer = mapG.append('g').attr('class', 'map-layer');
    layer.selectAll('path').data(drawFeats).enter().append('path')
      .attr('class', 'region')
      .attr('d', path)
      .attr('data-id', function (d) { return d.id; })
      .attr('fill', function (d) {
        var v = vals[d.id];
        var c = colour && has(v) ? colour.scale(v) : null;
        if (c) return c;
        if (noData === 'hatch') return 'url(#hatch)';
        if (noData === 'none') return 'none';
        return noData;
      })
      .attr('stroke', bc).attr('stroke-width', bw).attr('stroke-linejoin', 'round')
      .attr('stroke-dasharray', borderDash).attr('stroke-linecap', ui.borderStyle.value === 'dotted' ? 'round' : null)
      .on('pointermove pointerdown', function (e, d) {
        var p = d.properties;
        var label = p.name + (current.level !== 'states' && parentOf(p) ? ', ' + parentOf(p) : '');
        var v = vals[d.id];
        ui.tip.textContent = label + ' · ' + (has(v) ? fmt(v) : (v == null || v === '' ? 'no data' : String(v)));
        ui.tip.style.display = 'block';
        ui.tip.style.left = e.clientX + 'px'; ui.tip.style.top = (e.pointerType === 'touch' ? e.clientY - 36 : e.clientY) + 'px';
      })
      .on('pointerleave pointercancel', function (e) { if (e.pointerType !== 'touch') ui.tip.style.display = 'none'; });

    // --- boundary meshes ---
    function outline(key, filter, width) {
      if (!width) return;
      layer.append('path').attr('d', path(cachedMesh(meshKey + '|' + key, drawObj, filter)))
        .attr('fill', 'none').attr('stroke', oc).attr('stroke-width', width).attr('stroke-linejoin', 'round')
        .attr('stroke-dasharray', outlineDash).attr('stroke-linecap', ui.outlineStyle.value === 'dotted' ? 'round' : null);
    }
    if (hasDistrictParent() && !region.district) {
      outline('district', function (a, b) { return a !== b && a.properties.dist_lgd !== b.properties.dist_lgd; }, ow * 0.5);
    }
    if (current.level !== 'states' && !region.state) {
      outline('state', function (a, b) { return a !== b && a.properties.state_lgd !== b.properties.state_lgd; }, ow * 0.8);
    }
    outline('outer', function (a, b) { return a === b; }, ow);

    // --- labels: when the size is automatic, step it down until most labels fit ---
    if (ui.showNames.checked || ui.showValues.checked) {
      var boxes = featureBoxes();
      var halo = bg === 'transparent' ? '#ffffff' : bg;
      var ls = +ui.labelSize.value;
      var wanted = drawFeats.filter(function (d) { return ui.showNames.checked || has(vals[d.id]); }).length;
      for (var attempt = 0; attempt < 4; attempt++) {
        var lg = layer.append('g').attr('font-size', ls).attr('fill', ui.labelColour.value).attr('text-anchor', 'middle')
          .attr('paint-order', 'stroke').attr('stroke', halo).attr('stroke-width', ls * 0.25).attr('stroke-linejoin', 'round');
        var placedCount = placeLabels(lg, ls);
        if (!labelSizeAuto || placedCount >= wanted * 0.8 || ls <= 7) break;
        lg.remove(); ls = Math.max(7, ls - 1);
      }
      if (labelSizeAuto && String(ls) !== ui.labelSize.value) ui.labelSize.value = ls;
    }

    function placeLabels(lg, ls) {
      var count = 0;
      var grid = {}, cell = Math.max(20, ls * 6);
      function cellsOf(b) {
        var out = [];
        for (var gx = Math.floor(b.x / cell); gx <= Math.floor((b.x + b.w) / cell); gx++)
          for (var gy = Math.floor(b.y / cell); gy <= Math.floor((b.y + b.h) / cell); gy++) out.push(gx + ',' + gy);
        return out;
      }
      var placed = {
        hit: function (b) {
          return cellsOf(b).some(function (c) { return (grid[c] || []).some(function (o) { return intersects(o, b); }); });
        },
        push: function (b) { cellsOf(b).forEach(function (c) { (grid[c] = grid[c] || []).push(b); }); }
      };
      drawFeats.forEach(function (d, i) {
        var v = vals[d.id];
        var lines = [];
        if (ui.showNames.checked) lines.push(d.properties.name);
        if (ui.showValues.checked && has(v)) lines.push(fmt(v));
        if (!lines.length) return;
        var b = boxes[i];
        function textW(arr) { return d3.max(arr, function (l) { return l.length; }) * ls * 0.58; }
        var widest = textW(lines), lh = ls * 1.2 * lines.length;
        if (lines.length > 1 && (b.w < widest || b.h < lh)) { lines = lines.slice(0, 1); widest = textW(lines); lh = ls * 1.2; }   // drop the value before the name
        if (b.w < widest || b.h < lh) return;
        var c = path.centroid(d);
        if (isNaN(c[0])) return;
        var lb = { x: c[0] - widest / 2, y: c[1] - lh / 2, w: widest, h: lh };
        if (placed.hit(lb)) return;
        placed.push(lb);
        var t = lg.append('text').attr('x', c[0]).attr('y', c[1] - (lines.length - 1) * ls * 0.6);
        lines.forEach(function (l, i2) {
          t.append('tspan').attr('x', c[0]).attr('dy', i2 ? ls * 1.15 : 0).attr('font-weight', i2 === 0 && lines.length > 1 ? 600 : 400).text(l);
        });
        count++;
      });
      return count;
    }

    // --- drag the map itself to pan ---
    var panStart = null;
    layer.call(d3.drag()
      .touchable(function () { return view.k !== 1 || view.dx || view.dy; })
      .filter(function (e) { return !e.button && !(e.touches && e.touches.length > 1); })
      .on('start', function (e) { var se = e.sourceEvent, t = se && se.touches && se.touches[0]; panStart = { dx: view.dx, dy: view.dy, mx: 0, my: 0, sx: t ? t.clientX : se.clientX, sy: t ? t.clientY : se.clientY, moved: false }; })
      .on('drag', function (e) {
        if (!panStart) return;
        var se = e.sourceEvent;
        if (se && se.touches && se.touches.length > 1) { panStart.cancelled = true; return; }
        if (panStart.cancelled) return;
        panStart.mx += e.dx; panStart.my += e.dy;
        if (!panStart.moved) {
          var t = se && se.touches && se.touches[0];
          var cx = t ? t.clientX : se.clientX, cy = t ? t.clientY : se.clientY;
          if ((cx - panStart.sx) * (cx - panStart.sx) + (cy - panStart.sy) * (cy - panStart.sy) < 36) return;
          panStart.moved = true;
        }
        layer.attr('transform', 'translate(' + panStart.mx + ',' + panStart.my + ')');
      })
      .on('end', function () {
        if (panStart && panStart.cancelled) { panStart = null; return; }
        if (!panStart || !panStart.moved) { layer.attr('transform', null); panStart = null; return; }
        view.dx = panStart.dx + panStart.mx; view.dy = panStart.dy + panStart.my;
        panStart = null;
        render(); save();
      }));

    drawFrame(svg, W, H, pad);
    showSelection();
  }

  // --- on-canvas selection: click a text, the legend or the arrow to get a remove button ---
  function select(key) {
    selectedKey = key;
    showSelection();
    if (key && key.indexOf('asset-') === 0) {
      var row = ui.assetList.querySelector('[data-asset="' + key.slice(6) + '"]');
      if (row) {
        var panel = row.closest('details'); if (panel) panel.open = true;
        row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        row.classList.add('flash');
        setTimeout(function () { row.classList.remove('flash'); }, 1200);
      }
    }
  }
  function deselect() { selectedKey = null; showSelection(); }
  function showSelection() {
    d3.select(svgNode).selectAll('.sel-box').remove();
    var node = selectedKey && svgNode ? svgNode.querySelector('[data-key="' + selectedKey + '"]') : null;
    if (!node) { selectedKey = null; ui.selTools.hidden = true; return; }
    var bb = node.getBBox(), m = node.transform.baseVal.consolidate();
    var tx = m ? m.matrix.e : 0, ty = m ? m.matrix.f : 0;
    var padPx = 6;
    d3.select(svgNode).append('rect').attr('class', 'sel-box')
      .attr('x', bb.x + tx - padPx).attr('y', bb.y + ty - padPx).attr('width', bb.width + padPx * 2).attr('height', bb.height + padPx * 2).attr('rx', 3);
    var r = node.getBoundingClientRect(), host = ui.selTools.parentNode.getBoundingClientRect();
    var btn = TOUCH ? 40 : 24;
    ui.selTools.style.left = Math.round(Math.max(0, Math.min(host.width - btn, r.right - host.left - btn / 4))) + 'px';
    ui.selTools.style.top = Math.round(Math.max(0, r.top - host.top - btn * 0.75)) + 'px';
    ui.selTools.hidden = false;
  }
  function deleteSelected() {
    var key = selectedKey;
    if (!key) return;
    selectedKey = null;
    if (key === 'legend') { ui.showLegend.checked = false; render(); save(); }
    else if (key === 'north') { ui.northArrow.checked = false; syncUi(); render(); save(); }
    else if (key.indexOf('asset-') === 0) removeAsset(+key.slice(6));
  }
  ui.selDelete.addEventListener('click', function (e) { e.stopPropagation(); deleteSelected(); });
  ui.stage.addEventListener('click', function (e) { if (!e.target.closest('.drag')) deselect(); if (!e.target.closest('.region')) ui.tip.style.display = 'none'; });
  document.addEventListener('pointerdown', function (e) { if (!e.target.closest('#stage')) ui.tip.style.display = 'none'; });
  document.addEventListener('keydown', function (e) {
    if (!selectedKey) return;
    var tag = (document.activeElement && document.activeElement.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); deleteSelected(); }
    else if (e.key === 'Escape') deselect();
  });

  function drawFrame(svg, W, H, pad) {
    var style = ui.frameStyle.value;
    if (!style || style === 'none') return;
    var colour = ui.frameColour.value;
    function line(inset, sw, rx) {
      svg.append('rect').attr('x', inset + sw / 2).attr('y', inset + sw / 2)
        .attr('width', W - 2 * inset - sw).attr('height', H - 2 * inset - sw)
        .attr('fill', 'none').attr('stroke', colour).attr('stroke-width', sw).attr('rx', rx || 0);
    }
    if (style === 'thin') line(0, 2);
    else if (style === 'thick') line(0, 10);
    else if (style === 'double') { line(pad * 0.2, 2.5); line(pad * 0.2 + 6, 1); }
    else if (style === 'inset') line(pad * 0.4, 1.5);
    else if (style === 'rounded') line(6, 2.5, pad * 0.5);
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
  function drawLegend(parent, colour, textColour, vals) {
    var fs = +ui.legendSize.value;
    var sw = fs * 1.3, gap = fs * 0.35;
    var title = ui.legendTitle.value || valueHeaders[current.level] || '';
    var lg = parent.append('g').attr('font-size', fs).attr('fill', textColour);
    var y = 0;
    if (title) { lg.append('text').attr('x', 0).attr('y', fs).attr('font-weight', 600).text(title); y = fs * 1.6; }

    function swatch(fill, label) {
      lg.append('rect').attr('x', 0).attr('y', y).attr('width', sw).attr('height', sw).attr('fill', fill).attr('stroke', '#000').attr('stroke-opacity', 0.15);
      lg.append('text').attr('x', sw + gap * 2).attr('y', y + sw * 0.72).text(label);
      y += sw + gap;
    }

    if (colour.type === 'continuous') {
      var grad = d3.select(svgNode).select('defs').append('linearGradient').attr('id', 'legendGrad');
      var lo = colour.extent[0], hi = colour.extent[1];
      d3.range(0, 1.001, 0.05).forEach(function (t) { grad.append('stop').attr('offset', (t * 100) + '%').attr('stop-color', colour.scale(lo + (hi - lo) * t)); });
      var width = fs * 14;
      lg.append('rect').attr('x', 0).attr('y', y).attr('width', width).attr('height', fs * 0.9).attr('fill', 'url(#legendGrad)');
      lg.append('text').attr('x', 0).attr('y', y + fs * 2).text(fmt(lo));
      lg.append('text').attr('x', width).attr('y', y + fs * 2).attr('text-anchor', 'end').text(fmt(hi));
      if (colour.mid !== null && colour.mid !== undefined) {
        var mx = width * (colour.mid - lo) / (hi - lo);
        lg.append('text').attr('x', mx).attr('y', y + fs * 2).attr('text-anchor', 'middle').text(fmt(colour.mid));
      }
      y += fs * 2.2;
    } else {
      colour.items.forEach(function (it) { swatch(it.colour, it.label); });
    }
    var anyEmpty = current.features.some(function (f) { return !colour.has(vals[f.id]); });
    if (ui.noData.value !== 'none' && anyEmpty) {
      swatch(ui.noData.value === 'hatch' ? 'url(#hatch)' : ui.noData.value, 'No data');
    }
    return lg;
  }

  // ---------------------------------------------------------------------------
  //  Zoom
  // ---------------------------------------------------------------------------
  function setZoom(k, silent) {
    view.k = Math.max(0.5, Math.min(4, Math.round(k * 20) / 20));
    ui.mapZoom.value = Math.round(view.k * 100);
    ui.zoomValue.textContent = Math.round(view.k * 100) + '%';
    if (!silent) { render(); save(); }
  }
  ui.mapZoom.addEventListener('input', function () {
    if (!lastLayout || !svgNode) return;
    var k0 = gesture ? gesture.k0 : view.k;
    zoomAbout(lastLayout.cx, lastLayout.cy, (+ui.mapZoom.value / 100) / k0);
  });
  ui.mapZoom.addEventListener('change', function () { clearTimeout(renderTimer); if (gesture) commitZoom(); else setZoom(+ui.mapZoom.value / 100); });
  ui.zoomIn.addEventListener('click', function () { zoomCentre(view.k + 0.1); });

  // Zoom so that the canvas point under the pointer stays put.
  function canvasPoint(clientX, clientY) {
    var pt = svgNode.createSVGPoint(); pt.x = clientX; pt.y = clientY;
    var ctm = svgNode.getScreenCTM();
    return ctm ? pt.matrixTransform(ctm.inverse()) : { x: clientX, y: clientY };
  }
  var gesture = null;          // { k0, dx0, dy0, r, px, py } during a wheel or pinch gesture
  function zoomAbout(px, py, r) {
    if (!lastLayout) return;
    var k0 = gesture ? gesture.k0 : view.k, dx0 = gesture ? gesture.dx0 : view.dx, dy0 = gesture ? gesture.dy0 : view.dy;
    var k1 = Math.max(0.5, Math.min(4, k0 * r));
    r = k1 / k0;
    var layer = svgNode && svgNode.querySelector('.map-layer');
    if (layer) layer.setAttribute('transform', 'translate(' + px + ',' + py + ') scale(' + r + ') translate(' + (-px) + ',' + (-py) + ')');
    gesture = { k0: k0, dx0: dx0, dy0: dy0, r: r, px: px, py: py };
    ui.zoomValue.textContent = Math.round(k1 * 100) + '%';
    ui.mapZoom.value = Math.round(k1 * 100);
    ui.selTools.hidden = true;
  }
  function commitZoom() {
    if (!gesture) return;
    var g = gesture; gesture = null;
    var cx = lastLayout.cx, cy = lastLayout.cy;
    var k1 = Math.max(0.5, Math.min(4, Math.round(g.k0 * g.r * 20) / 20));
    var r = k1 / g.k0;
    // screen = cx + (fit - cx) * k + dx ; keep the point (px, py) fixed while k scales by r
    view.dx = (g.px - cx) - (g.px - cx - g.dx0) * r;
    view.dy = (g.py - cy) - (g.py - cy - g.dy0) * r;
    setZoom(k1);
  }
  function zoomCentre(k1) {
    if (!lastLayout || !svgNode || !current.features.length) { setZoom(k1); return; }
    gesture = null;
    zoomAbout(lastLayout.cx, lastLayout.cy, k1 / view.k);
    commitZoom();
  }
  var wheelTimer = null;
  ui.stage.addEventListener('wheel', function (e) {
    if (!(e.ctrlKey || e.metaKey) || !svgNode || !current.features.length) return;
    e.preventDefault();
    var p = canvasPoint(e.clientX, e.clientY);
    var step = Math.exp(-e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0015));
    zoomAbout(gesture ? gesture.px : p.x, gesture ? gesture.py : p.y, (gesture ? gesture.r : 1) * step);
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(commitZoom, 160);
  }, { passive: false });

  var pinch = null;            // { d0, px, py }
  function touchDist(t) { var dx = t[0].clientX - t[1].clientX, dy = t[0].clientY - t[1].clientY; return Math.sqrt(dx * dx + dy * dy); }
  ui.stage.addEventListener('touchstart', function (e) {
    if (e.touches.length !== 2 || !svgNode || !current.features.length) return;
    var mid = canvasPoint((e.touches[0].clientX + e.touches[1].clientX) / 2, (e.touches[0].clientY + e.touches[1].clientY) / 2);
    pinch = { d0: touchDist(e.touches), px: mid.x, py: mid.y };
    gesture = null;
    e.preventDefault();
  }, { passive: false, capture: true });
  ui.stage.addEventListener('touchmove', function (e) {
    if (!pinch || e.touches.length !== 2) return;
    e.preventDefault();
    zoomAbout(pinch.px, pinch.py, touchDist(e.touches) / pinch.d0);
  }, { passive: false, capture: true });
  function endPinch() { if (!pinch) return; pinch = null; commitZoom(); }
  ui.stage.addEventListener('touchend', endPinch, true);
  ui.stage.addEventListener('touchcancel', endPinch, true);

  ui.zoomOut.addEventListener('click', function () { zoomCentre(view.k - 0.1); });
  ui.zoomReset.addEventListener('click', function () { view.dx = 0; view.dy = 0; setZoom(1); });

  // ---------------------------------------------------------------------------
  //  Export
  // ---------------------------------------------------------------------------
  function slug() {
    var title = assets.filter(function (a) { return a.kind === 'title' && a.text.trim(); })[0];
    var base = title ? title.text : (regionLabel() + ' ' + current.level);
    var s = base.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    if (!s) s = (regionLabel() + ' ' + current.level).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    return s || 'map';
  }

  function svgString() {
    var clone = svgNode.cloneNode(true);
    clone.querySelectorAll('.sel-box').forEach(function (el) { el.parentNode.removeChild(el); });
    clone.querySelectorAll('[data-id], [data-key], [class], [style], [tabindex], [role]').forEach(function (el) {
      ['data-id', 'data-key', 'class', 'style', 'tabindex', 'role'].forEach(function (a) { el.removeAttribute(a); });
    });
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(clone);
  }

  function download(blob, name) {
    var file = null;
    try { file = new File([blob], name, { type: blob.type }); } catch (e) { /* older browsers */ }
    if (TOUCH && file && navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
      navigator.share({ files: [file], title: name }).catch(function (err) { if (err && err.name !== 'AbortError') anchorDownload(blob, name); });
      return;
    }
    anchorDownload(blob, name);
  }
  function anchorDownload(blob, name) {
    var url = URL.createObjectURL(blob);
    if (!('download' in HTMLAnchorElement.prototype)) { window.open(url, '_blank'); return; }
    var a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 60000);
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

  function exportFailed(err) { setBusy(false); setStatus('Export failed: ' + (err && err.message ? err.message : err)); }
  function setBusy(on) {
    ui.exportRow.querySelectorAll('button').forEach(function (b) { b.disabled = !!on; });
    ui.exportRow.setAttribute('aria-busy', on ? 'true' : 'false');
  }
  function csvSafe(v) { return (typeof v === 'string' && /^[=+@]/.test(v)) ? "'" + v : v; }

  function exportPng(scale) {
    var W = +svgNode.getAttribute('width'), H = +svgNode.getAttribute('height');
    var cap = Math.sqrt((TOUCH ? 16e6 : 64e6) / (W * H));           // stay under the browser's canvas area limit
    var used = Math.min(scale, Math.floor(cap * 4) / 4);
    setBusy(true);
    rasterize(used).then(function (c) {
      if (ui.background.value !== 'transparent') {
        var px = c.getContext('2d').getImageData(Math.floor(c.width / 2), Math.floor(c.height / 2), 1, 1).data;
        if (px[3] === 0) throw new Error('the image came out blank, try a smaller size');
      }
      c.toBlob(function (b) { setBusy(false); if (!b) return exportFailed(new Error('image too large for this browser')); download(b, slug() + (used > 1 ? '@' + used + 'x' : '') + '.png'); }, 'image/png');
    }).catch(exportFailed);
  }

  function copyImage() {
    if (!(navigator.clipboard && window.ClipboardItem)) return;
    setBusy(true);
    var W = +svgNode.getAttribute('width'), H = +svgNode.getAttribute('height');
    var used = Math.min(2, Math.floor(Math.sqrt(16e6 / (W * H)) * 4) / 4);
    // Safari needs the promise handed to ClipboardItem up front
    var blobPromise = rasterize(used).then(function (c) { return new Promise(function (res, rej) { c.toBlob(function (b) { b ? res(b) : rej(new Error('image too large')); }, 'image/png'); }); });
    navigator.clipboard.write([new ClipboardItem({ 'image/png': blobPromise })])
      .then(function () { setBusy(false); setStatus('Image copied'); setTimeout(function () { if (ui.matchStatus.textContent === 'Image copied') { setStatus(''); if (lastMatch) reportMatch(); } }, 2000); })
      .catch(exportFailed);
  }

  function exportPdf() {
    if (!window.jspdf) {
      setBusy(true); setStatus('Loading PDF support…');
      loadScript(JSPDF_URL, JSPDF_SRI).then(function () { setStatus(''); setBusy(false); exportPdf(); }, exportFailed);
      return;
    }
    setBusy(true);
    rasterize(3).then(function (c) {
      var W = +svgNode.getAttribute('width'), H = +svgNode.getAttribute('height');
      var doc = new window.jspdf.jsPDF({ orientation: W >= H ? 'landscape' : 'portrait', unit: 'px', format: [W, H], hotfixes: ['px_scaling'], compress: true });
      doc.addImage(c.toDataURL('image/png'), 'PNG', 0, 0, W, H, undefined, 'FAST');   // deflate the bitmap, else a plain map is tens of MB
      setBusy(false);
      download(doc.output('blob'), slug() + '.pdf');
    }).catch(exportFailed);
  }

  function projectData() {
    var settings = {};
    SETTING_IDS.forEach(function (id) { var el = ui[id]; settings[id] = el.type === 'checkbox' ? el.checked : el.value; });
    return { app: 'india-map-maker', version: 1, savedAt: new Date().toISOString(),
      settings: settings, region: region, values: values, valueHeaders: valueHeaders, offsets: offsets,
      assets: assets, assetSeq: assetSeq, autoSuffix: autoSuffix, paste: ui.paste.value, userAliases: userAliases, labelSizeAuto: labelSizeAuto };
  }
  function exportProject() {
    download(new Blob([JSON.stringify(projectData())], { type: 'application/json' }), slug() + '.mapmaker.json');
  }
  function openProject(file) {
    var fr = new FileReader();
    fr.onerror = function () { setStatus('Could not read ' + file.name + '.'); };
    fr.onload = function () {
      try {
        var data = JSON.parse(fr.result);
        if (!data || data.app !== 'india-map-maker') { setStatus('That file is not a saved map project.'); return; }
        localStorage.setItem(STORE_KEY, JSON.stringify(data));
        location.reload();
      } catch (e) { setStatus('Could not open ' + file.name + ': ' + e.message); }
    };
    fr.readAsText(file);
  }

  document.querySelectorAll('[data-export]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!svgNode) return;
      var kind = btn.dataset.export;
      if (kind === 'png') exportPng(+btn.dataset.scale || 1);
      else if (kind === 'copy') copyImage();
      else if (kind === 'project') exportProject();
      else if (kind === 'svg') download(new Blob([svgString()], { type: 'image/svg+xml' }), slug() + '.svg');
      else if (kind === 'pdf') exportPdf();
    });
  });

  // ---------------------------------------------------------------------------
  //  Persistence
  // ---------------------------------------------------------------------------
  var saveTimer = null, saveFailed = false;
  function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      var settings = {};
      SETTING_IDS.forEach(function (id) { var el = ui[id]; settings[id] = el.type === 'checkbox' ? el.checked : el.value; });
      try {
        localStorage.setItem(STORE_KEY, JSON.stringify({
          settings: settings, region: region, values: values, valueHeaders: valueHeaders, offsets: offsets,
          assets: assets, assetSeq: assetSeq, autoSuffix: autoSuffix, paste: ui.paste.value.length < 500000 ? ui.paste.value : '',
          userAliases: userAliases, labelSizeAuto: labelSizeAuto
        }));
        saveFailed = false;
        $('saveNote').hidden = false;
      } catch (e) { if (!saveFailed) { saveFailed = true; setStatus('This browser is not saving your work between visits.'); } }
    }, 300);
  }

  function restore() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (!raw) return;
      var data;
      try { data = JSON.parse(raw); } catch (e) { localStorage.removeItem(STORE_KEY); return; }
      var st = data.settings || {};
      Object.keys(st).forEach(function (id) {
        var el = ui[id];
        if (!el || SETTING_IDS.indexOf(id) === -1) return;
        if (el.type === 'checkbox') { el.checked = !!st[id]; return; }
        var before = el.value;
        el.value = st[id];
        if (el.tagName === 'SELECT' && el.value !== String(st[id])) el.value = before;   // stale option: keep default
        if (el.type === 'number' && el.value === '' && id !== 'decimals') el.value = before;
        if (el.type === 'color' && !HEX.test(String(st[id]))) el.value = before;
      });
      LEVEL_KEYS.forEach(function (lv) {
        var v = data.values && data.values[lv];
        if (v && typeof v === 'object' && !Array.isArray(v)) values[lv] = v;
      });
      if (data.region && typeof data.region === 'object') region = { state: String(data.region.state || ''), district: String(data.region.district || '') };
      LEVEL_KEYS.forEach(function (lv) { if (data.valueHeaders && typeof data.valueHeaders[lv] === 'string') valueHeaders[lv] = data.valueHeaders[lv]; });
      offsets = {};
      Object.keys(data.offsets || {}).forEach(function (k) {
        var o = data.offsets[k];
        if (o && isFinite(o.dx) && isFinite(o.dy)) offsets[k] = { dx: +o.dx, dy: +o.dy, band: o.band || null };
      });
      autoSuffix = !!data.autoSuffix;
      if (typeof data.paste === 'string') ui.paste.value = data.paste;
      view = { k: 1, dx: 0, dy: 0 };   // zoom and pan always start fresh
      if (data.userAliases && typeof data.userAliases === 'object') {
        LEVEL_KEYS.forEach(function (lv) {
          var m = data.userAliases[lv];
          if (m && typeof m === 'object') Object.keys(m).forEach(function (k) { if (typeof m[k] === 'string' && Object.prototype.hasOwnProperty.call(m, k)) userAliases[lv][k] = m[k]; });
        });
      }
      labelSizeAuto = data.labelSizeAuto !== false;
      if (Array.isArray(data.assets)) {
        assets = data.assets.filter(function (a) { return a && typeof a === 'object' && Object.prototype.hasOwnProperty.call(ASSET_KINDS, a.kind); }).map(function (a) {
          var d = ASSET_KINDS[a.kind];
          var posOk = (a.kind === 'text' ? CORNER_POS : BAND_POS).indexOf(a.pos) !== -1;
          return {
            id: isFinite(a.id) ? +a.id : 0, kind: a.kind, text: typeof a.text === 'string' ? a.text : d.text,
            size: isFinite(a.size) ? Math.max(6, Math.min(160, +a.size)) : d.size, font: Object.prototype.hasOwnProperty.call(FONTS, a.font) ? a.font : 'sans',
            weight: a.weight >= 600 ? 700 : 400, italic: !!a.italic, colour: HEX.test(String(a.colour)) ? a.colour : d.colour,
            pos: posOk ? a.pos : d.pos
          };
        });
        assets.forEach(function (a) { if (!a.id || assets.some(function (b) { return b !== a && b.id === a.id; })) a.id = (d3.max(assets, function (b) { return b.id; }) || 0) + 1; });
        assetSeq = Math.max(+data.assetSeq || 0, (d3.max(assets, function (a) { return a.id; }) || 0) + 1);
      }
    } catch (e) { /* ignore */ }
  }

  // ---------------------------------------------------------------------------
  //  Events
  // ---------------------------------------------------------------------------
  ui.regionState.addEventListener('change', function () {
    region.state = ui.regionState.value;
    region.district = '';
    if (region.state && ui.level.value === 'states') ui.level.value = 'districts';
    view = { k: 1, dx: 0, dy: 0 }; setZoom(1, true);
    Promise.resolve(populateDistricts()).then(refresh).catch(function (err) { setStatus('Could not load boundaries: ' + err.message); });
  });
  ui.regionDistrict.addEventListener('change', function () {
    region.district = ui.regionDistrict.value;
    if (region.district && !hasDistrictParent(ui.level.value)) ui.level.value = 'subdistricts';
    view = { k: 1, dx: 0, dy: 0 }; setZoom(1, true);
    refresh();
  });
  ui.level.addEventListener('change', function () {
    if (!hasDistrictParent(ui.level.value) && region.district) { region.district = ''; ui.regionDistrict.value = ''; }
    ui.districtField.hidden = !region.state || !usesDistricts(ui.level.value);
    view = { k: 1, dx: 0, dy: 0 }; setZoom(1, true);
    refresh();
  });

  ui.applyData.addEventListener('click', function () { sheets = null; valueColOverride = -1; applyRows(parseText(ui.paste.value)); });
  ui.paste.addEventListener('input', function (e) {
    if (e.inputType === 'insertFromPaste' || e.inputType === 'insertLineBreak' || /[\n\t]/.test(e.data || '')) { sheets = null; valueColOverride = -1; applyRows(parseText(ui.paste.value)); }
    else save();
  });
  ui.paste.addEventListener('paste', function () { setTimeout(function () { sheets = null; valueColOverride = -1; applyRows(parseText(ui.paste.value)); }, 0); });
  var undoSnapshot = null;
  function snapshot() {
    return { level: current.level, values: JSON.parse(JSON.stringify(values)), paste: ui.paste.value, headers: JSON.parse(JSON.stringify(valueHeaders)),
      assets: JSON.parse(JSON.stringify(assets)), offsets: JSON.parse(JSON.stringify(offsets)) };
  }
  function offerUndo(label) {
    ui.matchStatus.innerHTML = escapeHtml(label) + ' · <a id="undoClear" role="button" tabindex="0">Undo</a>';
    ui.matchStatus.classList.remove('notice');
    var undo = function () {
      if (!undoSnapshot) return;
      values = undoSnapshot.values; ui.paste.value = undoSnapshot.paste; valueHeaders = undoSnapshot.headers;
      assets = undoSnapshot.assets; offsets = undoSnapshot.offsets; undoSnapshot = null;
      renderAssetList(); lastMatch = null; reportMatch(); buildTable(); render(); save();
    };
    var a = ui.matchStatus.querySelector('#undoClear');
    a.addEventListener('click', undo);
    a.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); undo(); } });
  }
  ui.clearData.addEventListener('click', function () {
    undoSnapshot = snapshot();
    values[current.level] = {};
    ui.paste.value = ''; lastMatch = null; valueHeaders[current.level] = ''; pendingFixes = []; assumed = [];
    buildTable(); render(); save();
    renderFixes(); offerUndo('Cleared');
  });
  ui.startOver.addEventListener('click', function () {
    undoSnapshot = snapshot();
    values = levelMap(function () { return {}; }); valueHeaders = levelMap('');
    assets = []; offsets = {}; ui.paste.value = ''; lastMatch = null; pendingFixes = []; assumed = [];
    view = { k: 1, dx: 0, dy: 0 }; setZoom(1, true);
    SETTING_IDS.forEach(function (id) { var el = ui[id]; if (id === 'level') return; var d = el.getAttribute(el.type === 'checkbox' ? 'checked' : 'value'); if (el.tagName === 'SELECT') { el.value = el.querySelector('option[selected]') ? el.querySelector('option[selected]').value : el.options[0].value; } else if (el.type === 'checkbox') { el.checked = el.hasAttribute('checked'); } else { el.value = d == null ? '' : d; } });
    labelSizeAuto = true; ui.labelSize.value = suggestedLabelSize(current.features.length);
    lastBackground = ui.background.value;
    renderAssetList(); syncUi(); buildTable(); render(); save();
    renderFixes(); offerUndo('Started over');
  });
  function updateReportLink() {
    var body = 'What happened:\n\n\nDetails: level ' + current.level + ', area ' + regionLabel() + ', ' + navigator.userAgent;
    ui.reportLink.href = 'https://github.com/yashveeeeeeer/india-geodata/issues/new?title=' + encodeURIComponent('Map Maker: ') + '&body=' + encodeURIComponent(body);
  }
  ui.reportLink.addEventListener('focus', updateReportLink);
  ui.reportLink.addEventListener('mouseenter', updateReportLink);
  ui.fileInput.addEventListener('change', function () { readFile(ui.fileInput.files[0]); ui.fileInput.value = ''; });
  ['dragenter', 'dragover'].forEach(function (ev) {
    ui.fileDrop.addEventListener(ev, function (e) { e.preventDefault(); ui.fileDrop.classList.add('over'); });
  });
  ['dragleave', 'drop'].forEach(function (ev) {
    ui.fileDrop.addEventListener(ev, function (e) { e.preventDefault(); ui.fileDrop.classList.remove('over'); });
  });
  ui.fileDrop.addEventListener('drop', function (e) { readFile(e.dataTransfer.files[0]); });
  // a file dropped anywhere on the page loads instead of navigating away
  document.addEventListener('dragover', function (e) { if (e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types, 'Files') !== -1) e.preventDefault(); });
  document.addEventListener('drop', function (e) {
    if (!e.dataTransfer || !e.dataTransfer.files || !e.dataTransfer.files.length) return;
    e.preventDefault();
    if (!e.target.closest('#fileDrop')) readFile(e.dataTransfer.files[0]);
  });
  ui.tableSearch.addEventListener('input', buildTable);

  $('resetLayout').addEventListener('click', function () { offsets = {}; view = { k: 1, dx: 0, dy: 0 }; setZoom(1, true); render(); save(); });
  var POS_KEYS = { legendPos: ['legend'], northPos: ['north'] };
  Object.keys(POS_KEYS).forEach(function (id) {
    ui[id].addEventListener('change', function () { POS_KEYS[id].forEach(function (k) { delete offsets[k]; }); });
  });
  ui.canvas.addEventListener('change', function () { offsets = {}; view = { k: 1, dx: 0, dy: 0 }; setZoom(1, true); });

  // background flips: swap colours that still sit on the previous preset, including default text colours
  var lastBackground = ui.background.value;
  ui.background.addEventListener('change', function () {
    var wasDark = lastBackground === '#0f172a', isDark = ui.background.value === '#0f172a';
    if (wasDark !== isDark) {
      var from = PRESETS[wasDark ? 'dark' : 'light'], to = PRESETS[isDark ? 'dark' : 'light'];
      Object.keys(to).forEach(function (id) { if (ui[id].value === from[id]) ui[id].value = to[id]; });
      assets.forEach(function (a) {
        var d = ASSET_KINDS[a.kind];
        if (a.colour === (wasDark ? d.dark : d.colour)) a.colour = isDark ? d.dark : d.colour;
      });
      renderAssetList();
    }
    lastBackground = ui.background.value;
  });

  var renderTimer = null;
  function renderSoon() {
    clearTimeout(renderTimer);
    renderTimer = setTimeout(function () { render(); save(); }, 120);
  }

  ui.labelSize.addEventListener('input', function () { labelSizeAuto = false; });
  SETTING_IDS.forEach(function (id) {
    if (id === 'level') return;
    var el = ui[id];
    var typed = el.tagName === 'INPUT' && (el.type === 'text' || el.type === 'number' || el.type === 'color');
    if (typed) {
      el.addEventListener('input', function () { syncUi(); renderSoon(); });
      el.addEventListener('change', function () { clearTimeout(renderTimer); syncUi(); render(); save(); });
    } else {
      el.addEventListener('change', function () { syncUi(); render(); save(); });
    }
  });

  function syncUi() {
    ui.customColours.hidden = ui.ramp.value !== 'custom';
    ui.northField.hidden = !ui.northArrow.checked;
    ui.bucketsField.hidden = ui.scaleMode.value === 'continuous';
    ui.scaleHint.textContent = SCALE_HINTS[ui.scaleMode.value] || '';
    ui.legendTitle.placeholder = valueHeaders[current.level] || '';
    var hasData = Object.keys(values[current.level] || {}).length > 0;
    ui.copyImage.hidden = !(navigator.clipboard && window.ClipboardItem);
  }

  var resizeTimer = null;
  window.addEventListener('resize', function () {                 // keep the canvas fitted to its frame
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () { if (svgNode) showSelection(); }, 150);
  });

  // ---------------------------------------------------------------------------
  //  Boot
  // ---------------------------------------------------------------------------
  restore();
  lastBackground = ui.background.value;
  syncUi();
  setZoom(view.k, true);
  renderAssetList();
  // Panels: Region and Data start open; each browser remembers what the user opened or closed
  var PANEL_KEY = 'igd-mapmaker-panels';
  (function () {
    var saved = {};
    try { saved = JSON.parse(localStorage.getItem(PANEL_KEY)) || {}; } catch (e) { saved = {}; }
    document.querySelectorAll('.maps-side details.panel').forEach(function (p) {
      var sum = p.querySelector('summary');
      var key = sum ? sum.textContent.trim() : '';
      if (!key) return;
      if (Object.prototype.hasOwnProperty.call(saved, key)) p.open = !!saved[key];
      p.addEventListener('toggle', function () {
        saved[key] = p.open;
        try { localStorage.setItem(PANEL_KEY, JSON.stringify(saved)); } catch (e) { /* storage blocked */ }
      });
    });
  })();

  Promise.all([loadLayer('states'), loadLayer(ui.level.value)]).then(function (res) {
    populateStates(res[0]);
    ui.regionState.value = region.state;
    if (ui.regionState.value !== region.state) { region.state = ''; region.district = ''; }
    return populateDistricts();
  }).then(refresh).catch(function (err) { setStatus('Could not load boundaries: ' + err.message); });
})();
