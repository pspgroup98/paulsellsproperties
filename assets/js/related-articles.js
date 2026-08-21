(function () {
  'use strict';

  var section = document.querySelector('.post-more[data-slug]');
  if (!section) return;

  var currentSlug = section.getAttribute('data-slug');
  var grid = section.querySelector('#relatedArticlesGrid');
  if (!grid) return;

  // Category affinity groups — articles in the same group score higher as related
  var CATEGORY_GROUPS = {
    "Buyer's Guide":          ["Buyer's Guide", "Buyer Strategy", "Condo / HOA"],
    "Buyer Strategy":         ["Buyer Strategy", "Buyer's Guide"],
    "Market Analysis":        ["Market Analysis", "Buyer's Guide", "Buyer Strategy"],
    "Landlord & Rental Laws": ["Landlord & Rental Laws", "Real Estate Investing", "Investor Strategy"],
    "Real Estate Investing":  ["Real Estate Investing", "Landlord & Rental Laws", "Investor Strategy"],
    "Investor Strategy":      ["Investor Strategy", "Real Estate Investing", "Landlord & Rental Laws"],
    "Condo / HOA":            ["Condo / HOA", "Buyer's Guide"],
    "Seller Strategy":        ["Seller Strategy", "Real Estate Investing", "Investor Strategy"],
    "Market Analysis":        ["Market Analysis", "Buyer's Guide", "Buyer Strategy"]
  };

  function isPublished(article) {
    // Only surface articles that are explicitly marked published.
    // Approved-but-future and draft articles are excluded.
    return article.status === 'published';
  }

  function score(article, current) {
    var s = 0;
    if (!current) return s;
    var affinity = CATEGORY_GROUPS[current.category] || [current.category];

    if (article.category === current.category) s += 4;
    else if (affinity.indexOf(article.category) !== -1) s += 2;

    if (current.tags && article.tags) {
      current.tags.forEach(function (t) {
        if (article.tags.indexOf(t) !== -1) s += 1;
      });
    }

    if (current.audience && article.audience) {
      current.audience.forEach(function (a) {
        if (article.audience.indexOf(a) !== -1) s += 1;
      });
    }

    return s;
  }

  function renderCards(articles) {
    if (!articles.length) {
      grid.innerHTML = '<p class="post-more-empty">More articles coming soon.</p>';
      return;
    }
    grid.innerHTML = articles.map(function (a) {
      return '<a href="' + a.slug + '.html" class="more-card">' +
        '<span class="more-card-cat">' + escHtml(a.category) + '</span>' +
        '<h3 class="more-card-title">' + escHtml(a.title) + '</h3>' +
        '<span class="more-card-date">' + escHtml(a.date_display || '') + '</span>' +
        '</a>';
    }).join('');
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Path from /blog/ to /content-system/article-index.json
  var indexUrl = '../content-system/article-index.json';

  var xhr = new XMLHttpRequest();
  xhr.open('GET', indexUrl, true);
  xhr.onreadystatechange = function () {
    if (xhr.readyState !== 4) return;
    if (xhr.status !== 200) {
      grid.innerHTML = '<p class="post-more-empty"><a href="index.html">View all articles &rarr;</a></p>';
      return;
    }
    try {
      var allArticles = JSON.parse(xhr.responseText);

      // Filter to published articles only — never surface drafts or future-scheduled content
      var published = allArticles.filter(isPublished);

      var current    = null;
      var candidates = [];

      published.forEach(function (a) {
        if (a.slug === currentSlug) { current = a; }
        else { candidates.push(a); }
      });

      // Score every candidate, then sort
      candidates = candidates.map(function (a) {
        return { article: a, s: score(a, current) };
      }).sort(function (x, y) {
        if (y.s !== x.s) return y.s - x.s;
        // Tiebreak by recency (published_at preferred, fall back to date_iso)
        var ay = y.article.published_at || y.article.date_iso || '';
        var ax = x.article.published_at || x.article.date_iso || '';
        return ay.localeCompare(ax);
      }).map(function (o) { return o.article; });

      renderCards(candidates.slice(0, 3));
    } catch (e) {
      grid.innerHTML = '';
    }
  };
  xhr.send();
})();
