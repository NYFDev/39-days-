(function migrateCachedOperationalHub() {
  const isOldHub = !document.querySelector('[data-menu]') || /39 DAYS — NYF Holdings/i.test(document.title);
  if (!isOldHub) return;
  window.location.replace('/?release=20260814b');
}());
