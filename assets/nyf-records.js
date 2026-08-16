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
        .filter((record) => !surface || record.outputs?.some((output) => output.surface === surface))
        .sort((a, b) => new Date(b.source?.publishedAt || b.observedAt) - new Date(a.source?.publishedAt || a.observedAt))
        .slice(0, limit);

      if (!visible.length) {
        mount.hidden = true;
        continue;
      }

      const fragment = document.createDocumentFragment();
      for (const record of visible) {
        const article = document.createElement('article');
        article.className = 'module record-card';

        const lane = record.lanes?.[0] || record.kind || 'record';
        const date = new Date(record.source?.publishedAt || record.observedAt);
        const label = `${lane} / ${Number.isNaN(date.valueOf()) ? '' : date.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}`;
        const output = record.outputs?.find((candidate) => !surface || candidate.surface === surface);
        const url = output?.publishedUrl || record.source?.canonicalUrl || '#';

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
