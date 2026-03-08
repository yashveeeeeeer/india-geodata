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
