(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  window.toggleSB = function toggleSB() {
    var sidebar = byId('sidebar');
    var overlay = byId('overlay');
    if (sidebar) sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('on');
  };

  window.closeSB = function closeSB() {
    var sidebar = byId('sidebar');
    var overlay = byId('overlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('on');
  };

  window.showLoader = function showLoader() {
    var loader = byId('idloader');
    if (loader) loader.style.display = 'block';
  };

  window.hideLoader = function hideLoader() {
    var loader = byId('idloader');
    if (loader) loader.style.display = 'none';
  };

  window.showMo = function showMo(id) {
    var modal = byId(id);
    if (!modal) {
      if (id === 'login-mo') window.location.href = '/';
      return;
    }
    modal.classList.add('show');
    window.closeSB();
    document.body.style.overflow = 'hidden';
  };

  window.hideMo = function hideMo(id) {
    var modal = byId(id);
    if (modal) modal.classList.remove('show');
    document.body.style.overflow = '';
  };

  window.setLang = function setLang(lang) {
    var en = byId('len');
    var kn = byId('lkn');
    if (en) en.classList.toggle('on', lang === 'en');
    if (kn) kn.classList.toggle('on', lang === 'kn');

    document.querySelectorAll('[data-en][data-kn]').forEach(function (el) {
      el.textContent = lang === 'kn' ? el.getAttribute('data-kn') : el.getAttribute('data-en');
    });
    document.documentElement.lang = lang === 'kn' ? 'kn' : 'en';
  };

  function initSiteNav() {
    document.body.classList.add('has-site-nav');

    var closeButton = byId('sb-close-btn');
    if (closeButton) closeButton.addEventListener('click', window.closeSB);

    document.querySelectorAll('.mo').forEach(function (modal) {
      modal.addEventListener('click', function (event) {
        if (event.target === modal) window.hideMo(modal.id);
      });
    });

    window.setLang('kn');
    window.hideLoader();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSiteNav);
  } else {
    initSiteNav();
  }

  window.addEventListener('load', window.hideLoader);
  window.addEventListener('pageshow', function () {
    window.hideLoader();
    window.closeSB();
  });
}());
