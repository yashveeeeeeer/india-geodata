/* India Map Maker: pure helpers for names, numbers and text.
   Shared by the page (window.IGDMapCore) and the Node test suite (module.exports). */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.IGDMapCore = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var FONTS = {
    sans: { label: 'Sans', stack: 'Helvetica Neue, Helvetica, Arial, sans-serif', em: 0.52 },
    humanist: { label: 'Humanist', stack: 'Segoe UI, Tahoma, Geneva, sans-serif', em: 0.53 },
    rounded: { label: 'Rounded', stack: 'Verdana, Trebuchet MS, sans-serif', em: 0.6 },
    condensed: { label: 'Condensed', stack: 'Arial Narrow, Roboto Condensed, Helvetica, sans-serif', em: 0.45 },
    serif: { label: 'Serif', stack: 'Georgia, Times New Roman, serif', em: 0.52 },
    classic: { label: 'Classic serif', stack: 'Times New Roman, Times, serif', em: 0.48 },
    mono: { label: 'Mono', stack: 'Consolas, Menlo, Courier New, monospace', em: 0.6 }
  };
  var HEX = /^#[0-9a-f]{6}$/i;

  // Break text into lines that fit maxWidth, using the font's average glyph width.
  function wrapText(text, size, fontKey, weight, maxWidth) {
    var em = (FONTS[fontKey] || FONTS.sans).em * (weight >= 600 ? 1.07 : 1);
    var perChar = size * em;
    var maxChars = Math.max(4, Math.floor(maxWidth / perChar));
    var lines = [];
    String(text).split(/\r?\n|\\n/).forEach(function (para) {
      var words = para.split(/\s+/).filter(Boolean);
      if (!words.length) return;
      var line = '';
      words.forEach(function (w) {
        while (w.length > maxChars) { if (line) { lines.push(line); line = ''; } lines.push(w.slice(0, maxChars)); w = w.slice(maxChars); }
        var next = line ? line + ' ' + w : w;
        if (next.length > maxChars && line) { lines.push(line); line = w; } else line = next;
      });
      if (line) lines.push(line);
    });
    return lines.length ? lines : [''];
  }

  // Spelling variants and old names, keyed and valued in compact() form.
  var ALIASES = {
    bangalore: 'bengaluruurban', bangaloreurban: 'bengaluruurban', bangalorerural: 'bengalururural', bengaluru: 'bengaluruurban',
    mysore: 'mysuru', belgaum: 'belagavi', gulbarga: 'kalaburagi', bijapur: 'vijayapura', bellary: 'ballari',
    tumkur: 'tumakuru', shimoga: 'shivamogga', chikmagalur: 'chikkamagaluru', hospet: 'vijayanagar',
    allahabad: 'prayagraj', faizabad: 'ayodhya', hoshangabad: 'narmadapuram', orissa: 'odisha',
    pondicherry: 'puducherry', uttaranchal: 'uttarakhand', bombay: 'mumbai', calcutta: 'kolkata', madras: 'chennai',
    poona: 'pune', baroda: 'vadodara', cochin: 'ernakulam', trivandrum: 'thiruvananthapuram', calicut: 'kozhikode',
    cannanore: 'kannur', quilon: 'kollam', alleppey: 'alappuzha', trichur: 'thrissur', palghat: 'palakkad',
    tuticorin: 'tuticorin', thoothukudi: 'tuticorin', tanjore: 'thanjavur', trichy: 'tiruchirappalli', tiruchirapalli: 'tiruchirappalli',
    nctofdelhi: 'delhi', nationalcapitalterritoryofdelhi: 'delhi', telengana: 'telangana', chattisgarh: 'chhattisgarh',
    andamanandnicobar: 'andamanandnicobarislands', aandnislands: 'andamanandnicobarislands',
    dadraandnagarhaveli: 'dadraandnagarhavelianddamananddiu', damananddiu: 'dadraandnagarhavelianddamananddiu',
    dnhanddd: 'dadraandnagarhavelianddamananddiu', jandk: 'jammuandkashmir', jk: 'jammuandkashmir',
    up: 'uttarpradesh', mp: 'madhyapradesh', hp: 'himachalpradesh', ap: 'andhrapradesh', tn: 'tamilnadu', wb: 'westbengal',
    kerela: 'kerala', karnatak: 'karnataka', gujrat: 'gujarat', rajastan: 'rajasthan', panjab: 'punjab', hariyana: 'haryana',
    chhatisgarh: 'chhattisgarh', uttarkhand: 'uttarakhand', utarakhand: 'uttarakhand', jharkand: 'jharkhand', bengal: 'westbengal',
    andhra: 'andhrapradesh', telanganastate: 'telangana', jammukashmir: 'jammuandkashmir', jammuandkashmirut: 'jammuandkashmir',
    ladakhut: 'ladakh', newdelhi: 'delhi', delhinct: 'delhi', nctdelhi: 'delhi', puducherryut: 'puducherry', chandigarhut: 'chandigarh',
    andamannicobar: 'andamanandnicobarislands', andamanandnicobarisland: 'andamanandnicobarislands', andamans: 'andamanandnicobarislands',
    lakshadweepislands: 'lakshadweep', dadranagarhaveli: 'dadraandnagarhavelianddamananddiu', dnh: 'dadraandnagarhavelianddamananddiu',
    dadraandnagarhavelidamananddiu: 'dadraandnagarhavelianddamananddiu', dadraandnagarhaveliandamananddiu: 'dadraandnagarhavelianddamananddiu',
    arunachal: 'arunachalpradesh', himachal: 'himachalpradesh', madhya: 'madhyapradesh', odissa: 'odisha', orisa: 'odisha',
    tamilnad: 'tamilnadu', tamilnaadu: 'tamilnadu', maharastra: 'maharashtra', maharashtrastate: 'maharashtra', chattisgarhstate: 'chhattisgarh',
    north24parganas: '24paraganasnorth', south24parganas: '24paraganassouth', '24parganasnorth': '24paraganasnorth', '24parganassouth': '24paraganassouth',
    northtwentyfourparganas: '24paraganasnorth', southtwentyfourparganas: '24paraganassouth', twentyfourparganasnorth: '24paraganasnorth',
    twentyfourparganassouth: '24paraganassouth', north24pgs: '24paraganasnorth', south24pgs: '24paraganassouth', gurgaon: 'gurugram', cuddapah: 'ysr', kadapa: 'ysr', ysrkadapa: 'ysr',
    sriganganagar: 'ganganagar', mewat: 'nuh', palamau: 'palamu', hazaribag: 'hazaribagh', kancheepuram: 'kanchipuram', tiruvallur: 'thiruvallur',
    tiruvannamalai: 'tiruvannamalai', villupuram: 'villupuram', trivandrumdistrict: 'thiruvananthapuram', ernakulum: 'ernakulam', calicutdistrict: 'kozhikode'
  };

  var HEADER_WORDS = /^(name|names|region|regions|area|state|states|ut|stateut|statesuts|st|district|districts|dist|subdistrict|subdistricts|tehsil|taluk|taluka|mandal|block|constituency|pc|ac|unit|place|location)$/;

  function compact(s) {
    return String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/&/g, ' and ').replace(/\b(district|dist|distt|dt)\b\.?/g, '')
      .replace(/\b(state|u\.?t\.?|union territory|the)\b\.?/g, '').replace(/[^a-z0-9]+/g, '');
  }

  // Same as compact() but with the words sorted, so "North 24 Parganas" and "24 Parganas North" agree.
  function tokenKey(s) {
    var words = String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/&/g, ' and ')
      .replace(/\b(district|dist|distt|dt|state|u\.?t\.?|union territory|the)\b\.?/g, '')
      .split(/[^a-z0-9]+/).filter(Boolean).sort();
    return words.join('');
  }

  function digitsOnly(s) { return /^\d+$/.test(String(s).trim()); }

  // General edit distance for suggestion scoring.
  function editDistance(a, b) {
    var prev = [], cur = [], i, j;
    for (j = 0; j <= b.length; j++) prev[j] = j;
    for (i = 1; i <= a.length; i++) {
      cur = [i];
      for (j = 1; j <= b.length; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = cur;
    }
    return prev[b.length];
  }
  function levenshtein(a, b) {
    if (Math.abs(a.length - b.length) > 2) return 99;   // quick reject for the auto-match tolerance
    return editDistance(a, b);
  }
  function similarity(a, b) {
    if (a === b) return 1;
    if (!a || !b) return 0;
    if (a.indexOf(b) === 0 || b.indexOf(a) === 0) return 0.9 - Math.abs(a.length - b.length) / (4 * Math.max(a.length, b.length));
    if (a.indexOf(b) !== -1 || b.indexOf(a) !== -1) return 0.8;
    return 1 - editDistance(a, b) / Math.max(a.length, b.length);
  }

  var EMPTY_TOKENS = /^(na|n\/a|n\.a\.?|nan|null|nil|none|-{1,3}|–|—|\.\.|\.|\?|#n\/a|#value!|#div\/0!|#ref!)$/i;
  function isEmptyToken(v) { return v == null || String(v).trim() === '' || EMPTY_TOKENS.test(String(v).trim()); }

  function toNumber(v) {
    if (typeof v === 'number') return isFinite(v) ? v : NaN;
    var s = String(v).trim().replace(/[−–]/, '-').replace(/^(rs\.?|inr|₹|\$|€|£)\s*/i, '').replace(/[₹$€£,%\s]/g, '').replace(/^\((.*)\)$/, '-$1');
    if (s === '' || s === '-') return NaN;
    return Number(s);
  }

  // Rows from pasted text: tab separated, comma separated, or "Name 94" typed by hand.
  // `parsers` supplies tsvParseRows and csvParseRows (d3 in the browser).
  function parseText(text, parsers) {
    var lines = String(text).split(/\r?\n/).filter(function (l) { return l.trim(); });
    if (!lines.length) return [];
    var useTab = lines.some(function (l) { return l.indexOf('\t') !== -1; });
    if (useTab) return parsers.tsvParseRows(lines.join('\n'));
    if (lines.some(function (l) { return l.indexOf(',') !== -1; })) return parsers.csvParseRows(lines.join('\n'));
    return lines.map(function (l) {
      var m = l.trim().match(/^(.*\S)\s+(\S+)$/);
      return m ? [m[1], m[2]] : [l.trim()];
    });
  }

  function indianGroup(intStr) {
    if (intStr.length <= 3) return intStr;
    var last3 = intStr.slice(-3), rest = intStr.slice(0, -3);
    return rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + last3;
  }

  // style: 'plain' | 'indian' | 'lakh' | 'metric'
  function fmtNumber(v, d, style) {
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
      if (style === 'indian' || style === 'lakh') intPart = indianGroup(intPart);
      else if (style === 'metric') intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
      s = intPart + (fixed[1] ? '.' + fixed[1] : '');
    }
    return neg + s;
  }

  // Pick enough decimals to tell the given break values apart.
  function computeAutoDecimals(nums, breaks) {
    if (nums.every(function (n) { return Number.isInteger(n); })) return 0;
    var pts = (breaks && breaks.length > 1 ? breaks : nums).slice().sort(function (a, b) { return a - b; });
    var minStep = Infinity;
    for (var i = 1; i < pts.length; i++) { var s = pts[i] - pts[i - 1]; if (s > 0 && s < minStep) minStep = s; }
    if (!isFinite(minStep)) {
      var maxFrac = 0;
      nums.forEach(function (n) { var f = String(n).split('.')[1]; if (f && f.length > maxFrac) maxFrac = f.length; });
      return Math.min(3, maxFrac || 1);
    }
    var precision = Math.max(0, -Math.floor(Math.log(Math.abs(minStep)) / Math.LN10 + 1e-9));
    return Math.min(3, Math.max(1, precision));
  }

  var CLAMPED = { Greys: 1, Blues: 1, Greens: 1, Oranges: 1, Reds: 1, Purples: 1, YlOrRd: 1, YlGnBu: 1 };
  var QUALITATIVE = ['#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f', '#edc949', '#af7aa1', '#ff9da7', '#9c755f', '#bab0ab'];
  var DIVERGING = { RdBu: 1, RdYlGn: 1 };

  return {
    FONTS: FONTS, HEX: HEX, ALIASES: ALIASES, HEADER_WORDS: HEADER_WORDS, EMPTY_TOKENS: EMPTY_TOKENS,
    CLAMPED: CLAMPED, QUALITATIVE: QUALITATIVE, DIVERGING: DIVERGING,
    wrapText: wrapText, compact: compact, tokenKey: tokenKey, digitsOnly: digitsOnly, editDistance: editDistance,
    levenshtein: levenshtein, similarity: similarity, isEmptyToken: isEmptyToken, toNumber: toNumber, parseText: parseText,
    indianGroup: indianGroup, fmtNumber: fmtNumber, computeAutoDecimals: computeAutoDecimals
  };
}));
