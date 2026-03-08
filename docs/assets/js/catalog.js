/**
 * India Geodata — Catalog Page Interactivity
 * Handles category filtering, search, expand/collapse, and URL hash routing.
 */

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // DOM references
  // ---------------------------------------------------------------------------
  const sidebar       = document.querySelector('.catalog-sidebar');
  const searchBox     = document.querySelector('.search-box');
  const resultCount   = document.querySelector('.result-count');
  const datasetCards  = document.querySelectorAll('.dataset-card');
  const sidebarLinks  = sidebar ? sidebar.querySelectorAll('a[data-category]') : [];
  const totalDatasets = datasetCards.length;

  // Current active category ('all' means show everything)
  let activeCategory = 'all';

  // ---------------------------------------------------------------------------
  // 1. Category Filtering
  // ---------------------------------------------------------------------------

  /**
   * Filter visible dataset cards by category slug.
   * @param {string} category — category slug or 'all'
   */
  function filterByCategory(category) {
    activeCategory = category;

    // Update sidebar active state
    sidebarLinks.forEach(function (link) {
      if (link.dataset.category === category) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // Apply combined filter (category + search)
    applyFilters();
  }

  // Sidebar link click handler
  if (sidebar) {
    sidebar.addEventListener('click', function (e) {
      var link = e.target.closest('a[data-category]');
      if (!link) return;
      e.preventDefault();

      var category = link.dataset.category;
      filterByCategory(category);

      // Update URL hash (omit hash for 'all')
      if (category === 'all') {
        history.replaceState(null, '', window.location.pathname);
      } else {
        history.replaceState(null, '', '#' + category);
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 2. Search Filtering (debounced)
  // ---------------------------------------------------------------------------

  var debounceTimer = null;

  if (searchBox) {
    searchBox.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(applyFilters, 200);
    });
  }

  // ---------------------------------------------------------------------------
  // 3. Combined filter logic
  // ---------------------------------------------------------------------------

  /**
   * Show/hide cards based on the active category and the current search query.
   * Updates the result count element.
   */
  function applyFilters() {
    var query = searchBox ? searchBox.value.trim().toLowerCase() : '';
    var visible = 0;

    datasetCards.forEach(function (card) {
      var matchesCategory =
        activeCategory === 'all' || card.dataset.category === activeCategory;

      var name = (card.dataset.name || '').toLowerCase();
      var desc = (card.dataset.description || '').toLowerCase();
      var matchesSearch = !query || name.indexOf(query) !== -1 || desc.indexOf(query) !== -1;

      if (matchesCategory && matchesSearch) {
        card.style.display = '';
        visible++;
      } else {
        card.style.display = 'none';
      }
    });

    // Update result count
    if (resultCount) {
      resultCount.textContent = 'Showing ' + visible + ' of ' + totalDatasets + ' datasets';
    }
  }

  // ---------------------------------------------------------------------------
  // 4. Card Expand / Collapse
  // ---------------------------------------------------------------------------

  document.addEventListener('click', function (e) {
    // Match clicks on .expand-toggle or .dataset-header
    var header = e.target.closest('.dataset-header');
    var toggle = e.target.closest('.expand-toggle');
    if (!header && !toggle) return;

    var card = (header || toggle).closest('.dataset-card');
    if (!card) return;

    // Toggle expanded state
    card.classList.toggle('expanded');
  });

  // ---------------------------------------------------------------------------
  // 5. URL Hash Routing
  // ---------------------------------------------------------------------------

  function handleHash() {
    var hash = window.location.hash.replace('#', '').trim();
    if (hash) {
      // Check that a sidebar link exists for this category
      var matchingLink = sidebar
        ? sidebar.querySelector('a[data-category="' + hash + '"]')
        : null;
      if (matchingLink) {
        filterByCategory(hash);
        return;
      }
    }
    // Default: show all
    filterByCategory('all');
  }

  // Run on page load
  handleHash();

  // Also listen for hash changes (e.g. browser back/forward)
  window.addEventListener('hashchange', handleHash);
})();
