(function () {
  var nav = document.getElementById('siteNav');
  if (nav && !document.querySelector('.psp-hero')) {
    nav.classList.add('scrolled');
  }
  var toggle = document.getElementById('navToggle');
  var menu   = document.getElementById('mobileMenu');
  var close  = document.getElementById('mobileMenuClose');
  if (!toggle || !menu) return;

  function openMenu() {
    menu.classList.add('is-open');
    menu.setAttribute('aria-hidden', 'false');
    toggle.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
    if (close) close.focus();
  }

  function closeMenu() {
    menu.classList.remove('is-open');
    menu.setAttribute('aria-hidden', 'true');
    toggle.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
    toggle.focus();
  }

  toggle.addEventListener('click', openMenu);
  if (close) close.addEventListener('click', closeMenu);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && menu.classList.contains('is-open')) closeMenu();
  });
}());
