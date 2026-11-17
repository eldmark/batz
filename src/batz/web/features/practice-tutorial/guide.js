// «Cómo se juega» (panel del inicio) y diálogo de reglas con la chuleta. Solo DOM; los datos
// de las reglas llegan del servidor (bank.rules) y los ejemplos de rules-guide.json.
const GUIDE_URL = '/features/practice-tutorial/rules-guide.json';
let guidePromise = null;
export function loadGuide(fetcher = fetch) {
  guidePromise ||= fetcher(GUIDE_URL).then(r => { if (!r.ok) throw new Error('sin chuleta'); return r.json(); })
    .catch(err => { guidePromise = null; throw err; });
  return guidePromise;
}

const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
const button = (text, cls, action) => { const b = el('button', `pg-button ${cls || ''}`, text); b.type = 'button'; b.addEventListener('click', action); return b; };

export const QUICK_RULES = [
  ['Llega al objetivo', 'Cada ejercicio fija una fórmula objetivo. Ganas cuando tu prueba la alcanza y queda verificada.'],
  ['Una línea a la vez', 'Una línea es una regla, las líneas que citas y la fórmula nueva. «Comprobar paso» la verifica.'],
  ['El orden importa', 'Cita las líneas en el orden que pide la regla: →E pide primero A → B y después A.'],
  ['Descarga lo que supongas', 'Una hipótesis abierta no gana. Descárgala con →I, ¬I, RAA, ∨E o ∃E, salvo que sea una premisa.'],
  ['Sin presión', 'Sin reloj ni vidas. Las pistas y la solución no restan nada. Tu progreso queda solo en este navegador.'],
];

export const GAME_RULES = [
  ['El objetivo', 'Llegar a la fórmula objetivo con una prueba verificada: la última línea es el objetivo y ya no depende de ninguna hipótesis abierta.'],
  ['Qué es una línea', 'Cada línea tiene tres partes: la regla que usas, las líneas anteriores que citas y la fórmula nueva que obtienes. Las premisas son las primeras líneas y ya vienen dadas.'],
  ['Una línea a la vez', 'Añades una línea y pulsas «Comprobar paso». El servidor la verifica. Si falla, no se añade nada y se te explica por qué; lo que escribiste se conserva.'],
  ['El orden de las referencias importa', 'Las líneas se citan en el orden que pide la regla. →E pide primero A → B y luego A; ∧I pone a la izquierda la primera que citas; ¬E pide A y después ¬A. Con otro orden la regla no se aplica.'],
  ['Una hipótesis abierta no gana', 'Suponer algo (Hipótesis) abre un ámbito temporal. Si la última línea depende de una hipótesis abierta, no cuenta: hay que descargarla con →I, ¬I, RAA, ∨E o ∃E. Solo las premisas del ejercicio pueden quedar abiertas.'],
  ['Hay más de una prueba', 'Se acepta cualquier prueba válida, no solo la solución de referencia. Las reglas «Para este ejercicio» son una sugerencia, no una obligación.'],
  ['Pistas y solución explicada', 'No restan nada ni bloquean nada. Leer una solución no completa el ejercicio: tu prueba se comprueba por separado.'],
  ['Sin reloj ni vidas', '«Deshacer» quita tu última línea y «Reiniciar este ejercicio» empieza de cero. Equivocarte no cuesta nada.'],
  ['Tu progreso', 'Se guarda solo en este navegador, sin cuenta. Al abrir Practicar, las pruebas guardadas se vuelven a verificar.'],
];

const PARAM_NAMES = {term: 'un término', var: 'una variable', template: 'una plantilla'};
const short = label => String(label).split(' · ')[0];

/** Mini prueba de ejemplo: premisas y líneas, con la línea que usa la regla señalada. */
export function exampleList(example, rule, rules) {
  const list = el('ol', 'pg-example'); list.setAttribute('aria-label', `Ejemplo de ${short(rules[rule].label)}`);
  const lines = [...example.premises.map(f => ({formula: f, premise: true})), ...example.moves.map(m => ({...m}))];
  lines.forEach((line, i) => {
    const focus = i + 1 === example.focus;
    const item = el('li', `pg-ex-line${focus ? ' is-focus' : ''}`);
    if (focus) item.setAttribute('aria-current', 'true');
    let why = 'Premisa';
    if (!line.premise) {
      why = short(rules[line.rule]?.label ?? line.rule);
      if (line.refs?.length) why += ` · ${line.refs.join(', ')}`;
      for (const [k, v] of Object.entries(line.params || {})) why += k === 'term' ? ` · t = ${v}` : k === 'var' ? ` · var ${v}` : ` · plantilla ${v}`;
    }
    item.append(el('span', 'pg-ex-n', String(i + 1)), el('code', 'pg-ex-f', line.formula), el('span', 'pg-ex-why', why));
    list.append(item);
  });
  return list;
}

function ruleCard(key, rules, examples) {
  const rule = rules[key];
  const card = el('article', 'pg-rule');
  const name = el('h4', 'pg-rule-name', rule.label);
  const meta = [rule.refs ? `${rule.refs} ${rule.refs === 1 ? 'referencia' : 'referencias'}, en orden` : 'sin referencias'];
  if (rule.params.length) meta.push(`pide ${rule.params.map(p => PARAM_NAMES[p] || p).join(' y ')}`);
  card.append(name, el('p', 'pg-rule-help', rule.help), el('p', 'pg-rule-meta', meta.join(' · ')));
  if (examples[key]) card.append(exampleList(examples[key], key, rules));
  return card;
}

/** Diálogo nativo con las reglas del juego y la chuleta. opener recupera el foco al cerrar. */
export function openRulesDialog({rules, opener, onTutorial, doc = document}) {
  const dialog = el('dialog', 'pg-dialog'); dialog.setAttribute('aria-labelledby', 'pg-title');
  const head = el('div', 'pg-head');
  const title = el('h2', '', 'Reglas del juego'); title.id = 'pg-title';
  head.append(title, button('Cerrar', 'pg-close', () => dialog.close()));
  const body = el('div', 'pg-body');
  const tools = el('div', 'pg-tools');
  tools.append(button('Ver el tutorial', 'pg-primary', () => { dialog.close(); onTutorial?.(); }),
    el('span', 'pg-hint', 'Esc cierra esta ventana.'));
  const list = el('ol', 'pg-rules-list');
  for (const [name, text] of GAME_RULES) { const li = el('li'); li.append(el('strong', '', name), el('span', '', text)); list.append(li); }
  const sheet = el('section', 'pg-sheet'); sheet.setAttribute('aria-labelledby', 'pg-sheet-title');
  const sheetTitle = el('h3', '', 'Chuleta de reglas'); sheetTitle.id = 'pg-sheet-title';
  sheet.append(sheetTitle, el('p', 'pg-sheet-lead', 'Las 22 reglas de inferencia, por familia, con un ejemplo verificado de cada una. La línea marcada es la que usa la regla.'));
  const status = el('p', 'pg-status', 'Cargando la chuleta…'); status.setAttribute('role', 'status'); sheet.append(status);
  body.append(tools, el('h3', 'pg-section', 'Cómo se juega'), list, sheet);
  dialog.append(head, body); doc.body.append(dialog);
  dialog.addEventListener('close', () => { dialog.remove(); if (opener?.isConnected) opener.focus(); });
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
  dialog.showModal();
  loadGuide().then(guide => {
    status.remove();
    const nav = el('div', 'pg-toc'); nav.setAttribute('role', 'group'); nav.setAttribute('aria-label', 'Ir a una familia de reglas');
    sheet.append(nav);
    for (const family of guide.families) {
      const section = el('section', 'pg-family'); const id = `pg-fam-${family.id}`; section.setAttribute('aria-labelledby', id);
      const h = el('h3', 'pg-family-title', family.title); h.id = id; h.tabIndex = -1;
      section.append(h, el('p', 'pg-family-blurb', family.blurb));
      const grid = el('div', 'pg-family-rules');
      for (const key of family.rules) if (rules[key]) grid.append(ruleCard(key, rules, guide.examples));
      section.append(grid); sheet.append(section);
      nav.append(button(`${family.title} (${family.rules.length})`, 'pg-chip', () => {
        h.scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'}); h.focus({preventScroll: true});
      }));
    }
  }).catch(() => { status.textContent = 'No se pudo cargar la chuleta con ejemplos. Las reglas del juego de arriba siguen valiendo.'; });
  return dialog;
}

/** {banner, panel}: el banner de primera vez (o null) y el panel «Cómo se juega» del inicio. */
export function homePanel({offer, onStart, onDismiss, onRules}) {
  let banner = null;
  if (offer) {
    banner = el('section', 'pg-banner'); banner.setAttribute('aria-labelledby', 'pg-banner-title');
    const text = el('p', 'pg-banner-text'); const strong = el('strong', '', '¿Primera vez? Haz el tutorial'); strong.id = 'pg-banner-title';
    text.append(strong, el('span', '', ' Tu primera prueba en 2 minutos, dentro del ejercicio 01 real.'));
    const actions = el('div', 'pg-banner-actions');
    actions.append(button('Hacer el tutorial', 'pg-primary', onStart), button('Ahora no', 'pg-quiet', onDismiss));
    banner.append(text, actions);
  }
  const panel = el('section', 'pg-panel'); panel.setAttribute('aria-labelledby', 'pg-panel-title');
  const top = el('div', 'pg-panel-top');
  const heading = el('div');
  heading.append(el('p', 'pg-eyebrow', 'REGLAS EN CORTO'));
  const h = el('h3', '', 'Cómo se juega'); h.id = 'pg-panel-title'; heading.append(h);
  const actions = el('div', 'pg-panel-actions');
  actions.append(button('Reglas y chuleta', 'pg-secondary', e => onRules(e.currentTarget)), button('Ver el tutorial', 'pg-secondary', onStart));
  top.append(heading, actions);
  const steps = el('ol', 'pg-steps');
  QUICK_RULES.forEach(([name, text]) => { const li = el('li', 'pg-step'); li.append(el('span', 'pg-knot', ''), el('h4', '', name), el('p', '', text)); steps.append(li); });
  panel.append(top, steps);
  return {banner, panel};
}
