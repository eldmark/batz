// Carrusel de Inicio: Gödel, Turing y Church. Sin autoavance (no hay nada que pausar).
// Las diapositivas inactivas llevan `inert`: no reciben foco ni salen en el árbol de accesibilidad.
import {person, lifespan} from '../people/people.js';
import {bio} from '../people/bios.js';
import {portrait} from '../people/person.js';

export const SLIDES = ['godel', 'turing', 'church'];

/** Índice siguiente con vuelta circular. */
export function stepIndex(index, delta, count) { return ((index + delta) % count + count) % count; }

/** Gesto táctil: izquierda o derecha solo si es largo y más horizontal que vertical. Devuelve -1, 1 o 0. */
export function swipeDelta(dx, dy, min = 48) {
  if (Math.abs(dx) < min || Math.abs(dx) < Math.abs(dy) * 1.5) return 0;
  return dx < 0 ? 1 : -1;
}

/** Tecla -> nuevo índice, o null si la tecla no navega. */
export function keyIndex(key, index, count) {
  if (key === 'ArrowRight') return stepIndex(index, 1, count);
  if (key === 'ArrowLeft') return stepIndex(index, -1, count);
  if (key === 'Home') return 0;
  if (key === 'End') return count - 1;
  return null;
}

const make = (tag, text, cls) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (cls) el.className = cls; return el; };

export function renderCarousel({arrow}) {
  const n = SLIDES.length;
  const root = make('section', undefined, 'home-banner hs carousel');
  root.dataset.sec = '';
  root.setAttribute('role', 'region'); root.setAttribute('aria-roledescription', 'carrusel');
  root.setAttribute('aria-label', 'Gödel, Turing y Church');
  const title = make('h3', 'Tres lógicos detrás de lo que practicas', 'hs-title'); title.id = 'banner-title'; title.dataset.rv = '';

  const viewport = make('div', undefined, 'carousel-viewport'); viewport.dataset.rv = '';
  viewport.setAttribute('aria-live', 'off');
  const slides = SLIDES.map((slug, i) => {
    const p = person(slug), b = bio(slug);
    const slide = make('div', undefined, 'slide');
    slide.setAttribute('role', 'group'); slide.setAttribute('aria-roledescription', 'diapositiva'); slide.setAttribute('aria-label', `${i + 1} de ${n}`);
    slide.dataset.slug = slug;
    const text = make('div', undefined, 'slide-text');
    const name = make('h4', undefined, 'banner-name'); name.append(p.name, make('span', lifespan(slug)));
    const learn = make('a', `Conocer a ${p.name}`, 'home-link slide-link'); learn.href = b.route; learn.append(arrow());
    text.append(name, make('p', b.carousel.contribution, 'slide-contribution'), make('p', b.carousel.batz, 'banner-link'), learn);
    slide.append(portrait(slug), text);
    viewport.append(slide);
    return slide;
  });

  const live = make('p', undefined, 'sr-only'); live.setAttribute('role', 'status'); live.setAttribute('aria-live', 'polite'); live.setAttribute('aria-atomic', 'true');
  const controls = make('div', undefined, 'carousel-controls'); controls.dataset.rv = '';
  const chevron = (dir) => { const b = make('button', undefined, `carousel-btn ${dir}`); b.type = 'button'; b.setAttribute('aria-label', dir === 'prev' ? 'Diapositiva anterior' : 'Diapositiva siguiente'); const a = arrow(); b.append(a); return b; };
  const prev = chevron('prev'), next = chevron('next');
  const dots = make('div', undefined, 'carousel-dots');
  const dotEls = SLIDES.map((slug, i) => { const d = make('button', undefined, 'carousel-dot'); d.type = 'button'; d.setAttribute('aria-label', `Ir a la diapositiva ${i + 1} de ${n}: ${person(slug).name}`); d.addEventListener('click', () => show(i, true)); dots.append(d); return d; });
  controls.append(prev, dots, next);

  let current = 0;
  function show(i, announce) {
    const moved = i !== current;
    current = i;
    slides.forEach((s, k) => {
      const active = k === current;
      s.classList.toggle('is-active', active); s.classList.toggle('is-before', k < current); s.classList.toggle('is-after', k > current);
      s.inert = !active;
    });
    dotEls.forEach((d, k) => { if (k === current) d.setAttribute('aria-current', 'true'); else d.removeAttribute('aria-current'); });
    if (announce && moved) live.textContent = `Diapositiva ${current + 1} de ${n}: ${person(SLIDES[current]).name}`;
  }
  const go = (i, focusDot = false) => { const had = root.contains(document.activeElement) && slides.some((s) => s.contains(document.activeElement)); show(i, true); if (had || focusDot) dotEls[current].focus(); };
  prev.addEventListener('click', () => go(stepIndex(current, -1, n)));
  next.addEventListener('click', () => go(stepIndex(current, 1, n)));
  root.addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    const to = keyIndex(e.key, current, n);
    if (to === null || to === current) return;
    e.preventDefault(); go(to, true);
  });

  // Deslizar con el dedo o el lápiz; el ratón usa los botones.
  let start = null;
  viewport.addEventListener('pointerdown', (e) => { start = e.pointerType === 'mouse' ? null : {x: e.clientX, y: e.clientY}; });
  viewport.addEventListener('pointerup', (e) => {
    if (!start) return;
    const d = swipeDelta(e.clientX - start.x, e.clientY - start.y); start = null;
    if (d) go(stepIndex(current, d, n));
  });
  viewport.addEventListener('pointercancel', () => { start = null; });

  show(0, false);
  const goal = make('div', undefined, 'banner-goal'); goal.dataset.rv = '';
  const cta = make('a', 'Ir a Practicar', 'home-link'); cta.href = '#/practicar'; cta.append(arrow());
  goal.append(make('p', 'Esta página sirve para practicar: los ejercicios de Practicar, evaluar modelos y demostrar.'), cta);
  root.append(title, viewport, controls, live, goal);
  return root;
}
