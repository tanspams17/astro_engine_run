/*
 * Cookie consent banner for the Google Ads tag (Consent Mode v2).
 *
 * Each page's <head> sets every consent type to "denied" (or to the stored
 * choice) before gtag.js loads, so no ad cookies are set until the visitor
 * accepts here. The choice lives in localStorage under arvelos_consent
 * ("granted" | "denied"); window.arvelosConsent.open() reopens the banner
 * (used by the footer's "Cookie settings" link).
 */
(function () {
  var KEY = 'arvelos_consent';

  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }

  function apply(choice) {
    try { localStorage.setItem(KEY, choice); } catch (e) {}
    var v = choice === 'granted' ? 'granted' : 'denied';
    if (typeof window.gtag === 'function') {
      window.gtag('consent', 'update', {
        ad_storage: v, ad_user_data: v, ad_personalization: v,
        analytics_storage: v
      });
    }
    close();
  }

  var el = null;

  function close() {
    if (el && el.parentNode) el.parentNode.removeChild(el);
    el = null;
  }

  function open() {
    if (el) return;
    var css = document.createElement('style');
    css.textContent =
      '.arv-consent{position:fixed;left:16px;right:16px;bottom:16px;z-index:9999;' +
      'max-width:560px;margin:0 auto;padding:16px 18px;border-radius:12px;' +
      'background:#1c1a3e;color:#f5eedc;border:1px solid rgba(212,146,10,0.55);' +
      'box-shadow:0 8px 30px rgba(0,0,0,0.35);font:14px/1.5 Inter,-apple-system,sans-serif}' +
      '.arv-consent p{margin:0 0 12px}' +
      '.arv-consent a{color:#f0c04a}' +
      '.arv-consent .arv-btns{display:flex;gap:10px;flex-wrap:wrap}' +
      '.arv-consent button{flex:1 1 120px;padding:9px 14px;border-radius:8px;cursor:pointer;' +
      'font:600 14px Inter,-apple-system,sans-serif;border:1px solid rgba(212,146,10,0.55)}' +
      '.arv-consent .arv-accept{background:#d4920a;color:#0e1535;border-color:#d4920a}' +
      '.arv-consent .arv-reject{background:transparent;color:#f5eedc}';
    el = document.createElement('div');
    el.className = 'arv-consent';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-label', 'Cookie consent');
    el.appendChild(css);
    el.insertAdjacentHTML('beforeend',
      '<p>We use Google Ads cookies to measure which ads bring people to Arvelos. ' +
      'Your birth details are never shared with them. ' +
      '<a href="/privacy.html#cookies">Privacy policy</a></p>' +
      '<div class="arv-btns">' +
      '<button type="button" class="arv-reject">Reject</button>' +
      '<button type="button" class="arv-accept">Accept</button></div>');
    el.querySelector('.arv-accept').onclick = function () { apply('granted'); };
    el.querySelector('.arv-reject').onclick = function () { apply('denied'); };
    document.body.appendChild(el);
  }

  window.arvelosConsent = { open: open };

  function init() { if (!stored()) open(); }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
