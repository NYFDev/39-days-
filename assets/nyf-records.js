(async function renderNYFRecords() {
  const mounts = document.querySelectorAll('[data-record-feed]');
  if (!mounts.length) return;

  try {
    const response = await fetch('/data/records.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`records ${response.status}`);
    const payload = await response.json();
    const records = Array.isArray(payload.records) ? payload.records : [];

    for (const mount of mounts) {
      const surface = mount.dataset.recordFeed;
      const limit = Number(mount.dataset.recordLimit || 6);
      const visible = records
        .filter((record) => record.visibility === 'public' && record.status === 'published')
        .filter((record) => !surface || record.publication?.surfaces?.includes(surface))
        .sort((a, b) => new Date(b.publishedAt || b.occurredAt) - new Date(a.publishedAt || a.occurredAt))
        .slice(0, limit);

      if (!visible.length) {
        mount.hidden = true;
        continue;
      }

      const fragment = document.createDocumentFragment();
      for (const record of visible) {
        const article = document.createElement('article');
        article.className = 'module record-card';

        const lane = record.taxonomy?.lanes?.[0] || record.kind || 'record';
        const date = new Date(record.publishedAt || record.occurredAt);
        const label = `${lane} / ${Number.isNaN(date.valueOf()) ? '' : date.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}`;
        const url = record.publication?.url || record.source?.url || '#';

        article.innerHTML = `<span>${escapeHTML(label)}</span><h3><a href="${escapeAttribute(url)}">${escapeHTML(record.title)}</a></h3><p>${escapeHTML(record.summary || record.whyItMatters || '')}</p>`;
        fragment.appendChild(article);
      }

      mount.replaceChildren(fragment);
    }
  } catch (error) {
    console.error('NYF record feed unavailable', error);
  }

  function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[char]));
  }

  function escapeAttribute(value) {
    return escapeHTML(value).replace(/`/g, '&#096;');
  }
}());
