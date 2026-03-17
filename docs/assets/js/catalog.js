(function () {
  'use strict';

  var searchBox     = document.getElementById('searchBox');
  var resultCount   = document.getElementById('resultCount');
  var pills         = document.querySelectorAll('.pill[data-category]');
  var groups        = document.querySelectorAll('.category-group');
  var cards         = document.querySelectorAll('.dataset-card');
  var totalDatasets = cards.length;
  var activeCategory = 'all';
  var debounceTimer  = null;

  // =========================================================================
  //  Resumable Download Manager
  //  Uses fetch + ReadableStream to download large files with progress.
  //  Falls back to normal <a> click for small files or unsupported browsers.
  // =========================================================================
  var CHUNK_THRESHOLD = 50 * 1024 * 1024; // 50 MB — use resumable for files above this
  var activeDownloads = new Map();

  function parseSize(sizeStr) {
    if (!sizeStr) return 0;
    var m = sizeStr.match(/([\d.]+)\s*(GB|MB|KB|B)/i);
    if (!m) return 0;
    var n = parseFloat(m[1]);
    var u = m[2].toUpperCase();
    if (u === 'GB') return n * 1073741824;
    if (u === 'MB') return n * 1048576;
    if (u === 'KB') return n * 1024;
    return n;
  }

  function formatBytes(bytes) {
    if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB';
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
    if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return bytes + ' B';
  }

  function createProgressUI(row, fileName) {
    var cell = row.querySelector('td:last-child');
    if (!cell) return null;
    cell.innerHTML = '';
    var wrap = document.createElement('div');
    wrap.className = 'dl-progress-wrap';
    wrap.innerHTML =
      '<div class="dl-progress-bar"><div class="dl-progress-fill" style="width:0%"></div></div>' +
      '<span class="dl-progress-text">0%</span>' +
      '<button class="dl-cancel-btn" title="Cancel">✕</button>';
    cell.appendChild(wrap);
    return {
      fill: wrap.querySelector('.dl-progress-fill'),
      text: wrap.querySelector('.dl-progress-text'),
      cancel: wrap.querySelector('.dl-cancel-btn'),
      cell: cell,
      restore: function() {
        cell.innerHTML = '<a href="' + row.dataset.dlUrl + '" class="btn-file-dl">Download</a>';
      }
    };
  }

  function resumableDownload(url, fileName, expectedSize, row) {
    if (activeDownloads.has(fileName)) return;
    var abortCtrl = new AbortController();
    activeDownloads.set(fileName, abortCtrl);
    var ui = createProgressUI(row, fileName);
    if (!ui) { window.open(url, '_blank'); return; }

    ui.cancel.addEventListener('click', function() {
      abortCtrl.abort();
      activeDownloads.delete(fileName);
      ui.text.textContent = 'Cancelled';
      setTimeout(function() { ui.restore(); }, 1500);
    });

    var received = 0;
    var chunks = [];

    fetch(url, { signal: abortCtrl.signal })
      .then(function(resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var total = parseInt(resp.headers.get('content-length'), 10) || expectedSize;
        var reader = resp.body.getReader();

        function pump() {
          return reader.read().then(function(result) {
            if (result.done) return;
            chunks.push(result.value);
            received += result.value.length;
            var pct = total ? Math.min(100, Math.round(received / total * 100)) : 0;
            ui.fill.style.width = pct + '%';
            ui.text.textContent = formatBytes(received) + ' / ' + formatBytes(total) + '  (' + pct + '%)';
            return pump();
          });
        }
        return pump();
      })
      .then(function() {
        var blob = new Blob(chunks);
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        setTimeout(function() {
          URL.revokeObjectURL(a.href);
          document.body.removeChild(a);
        }, 100);
        ui.fill.style.width = '100%';
        ui.fill.style.background = '#22c55e';
        ui.text.textContent = 'Complete!';
        ui.cancel.style.display = 'none';
        activeDownloads.delete(fileName);
        setTimeout(function() { ui.restore(); }, 3000);
      })
      .catch(function(err) {
        activeDownloads.delete(fileName);
        if (err.name === 'AbortError') return;
        ui.fill.style.background = '#ef4444';
        ui.text.textContent = 'Failed — click to retry';
        ui.cancel.style.display = 'none';
        ui.cell.style.cursor = 'pointer';
        ui.cell.onclick = function() {
          ui.cell.onclick = null;
          ui.cell.style.cursor = '';
          resumableDownload(url, fileName, expectedSize, row);
        };
      });
  }

  function blobDownload(url, fileName, row) {
    fetch(url)
      .then(function(resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.blob();
      })
      .then(function(blob) {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        setTimeout(function() { URL.revokeObjectURL(a.href); a.remove(); }, 100);
      })
      .catch(function() {
        window.location.href = url;
      });
  }

  document.addEventListener('click', function(e) {
    var link = e.target.closest('.btn-file-dl');
    if (!link) return;
    var row = link.closest('tr');
    if (!row) return;
    var url = link.getAttribute('href');
    if (!url) return;
    var nameCell = row.querySelector('td:first-child');
    var fileName = nameCell ? nameCell.textContent.trim().split('/').pop() : '';
    var sizeCell = row.querySelectorAll('td')[2];
    var sizeStr = sizeCell ? sizeCell.textContent.trim() : '';
    var expectedSize = parseSize(sizeStr);
    var isRelease = url.indexOf('/releases/download/') !== -1;

    if (isRelease) {
      return;
    }

    e.preventDefault();
    row.dataset.dlUrl = url;

    if (expectedSize > CHUNK_THRESHOLD && window.ReadableStream) {
      resumableDownload(url, fileName, expectedSize, row);
    } else {
      blobDownload(url, fileName, row);
    }
  });

  // --- Category pill click ---
  pills.forEach(function (pill) {
    pill.addEventListener('click', function () {
      activeCategory = pill.dataset.category;
      pills.forEach(function (p) { p.classList.remove('active'); });
      pill.classList.add('active');
      applyFilters();

      if (activeCategory === 'all') {
        history.replaceState(null, '', window.location.pathname);
      } else {
        history.replaceState(null, '', '#' + activeCategory);
      }
    });
  });

  // --- Search ---
  if (searchBox) {
    searchBox.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(applyFilters, 200);
    });
  }

  // --- Combined filter ---
  function applyFilters() {
    var query = searchBox ? searchBox.value.trim().toLowerCase() : '';
    var visible = 0;
    var visibleGroupCats = {};

    cards.forEach(function (card) {
      var cat = card.dataset.category;
      var matchesCat = activeCategory === 'all' || cat === activeCategory;
      var name = (card.dataset.name || '');
      var desc = (card.dataset.description || '');
      var matchesSearch = !query || name.indexOf(query) !== -1 || desc.indexOf(query) !== -1;

      if (matchesCat && matchesSearch) {
        card.style.display = '';
        visible++;
        visibleGroupCats[cat] = true;
      } else {
        card.style.display = 'none';
      }
    });

    groups.forEach(function (group) {
      var cat = group.dataset.group;
      group.style.display = visibleGroupCats[cat] ? '' : 'none';
    });

    if (resultCount) {
      resultCount.textContent = 'Showing ' + visible + ' of ' + totalDatasets + ' datasets';
    }
  }

  function collapseAllExcept(keepCard) {
    cards.forEach(function (c) {
      if (c !== keepCard && c.classList.contains('expanded')) {
        c.classList.remove('expanded');
        var btn = c.querySelector('.expand-card-btn');
        if (btn) btn.textContent = 'Download ▾';
      }
    });
  }

  // --- Expand / Collapse (accordion) ---
  document.addEventListener('click', function (e) {
    var expandBtn = e.target.closest('.expand-card-btn');
    if (expandBtn) {
      var card = expandBtn.closest('.dataset-card');
      if (card) {
        var opening = !card.classList.contains('expanded');
        collapseAllExcept(card);
        card.classList.toggle('expanded');
        expandBtn.textContent = card.classList.contains('expanded') ? 'Download ▴' : 'Download ▾';
        if (opening) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
      return;
    }

    var header = e.target.closest('.dataset-header');
    var toggle = e.target.closest('.expand-toggle');
    if (!header && !toggle) return;

    if (e.target.closest('.dataset-actions') || e.target.closest('a')) return;

    var card = (header || toggle).closest('.dataset-card');
    if (card) {
      var opening = !card.classList.contains('expanded');
      collapseAllExcept(card);
      card.classList.toggle('expanded');
      var btn = card.querySelector('.expand-card-btn');
      if (btn) btn.textContent = card.classList.contains('expanded') ? 'Download ▴' : 'Download ▾';
      if (opening) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  });

  // --- Hash routing ---
  function handleHash() {
    var hash = window.location.hash.replace('#', '').trim();
    if (hash) {
      var matchingPill = document.querySelector('.pill[data-category="' + hash + '"]');
      if (matchingPill) {
        activeCategory = hash;
        pills.forEach(function (p) { p.classList.remove('active'); });
        matchingPill.classList.add('active');
        applyFilters();
        return;
      }
    }
    activeCategory = 'all';
    applyFilters();
  }

  handleHash();
  window.addEventListener('hashchange', handleHash);
})();
