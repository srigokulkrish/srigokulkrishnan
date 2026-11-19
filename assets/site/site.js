// Small progressive enhancements. Every page works without this file.
(() => {
  const root = document.documentElement;

  // Theme toggle: system by default, remembered per browser when chosen.
  const toggle = document.querySelector('.theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      const dark = root.dataset.theme
        ? root.dataset.theme === 'dark'
        : matchMedia('(prefers-color-scheme: dark)').matches;
      root.dataset.theme = dark ? 'light' : 'dark';
      try { localStorage.setItem('theme', root.dataset.theme); } catch (e) {}
    });
  }

  // Header hairline once the page scrolls.
  const header = document.querySelector('.site-header');
  const onScroll = () => header && header.classList.toggle('scrolled', scrollY > 8);
  addEventListener('scroll', onScroll, { passive: true }); onScroll();

  // Mobile menu.
  const menuBtn = document.querySelector('.menu-btn');
  const nav = document.querySelector('.nav');
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', String(open));
    });
    nav.addEventListener('click', (e) => { if (e.target.closest('a')) nav.classList.remove('open'); });
  }

  // Reveal on scroll.
  const items = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
    items.forEach((el) => io.observe(el));
  } else {
    items.forEach((el) => el.classList.add('in'));
  }

  // Work filters.
  const chips = document.querySelectorAll('.chip[data-filter]');
  chips.forEach((chip) => chip.addEventListener('click', () => {
    const f = chip.dataset.filter;
    chips.forEach((c) => c.setAttribute('aria-pressed', String(c === chip)));
    document.querySelectorAll('[data-tags]').forEach((card) => {
      card.hidden = f !== 'all' && !card.dataset.tags.split('|').includes(f);
    });
  }));

  // Lightbox for case-study images.
  const dialog = document.querySelector('.lightbox');
  if (dialog && dialog.showModal) {
    const img = dialog.querySelector('img');
    const cap = dialog.querySelector('p');
    document.addEventListener('click', (e) => {
      const frame = e.target.closest('[data-zoom]');
      if (!frame) return;
      img.src = frame.dataset.zoom;
      img.alt = frame.querySelector('img')?.alt || '';
      cap.textContent = frame.closest('figure')?.querySelector('figcaption')?.textContent || '';
      dialog.showModal();
    });
    dialog.addEventListener('click', (e) => { if (e.target === dialog || e.target.closest('button')) dialog.close(); });
  }

  // Testimonial carousel: arrows move one card; they disable at either end and hide when everything fits.
  const track = document.querySelector('.quotes');
  const navBox = document.querySelector('.carousel-nav');
  if (track && navBox) {
    const prev = navBox.querySelector('[data-carousel-prev]');
    const next = navBox.querySelector('[data-carousel-next]');
    const step = () => {
      const card = track.querySelector('.quote');
      return card ? card.getBoundingClientRect().width + parseFloat(getComputedStyle(track).columnGap || 20) : track.clientWidth;
    };
    const update = () => {
      const max = track.scrollWidth - track.clientWidth;
      navBox.hidden = max <= 4;
      prev.disabled = track.scrollLeft <= 4;
      next.disabled = track.scrollLeft >= max - 4;
    };
    prev.addEventListener('click', () => track.scrollBy({ left: -step() }));
    next.addEventListener('click', () => track.scrollBy({ left: step() }));
    track.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight') { e.preventDefault(); track.scrollBy({ left: step() }); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); track.scrollBy({ left: -step() }); }
    });
    track.addEventListener('scroll', update, { passive: true });
    addEventListener('resize', update);
    update();
  }

  const year = document.querySelector('[data-year]');
  if (year) year.textContent = new Date().getFullYear();
})();
