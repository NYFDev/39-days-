// NYF Holdings public release 2026-08-14
const operationsFragments = new Set(['#crm', '#command', '#daily', '#activity', '#intelligence', '#evidence', '#financial']);
if (operationsFragments.has(window.location.hash.toLowerCase()) && window.location.pathname === '/') {
  window.location.replace(`/operations/${window.location.hash}`);
}

const menuButton = document.querySelector('[data-menu]');
const navigation = document.querySelector('[data-nav]');

function closeMenu() {
  if (!menuButton || !navigation) return;
  menuButton.setAttribute('aria-expanded', 'false');
  navigation.classList.remove('is-open');
}

if (menuButton && navigation) {
  menuButton.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') === 'true';
    menuButton.setAttribute('aria-expanded', String(!open));
    navigation.classList.toggle('is-open', !open);
  });

  navigation.addEventListener('click', event => {
    if (event.target.closest('a')) closeMenu();
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 900) closeMenu();
  });
}

document.querySelectorAll('[data-year]').forEach(node => {
  node.textContent = new Date().getFullYear();
});

const revealItems = document.querySelectorAll('[data-reveal]');
if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.12 });
  revealItems.forEach(item => observer.observe(item));
} else {
  revealItems.forEach(item => item.classList.add('is-visible'));
}

const searchForm = document.querySelector('[data-search-form]');
const searchInput = document.querySelector('[data-search-input]');
const searchResults = document.querySelector('[data-search-results]');
const searchStatus = document.querySelector('[data-search-status]');

if (searchForm && searchInput && searchResults && searchStatus) {
  const normal = value => String(value || '').toLowerCase().normalize('NFKD').replace(/[^a-z0-9\s-]/g, ' ');
  const makeResult = item => {
    const link = document.createElement('a');
    link.className = 'search-result';
    link.href = item.url;
    const section = document.createElement('span');
    section.className = 'result-section';
    section.textContent = item.section;
    const copy = document.createElement('div');
    const title = document.createElement('h2');
    title.textContent = item.title;
    const description = document.createElement('p');
    description.textContent = item.description;
    copy.append(title, description);
    const arrow = document.createElement('span');
    arrow.className = 'arrow';
    arrow.setAttribute('aria-hidden', 'true');
    arrow.textContent = '↗';
    link.append(section, copy, arrow);
    return link;
  };

  fetch('/search-index.json', { cache: 'no-store' })
    .then(response => {
      if (!response.ok) throw new Error('Search index unavailable');
      return response.json();
    })
    .then(index => {
      const render = rawQuery => {
        const query = normal(rawQuery).trim();
        const tokens = query.split(/\s+/).filter(Boolean);
        const ranked = index.map(item => {
          const title = normal(item.title);
          const section = normal(item.section);
          const description = normal(item.description);
          const keywords = normal((item.keywords || []).join(' '));
          const score = tokens.reduce((total, token) => total
            + (title.includes(token) ? 12 : 0)
            + (section.includes(token) ? 7 : 0)
            + (keywords.includes(token) ? 5 : 0)
            + (description.includes(token) ? 3 : 0), 0);
          const matches = !tokens.length || tokens.every(token => `${title} ${section} ${description} ${keywords}`.includes(token));
          return { item, score, matches };
        }).filter(row => row.matches).sort((a, b) => b.score - a.score || a.item.title.localeCompare(b.item.title));

        searchResults.replaceChildren();
        ranked.forEach(row => searchResults.append(makeResult(row.item)));
        if (!ranked.length) {
          const empty = document.createElement('p');
          empty.className = 'search-empty';
          empty.textContent = 'No public page matches that search yet.';
          searchResults.append(empty);
        }
        searchStatus.textContent = query ? `${ranked.length} public result${ranked.length === 1 ? '' : 's'} for “${rawQuery.trim()}”.` : `${ranked.length} public pages in the index.`;
        const url = new URL(window.location.href);
        query ? url.searchParams.set('q', rawQuery.trim()) : url.searchParams.delete('q');
        history.replaceState(null, '', url);
      };

      const initialQuery = new URLSearchParams(window.location.search).get('q') || '';
      searchInput.value = initialQuery;
      render(initialQuery);
      searchForm.addEventListener('submit', event => { event.preventDefault(); render(searchInput.value); });
      searchInput.addEventListener('input', () => render(searchInput.value));
    })
    .catch(() => {
      searchStatus.textContent = 'The public directory is shown below; live filtering is temporarily unavailable.';
    });
}

