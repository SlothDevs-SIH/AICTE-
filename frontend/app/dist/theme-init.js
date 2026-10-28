// Light by default (matches the design reference); dark only when the user switches it.
try {
  if (localStorage.getItem('theme') === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
} catch (e) {}
