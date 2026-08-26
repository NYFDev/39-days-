(() => {
  'use strict';

  const CONFIG = window.NYF_FUNNEL || {};
  const endpoint = CONFIG.endpoint || '';
  const consentVersion = CONFIG.consentVersion || 'v1';
  const contentId = document.documentElement.dataset.contentId || document.body.dataset.contentId || 'site';
  const assetId = new URLSearchParams(location.search).get('asset_id');
  const campaignId = new URLSearchParams(location.search).get('campaign_id') || contentId;

  const randomId = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`);
  const session = sessionStorage.getItem('nyf_session_id') || randomId();
  sessionStorage.setItem('nyf_session_id', session);

  const consented = () => localStorage.getItem('nyf_analytics_consent') === consentVersion;
  const anonymousId = () => {
    let id = localStorage.getItem('nyf_anonymous_id');
    if (!id) {
      id = randomId();
      localStorage.setItem('nyf_anonymous_id', id);
    }
    return id;
  };

  const params = new URLSearchParams(location.search);
  const source = params.get('utm_source') || (document.referrer ? (() => { try { return new URL(document.referrer).hostname; } catch (_) { return 'referral'; } })() : 'direct');
  const medium = params.get('utm_medium') || (document.referrer ? 'referral' : 'direct');

  function event(name, properties = {}) {
    if (!endpoint || !consented()) return false;
    const payload = {
      event_id: randomId(),
      event_name: name,
      occurred_at: new Date().toISOString(),
      anonymous_id: anonymousId(),
      subscriber_id: null,
      session_id: session,
      content_id: contentId,
      asset_id: assetId,
      campaign_id: campaignId,
      source,
      medium,
      landing_path: location.pathname,
      properties,
      consent_version: consentVersion
    };
    const body = JSON.stringify(payload);
    if (navigator.sendBeacon) return navigator.sendBeacon(endpoint, new Blob([body], {type: 'application/json'}));
    fetch(endpoint, {method: 'POST', headers: {'content-type': 'application/json'}, body, keepalive: true}).catch(() => {});
    return true;
  }

  function grantConsent() {
    localStorage.setItem('nyf_analytics_consent', consentVersion);
    event('page_view', {consent_granted: true});
  }

  function revokeConsent() {
    localStorage.removeItem('nyf_analytics_consent');
    localStorage.removeItem('nyf_anonymous_id');
  }

  window.NYFFunnel = {event, grantConsent, revokeConsent, consented};

  if (consented()) event('page_view');

  document.addEventListener('click', e => {
    const target = e.target.closest('[data-funnel-event]');
    if (!target) return;
    event(target.dataset.funnelEvent, {
      target: target.dataset.funnelTarget || target.getAttribute('href') || null
    });
  });

  const depthSeen = new Set();
  let engaged = false;
  const started = Date.now();
  addEventListener('scroll', () => {
    if (!consented()) return;
    const doc = document.documentElement;
    const max = Math.max(1, doc.scrollHeight - innerHeight);
    const pct = Math.min(100, Math.round((scrollY / max) * 100));
    [25, 50, 75, 100].forEach(mark => {
      if (pct >= mark && !depthSeen.has(mark)) {
        depthSeen.add(mark);
        event('article_depth', {bucket: mark});
      }
    });
    if (!engaged && Date.now() - started >= 30000 && pct >= 25) {
      engaged = true;
      event('article_engaged', {threshold_seconds: 30, minimum_depth: 25});
    }
  }, {passive: true});
})();
