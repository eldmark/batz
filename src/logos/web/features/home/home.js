import {hashFor} from '../../app/navigation.js';

// Inicio: tarjetas de las cuatro herramientas y tres ejercicios progresivos.
// Cada ejercicio es un dato; quien lo ejecuta (app.js) abre el módulo y carga sus entradas.
export const CARDS = [
  {route: 'evaluate', title: 'Evaluar modelo', purpose: 'Comprueba si una fórmula es verdadera en una interpretación que tú defines.', example: '∀x(P(x) → Q(x)) en un modelo explícito'},
  {route: 'prove', title: 'Demostrar', purpose: 'Pregunta si una conclusión se sigue de unas premisas, en todos los modelos.', example: '∀x(P(x) → Q(x)), P(a) ⊢ Q(a)'},
  {route: 'notebook', title: 'Cuadernos', purpose: 'Haz preguntas a tus textos y obtén respuestas con cita, prueba o contramodelo.', example: '«¿Juan aprueba?»'},
  {route: 'dictionary', title: 'Diccionario', purpose: 'Consulta palabras, formas, categorías y símbolos; añade las que falten.', example: '«abandonar»'},
];
export const EXERCISES = [
  {id: 'evaluate', route: 'evaluate', title: '1 · Evalúa una fórmula', does: 'Carga D = {0, 1}, P = {0}, Q = {1} y ∀x (P(x) → Q(x)), y te deja en el paso de la fórmula.', watch: 'Pulsa «Verificar» y observa por qué es falsa: x = 0 cumple P y no cumple Q.'},
  {id: 'prove', route: 'prove', title: '2 · Demuestra una consecuencia', does: 'Carga las premisas ∀x (Humano(x) → Mortal(x)) y Humano(socrates), con la conclusión Mortal(socrates).', watch: 'Pulsa «Buscar prueba» y sigue cada línea Fitch con su regla.'},
  {id: 'notebook', route: 'notebook', title: '3 · Consulta unas fuentes', does: 'Crea el cuaderno de ejemplo con textos en español.', watch: 'Pregunta «¿Juan aprueba?» y abre la cita que respalda la respuesta.'},
];

// Banner: dos retratos de dominio público (ver img/CREDITOS.md). Si falta una imagen, queda la tarjeta con iniciales.
export const BANNER = {
  title: 'Dos lógicos detrás de lo que practicas',
  people: [
    {id: 'godel', name: 'Kurt Gödel', years: '1906–1978', initials: 'KG', src: '/img/godel.jpg',
     alt: 'Retrato fotográfico de Kurt Gödel, joven, con gafas redondas, traje y corbata a cuadros.',
     credit: 'Retrato, h. 1925. Dominio público (Wikimedia Commons).', page: 'https://commons.wikimedia.org/wiki/File:Young_Kurt_G%C3%B6del_as_a_student_in_1925.jpg',
     facts: ['Teorema de completitud (1929): en lógica de primer orden, lo verdadero en todos los modelos se puede demostrar.',
             'Teoremas de incompletitud (1931): en sistemas formales suficientemente ricos hay enunciados que no se pueden ni demostrar ni refutar.'],
     link: '«Evaluar» trabaja con modelos (semántica) y «Demostrar» con pruebas (sintaxis); la completitud es el puente entre ambos.'},
    {id: 'turing', name: 'Alan Turing', years: '1912–1954', initials: 'AT', src: '/img/turing.jpg',
     alt: 'Retrato fotográfico de Alan Turing con la mirada hacia un lado, de chaqueta de tweed, camisa y corbata oscura.',
     credit: 'Retrato de Elliott & Fry, 1951. Dominio público (Wikimedia Commons).', page: 'https://commons.wikimedia.org/wiki/File:Alan_Turing_(1951).jpg',
     facts: ['1936: la máquina de Turing y la indecidibilidad del problema de la parada.',
             'Junto con Church, de ahí se sigue que la validez en lógica de primer orden es indecidible.'],
     link: 'Por eso una búsqueda puede quedar «inconclusa», y eso no equivale a falso.'},
  ],
  goal: 'Esta página sirve para practicar: los ejercicios de Practicar, evaluar modelos y demostrar.',
};

const THREAD_NS = 'http://www.w3.org/2000/svg';
function thread(cls, d, box) {
  const svg = document.createElementNS(THREAD_NS, 'svg');
  svg.setAttribute('class', cls); svg.setAttribute('viewBox', box); svg.setAttribute('aria-hidden', 'true'); svg.setAttribute('focusable', 'false');
  svg.setAttribute('preserveAspectRatio', 'none');
  const path = document.createElementNS(THREAD_NS, 'path');
  path.setAttribute('d', d);
  svg.append(path);
  return svg;
}

/** Del teorema al ejercicio: cada tarjeta carga en Demostrar un caso que ilustra un resultado de Gödel o de Turing. */
export const CONNECTIONS = [
  {id: 'goedel-completitud', route: 'prove', who: 'Gödel · completitud (1929)', title: 'Lo que se sigue, se demuestra',
   does: 'Carga ∀x (Humano(x) → Mortal(x)), Humano(socrates) ⊢ Mortal(socrates).',
   watch: 'Pulsa «Buscar prueba»: Bat’z halla la derivación y el verificador la acepta. Si en todos los modelos vale, hay prueba: ese es el puente entre Evaluar y Demostrar.',
   proof: {premises: '∀x (Humano(x) → Mortal(x))\nHumano(socrates)', conclusion: 'Mortal(socrates)', constants: 'socrates'}},
  {id: 'goedel-contramodelo', route: 'prove', who: 'Tarski y Gödel · modelos', title: 'Lo que no se sigue, tiene un contramodelo',
   does: 'Carga ∀x ∃y Ama(x, y) ⊢ ∃y ∀x Ama(x, y): cambiar el orden de ∀ y ∃ cambia el significado.',
   watch: 'Pulsa «Buscar prueba»: no hay prueba, y Bat’z muestra un modelo concreto donde las premisas son verdaderas y la conclusión falsa. Ábrelo en Evaluar.',
   proof: {premises: '∀x ∃y Ama(x, y)', conclusion: '∃y ∀x Ama(x, y)', constants: ''}},
  {id: 'turing-inconclusa', route: 'prove', who: 'Turing y Church · indecidibilidad (1936)', title: 'A veces la búsqueda no decide',
   does: 'Carga transitividad, irreflexividad y serialidad de R ⊢ ∃x ∀y ¬R(y, x).',
   watch: 'Pulsa «Buscar prueba»: queda «Búsqueda inconclusa». No decide la consecuencia: no es «falsa» ni «demostrada». No existe un algoritmo que decida toda consecuencia de primer orden.',
   proof: {premises: '∀x ∀y ∀z ((R(x, y) ∧ R(y, z)) → R(x, z))\n∀x ¬R(x, x)\n∀x ∃y R(x, y)', conclusion: '∃x ∀y ¬R(y, x)', constants: ''}},
];

export function renderBanner(make) {
  const section = make('section', undefined, 'home-banner');
  section.setAttribute('aria-labelledby', 'banner-title');
  const title = make('h3', BANNER.title, 'banner-title'); title.id = 'banner-title';
  const grid = make('div', undefined, 'banner-grid');
  BANNER.people.forEach((p, i) => {
    const card = make('article', undefined, `banner-person banner-${p.id}`);
    const fig = make('figure', undefined, 'banner-portrait');
    const frame = make('div', undefined, 'banner-frame');
    const initials = make('span', p.initials, 'banner-initials'); initials.setAttribute('aria-hidden', 'true');
    const img = make('img'); img.src = p.src; img.alt = p.alt; img.width = 480; img.height = p.id === 'godel' ? 636 : 640; img.loading = 'lazy'; img.decoding = 'async';
    img.addEventListener('error', () => { img.remove(); frame.classList.add('is-missing'); frame.setAttribute('role', 'img'); frame.setAttribute('aria-label', `Retrato de ${p.name} no disponible`); });
    frame.append(initials, img);
    const cap = make('figcaption', undefined, 'banner-credit');
    const a = make('a', p.credit); a.href = p.page; a.target = '_blank'; a.rel = 'noopener noreferrer';
    cap.append(a); fig.append(frame, cap);
    const body = make('div', undefined, 'banner-text');
    const h = make('h4', undefined, 'banner-name'); h.append(p.name, make('span', p.years));
    const facts = make('ul'); for (const f of p.facts) facts.append(make('li', f));
    body.append(h, facts, make('p', p.link, 'banner-link'));
    card.append(fig, body);
    grid.append(card);
    if (i === 0) grid.append(thread('banner-thread banner-thread-h', 'M0 50 C 25 10, 40 90, 60 50 S 85 20, 100 50', '0 0 100 100'), thread('banner-thread banner-thread-v', 'M50 0 C 10 25, 90 40, 50 60 S 20 85, 50 100', '0 0 100 100'));
  });
  const goal = make('div', undefined, 'banner-goal');
  const cta = make('a', 'Ir a Practicar', 'button primary'); cta.href = '#/practicar';
  goal.append(thread('banner-thread banner-thread-goal', 'M0 50 C 30 0, 60 100, 100 50', '0 0 100 100'), make('p', BANNER.goal), cta);
  section.append(title, grid, goal);
  return section;
}

export function renderHome(host, {go, runExercise}) {
  host.replaceChildren();
  const make = (tag, text, cls) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (cls) el.className = cls; return el; };
  const cards = make('ul', undefined, 'home-cards');
  for (const card of CARDS) {
    const item = make('li'), link = make('a', undefined, 'home-card');
    link.href = hashFor(card.route);
    link.append(make('strong', card.title), make('span', card.purpose), make('code', card.example));
    item.append(link); cards.append(item);
  }
  const list = make('ol', undefined, 'home-exercises');
  for (const ex of EXERCISES) {
    const item = make('li'), button = make('button', 'Abrir y cargar ejemplo', 'button primary'); button.type = 'button';
    button.addEventListener('click', () => runExercise(ex));
    item.append(make('strong', ex.title), make('p', ex.does), make('p', ex.watch, 'hint'), button);
    list.append(item);
  }
  const bridge = make('section', undefined, 'home-bridge'); bridge.setAttribute('aria-labelledby', 'home-bridge-title');
  const bridgeTitle = make('h3', 'Practica lo que probaron Gödel y Turing'); bridgeTitle.id = 'home-bridge-title';
  const bridgeList = make('ul', undefined, 'home-bridge-list');
  for (const item of CONNECTIONS) {
    const li = make('li'), button = make('button', 'Cargar en Demostrar', 'button secondary'); button.type = 'button';
    button.addEventListener('click', () => runExercise(item));
    li.append(make('span', item.who, 'bridge-who'), make('strong', item.title), make('p', item.does), make('p', item.watch, 'hint'), button);
    bridgeList.append(li);
  }
  bridge.append(bridgeTitle, bridgeList);
  host.append(renderBanner(make), bridge, cards, make('h3', 'Empieza con un ejemplo'), make('p', 'Tres ejercicios progresivos. Cargar uno reemplaza lo que haya en esa herramienta y te avisa antes.', 'hint'), list);
}
