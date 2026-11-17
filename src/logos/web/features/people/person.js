import {person, initials, lifespan} from './people.js';
import {bio} from './bios.js';

const make = (tag, text, cls) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (cls) el.className = cls; return el; };
const link = (text, href, cls) => { const a = make('a', text, cls); a.href = href; return a; };

/** Retrato con su crédito visible; sin imagen libre, tarjeta tipográfica con el monograma y una nota. */
export function portrait(slug, {large = true} = {}) {
  const p = person(slug), b = bio(slug);
  const fig = make('figure', undefined, `portrait${large ? ' portrait-lg' : ''}`);
  const frame = make('div', undefined, 'portrait-frame');
  const caption = make('figcaption', undefined, 'portrait-credit');
  const placeholder = () => {
    frame.classList.add('is-placeholder');
    frame.setAttribute('role', 'img'); frame.setAttribute('aria-label', `Monograma de ${p.name}; retrato no disponible con licencia libre`);
    const mono = make('span', initials(slug), 'portrait-mono'); mono.setAttribute('aria-hidden', 'true');
    const lambda = make('span', slug === 'church' ? 'λ' : '', 'portrait-glyph'); lambda.setAttribute('aria-hidden', 'true');
    frame.replaceChildren(lambda, mono);
    caption.replaceChildren('Retrato no disponible con licencia libre');
  };
  if (p.image) {
    const img = make('img'); img.src = p.image; img.alt = b.alt; img.width = 480; img.height = 640; img.decoding = 'async';
    img.addEventListener('error', () => { placeholder(); });
    frame.append(img);
    const a = link(p.credit, p.creditUrl); a.target = '_blank'; a.rel = 'noopener noreferrer';
    caption.append(a);
  } else placeholder();
  fig.append(frame, caption);
  return fig;
}

/** Página de una persona. `runExercise` y `connections` son los de Inicio: cargan el ejemplo en Demostrar. */
export function renderPerson(host, slug, {runExercise, connections = []} = {}) {
  host.replaceChildren();
  const p = person(slug), b = bio(slug);
  if (!p || !b) return;

  const nav = make('nav', undefined, 'person-nav'); nav.setAttribute('aria-label', 'Volver');
  nav.append(link('← Volver al inicio', '#/inicio', 'home-link'), link('Ver la historia en Aprender', '#/aprender', 'home-link'));

  const head = make('header', undefined, 'person-head');
  const info = make('div', undefined, 'person-info');
  info.append(make('p', lifespan(slug), 'person-years'), make('p', b.lede, 'person-lede'));
  const facts = make('dl', undefined, 'person-facts');
  const row = (k, v) => { if (v) facts.append(make('dt', k), make('dd', v)); };
  row('Nació', `${p.born}, ${b.birthplace}`);
  row('Murió', b.deathplace ? `${p.died}, ${b.deathplace}` : String(p.died));
  info.append(facts);
  head.append(portrait(slug), info);

  const section = (title, id) => { const s = make('section', undefined, 'person-sec'); s.setAttribute('aria-labelledby', id); const h = make('h2', title, 'person-h'); h.id = id; s.append(h); return s; };
  const list = (tag, items, cls) => { const l = make(tag, undefined, cls); for (const i of items) l.append(i); return l; };
  const dated = (items) => items.map(({year, text}) => { const li = make('li'); li.append(make('span', year, 'dated-y'), make('span', text, 'dated-t')); return li; });

  const bioSec = section('Biografía', 'pp-bio');
  for (const paragraph of b.bio) bioSec.append(make('p', paragraph));

  const contrib = section('Sus aportes', 'pp-contrib');
  contrib.append(list('ul', dated(b.contributions), 'dated'));

  const batz = section('Dónde lo ves en Bat’z', 'pp-batz');
  const batzList = make('ul', undefined, 'person-batz');
  for (const item of b.batz) { const li = make('li'); li.append(make('p', item.text), link(item.label, item.href, 'home-link')); batzList.append(li); }
  batz.append(batzList);
  const connection = connections.find((c) => c.id === b.exercise.id);
  if (connection && runExercise) {
    const button = make('button', b.exercise.label, 'button secondary'); button.type = 'button';
    button.addEventListener('click', () => runExercise(connection));
    batz.append(button);
  }

  const time = section('Cronología', 'pp-time');
  time.append(list('ol', dated(b.timeline), 'dated timeline'));

  const read = section('Para leer más', 'pp-read');
  read.append(list('ul', b.reading.map((t) => make('li', t)), 'reading'));

  const more = make('nav', undefined, 'person-more'); more.setAttribute('aria-label', 'Otras personas');
  more.append(make('span', 'Ver también'));
  for (const other of b.related) more.append(link(person(other).name, bio(other).route, 'home-link'));

  host.append(nav, head, bioSec, contrib, batz, time, read, more);
}
