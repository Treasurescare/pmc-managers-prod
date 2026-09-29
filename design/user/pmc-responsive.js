/* PMC Tender Board — responsive helpers. Load once, after the app renders.
   1. Adds a menu button that opens the sidebar as a drawer on tablet/phone.
   2. Copies each table's column headers onto its cells (data-label) so tables
      read as labelled cards on phones.
   Works with React/SPA re-renders: a MutationObserver re-applies both. */
(function () {
  var MENU_SVG = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>';

  function addMenuButton() {
    var bar = document.querySelector('.pmc-atop, .pmc-vtop');
    var nav = document.querySelector('.pmc-side, .pmc-lnav');
    if (!bar || !nav || bar.querySelector('.pmc-menu-btn')) return;
    var b = document.createElement('button');
    b.className = 'pmc-menu-btn';
    b.type = 'button';
    b.setAttribute('aria-label', 'Open menu');
    b.setAttribute('aria-expanded', 'false');
    b.innerHTML = MENU_SVG;
    b.addEventListener('click', function () {
      var open = document.documentElement.classList.toggle('pmc-nav-open');
      b.setAttribute('aria-expanded', String(open));
    });
    bar.insertBefore(b, bar.firstChild);
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) close();
    });
  }

  function close() {
    document.documentElement.classList.remove('pmc-nav-open');
    var b = document.querySelector('.pmc-menu-btn');
    if (b) b.setAttribute('aria-expanded', 'false');
  }

  function labelTables() {
    document.querySelectorAll('table.pmc-table').forEach(function (t) {
      var heads = Array.prototype.map.call(t.querySelectorAll('thead th'), function (th) {
        return th.textContent.trim();
      });
      if (!heads.length) return;
      t.querySelectorAll('tbody tr').forEach(function (tr) {
        var i = 0;
        Array.prototype.forEach.call(tr.children, function (td) {
          if (!td.hasAttribute('data-label')) td.setAttribute('data-label', heads[i] || '');
          i += td.colSpan || 1;
        });
      });
    });
  }

  function run() { addMenuButton(); labelTables(); }

  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
  document.addEventListener('click', function (e) {
    if (document.documentElement.classList.contains('pmc-nav-open') &&
        !e.target.closest('.pmc-side, .pmc-lnav, .pmc-menu-btn')) close();
  });
  window.addEventListener('resize', function () { if (window.innerWidth > 1100) close(); });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
  var pending = false;
  new MutationObserver(function () {
    if (pending) return; pending = true;
    requestAnimationFrame(function () { pending = false; run(); });
  }).observe(document.body, { childList: true, subtree: true });
})();
