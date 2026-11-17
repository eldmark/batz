/* Tutor de demostraciones. Las decisiones lógicas se comprueban en Python. */
(() => {
  'use strict';
  const root = document.getElementById('practice-root');
  const storageKey = 'batz.practice.v1';
  let bank, progress = {}, current = null, result = null, hints = [], hintIndex = 0;
  let generation = 0, previewGeneration = 0, timer, busy = false, lastField, savingWarning = false;
  let activeCategory = 'introduction', migrated = false;
  // Reglas y tutorial: módulo ES opcional (features/practice-tutorial). Si no carga, el juego sigue igual.
  let extras = null;
  const emit = (name, detail) => root.dispatchEvent(new CustomEvent(name, {bubbles: true, detail}));
  // ÚNICO punto de unión con el módulo: este puente (sin globals). Eventos que emite practice.js sobre #practice-root:
  // 'batz-practice-view' {view:'home'|'exercise', id} y 'batz-practice-checked' {ok, complete, error}.
  const bridge = {root, getProgress: () => progress, getBank: () => bank, currentId: () => current?.id ?? null,
    setRecord: (id, rec) => { progress[id] = rec; save(); }, open: id => open(id),
    refreshHome: () => { if (!current && root.querySelector('.pr-hero')) home(); }};
  const el = (tag, cls, text) => {
    const n = document.createElement(tag); if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text; return n;
  };
  const byId = id => document.getElementById(`pr-${id}`);
  const button = (text, cls, action) => {
    const b = el('button', `pr-button ${cls || ''}`, text); b.type = 'button';
    b.addEventListener('click', action); return b;
  };
  const formula = item => {
    const box = el('div', 'pr-expression');
    box.append(el('p', 'pr-reading', item.reading), el('p', 'pr-formal', item.formula));
    return box;
  };
  async function api(action, data = {}) {
    const response = await fetch(`/api/practice/${action}`, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
    });
    const payload = await response.json();
    if (!response.ok || payload.status !== 'ok') {
      const error = new Error(payload.errors?.[0]?.message || 'No se pudo comprobar la demostración.');
      error.status = response.status; throw error;
    }
    return payload;
  }
  function save() {
    try { localStorage.setItem(storageKey, JSON.stringify(progress)); }
    catch { savingWarning = true; }
    if (byId('save-note')) byId('save-note').textContent = savingWarning
      ? 'El navegador no permite guardar el progreso. Puedes seguir jugando en esta sesión.'
      : 'Tu progreso se guarda en este navegador.';
  }
  const record = id => progress[id] || (progress[id] = {moves: [], complete: false, hints: 0});
  const completed = () => bank.exercises.filter(ex => record(ex.id).complete).length;
  const categoryOf = id => bank.categories.find(c => c.id === id);
  const categoryExercises = id => bank.exercises.filter(ex => ex.category === id);
  const categoryCompleted = id => categoryExercises(id).filter(ex => record(ex.id).complete).length;
  function progressBar() {
    const bar = el('div', 'pr-progress'); bar.setAttribute('role', 'img');
    const exercises = current ? categoryExercises(current.category) : bank.exercises;
    bar.setAttribute('aria-label', `${exercises.filter(ex=>record(ex.id).complete).length} de ${exercises.length} ejercicios completados${current ? ' en ' + categoryOf(current.category).title : ''}`);
    if (!current) {
      for (const category of bank.categories) {
        const span = el('span'); const ratio = categoryCompleted(category.id)/categoryExercises(category.id).length*100;
        span.style.flex = String(categoryExercises(category.id).length);
        span.style.background = `linear-gradient(to right, var(--pr-green) ${ratio}%, #dce2d6 ${ratio}%)`;
        span.setAttribute('aria-hidden', 'true'); bar.append(span);
      }
      return bar;
    }
    for (const ex of exercises) {
      const segment = el('span', `${record(ex.id).complete ? 'done' : ''} ${current?.id === ex.id ? 'active' : ''}`);
      segment.setAttribute('aria-hidden', 'true'); bar.append(segment);
    }
    return bar;
  }
  function home() {
    generation++; previewGeneration++; clearTimeout(timer); current = null; busy = false;
    root.replaceChildren();
    root.dataset.category = activeCategory;
    const hero = el('section', 'pr-hero');
    const heading = el('div');
    heading.append(el('p', 'pr-eyebrow', 'EL TALLER DE BAT’Z'), el('h2', '', 'Aprende a demostrar. Paso a paso.'),
      el('p', 'pr-lead', 'Cincuenta ejercicios, tres etapas y cada vez más ideas por conectar. De tu primera deducción a demostrar por qué el orden de una suma no importa.'));
    const next = bank.exercises.find(ex => !record(ex.id).complete) || bank.exercises[0];
    heading.append(button(completed() ? 'Continuar practicando →' : 'Empezar el primer ejercicio →', 'pr-primary', () => open(next.id)));
    const summary = el('aside', 'pr-summary');
    summary.append(el('span', 'pr-summary-symbol', '⊢'), el('p', 'pr-summary-count', `${completed()} / ${bank.total}`),
      el('p', '', completed() === bank.total ? 'Colección completada' : 'ejercicios completados'), progressBar(),
      el('span', 'pr-small', 'Sin reloj. Sin vidas. Con todas las pistas que necesites.'));
    hero.append(heading, summary);
    const guide = extras?.homeGuide();
    if (guide?.banner) root.append(guide.banner);
    root.append(hero);
    if (guide) root.append(guide.panel);
    if (migrated) root.append(el('p', 'pr-migration', 'Tu progreso compatible se conservó. Los ejercicios 05, 06 y 10 ahora son introductorios; sus borradores anteriores quedan archivados en este navegador.'));
    const navigation = el('nav', 'pr-categories'); navigation.setAttribute('aria-label', 'Categorías de ejercicios');
    for (const category of bank.categories) {
      const card = button('', `pr-category pr-category-${category.id}`, () => {
        activeCategory = category.id; home();
        root.querySelector(`[data-category="${category.id}"]`).focus({preventScroll:true});
      });
      card.dataset.category = category.id;
      card.setAttribute('aria-pressed', String(activeCategory === category.id));
      const count = categoryCompleted(category.id), total = categoryExercises(category.id).length;
      card.append(el('span', 'pr-category-range', `${String(category.start).padStart(2,'0')} — ${category.end}`),
        el('span', 'pr-category-title', category.title), el('span', 'pr-category-count', `${count} de ${total} completados`));
      const meter = el('span', 'pr-category-meter'); const fill = el('span'); fill.style.width = `${count/total*100}%`; meter.append(fill); card.append(meter);
      navigation.append(card);
    }
    root.append(navigation);
    const section = el('section', 'pr-collection');
    const category = categoryOf(activeCategory);
    const bar = el('div', 'pr-collection-bar');
    const sectionHeading = el('div'); sectionHeading.append(el('h3', '', category.title), el('p', 'pr-category-description', category.description));
    bar.append(sectionHeading, el('span', 'pr-small', `Niveles ${category.start}–${category.end}`)); section.append(bar);
    const grid = el('div', 'pr-grid');
    for (const ex of categoryExercises(activeCategory)) {
      const card = button('', `pr-exercise ${record(ex.id).complete ? 'is-complete' : ''}`, () => open(ex.id));
      const top = el('div', 'pr-card-top');
      top.append(el('span', 'pr-number', record(ex.id).complete ? '✓' : ex.id),
        el('span', 'pr-small', record(ex.id).complete ? 'Completado' : ex.topic), el('span', 'pr-card-arrow', '↗'));
      top.lastChild.setAttribute('aria-hidden', 'true');
      card.append(top, el('h4', '', ex.title), formula(ex.goal)); grid.append(card);
    }
    section.append(grid); root.append(section);
    const note = el('p', 'pr-footnote'); note.id = 'pr-save-note'; root.append(note); save();
    emit('batz-practice-view', {view: 'home'});
  }
  function message(text, kind = '') {
    const box = byId('feedback'); if (!box) return;
    box.className = `pr-feedback ${kind}`; box.textContent = text; box.hidden = !text;
  }
  function setBusy(value) {
    busy = value;
    for (const id of ['check', 'undo', 'reset', 'hint']) {
      const b = byId(id); if (b) b.disabled = value;
    }
    if (byId('check')) {
      byId('check').textContent = value ? 'Comprobando…' : 'Comprobar paso';
      byId('check').setAttribute('aria-busy', String(value));
    }
  }
  async function open(id) {
    const ticket = ++generation; previewGeneration++; clearTimeout(timer); busy = false;
    current = bank.exercises.find(e => e.id === id); const ex = current;
    activeCategory = ex.category; root.dataset.category = ex.category;
    root.replaceChildren(el('p', 'pr-loading', 'Abriendo tu demostración…'));
    try {
      result = await api('check', {exercise: id, moves: record(id).moves});
      if (ticket !== generation) return;
      record(id).complete = result.complete;
      hintIndex = record(id).hints || 0; hints = [];
      for (let i = 0; i < hintIndex; i++) hints.push((await api('hint', {exercise: id, index: i})).hint);
      if (ticket !== generation) return;
      renderExercise();
    } catch (err) {
      if (ticket !== generation) return;
      const box = el('div', 'pr-load-error'); box.append(el('h2', '', 'No pudimos abrir el ejercicio'), el('p', '', err.message),
        button('Volver a los ejercicios', '', home), button('Reintentar', 'pr-primary', () => open(ex.id)));
      root.replaceChildren(box);
    }
  }
  function renderExercise() {
    root.replaceChildren();
    const toolbar = el('div', 'pr-toolbar');
    const position = el('span', 'pr-position');
    position.append(el('span', `pr-stage pr-stage-${current.category}`, categoryOf(current.category).title),
      el('span', 'pr-small', `EJERCICIO ${current.id} DE ${bank.total}`));
    toolbar.append(button('← Ejercicios', 'pr-quiet', home), position);
    if (extras) position.prepend(extras.rulesButton()); root.append(toolbar, progressBar());
    const layout = el('div', 'pr-layout');
    const proof = el('section', 'pr-proof');
    proof.append(el('p', 'pr-eyebrow', current.topic), el('h2', 'pr-title', current.title), el('p', 'pr-intro', current.intro));
    const goal = el('div', 'pr-goal'); goal.append(el('h3', 'pr-eyebrow', 'TU OBJETIVO'), formula(current.goal)); proof.append(goal);
    const heading = el('div', 'pr-proof-heading');
    const h = el('h3', '', 'Tu demostración'); h.id = 'pr-lines-title';
    const undo = button('Deshacer', 'pr-quiet', undoMove); undo.id = 'pr-undo';
    heading.append(h, undo); proof.append(heading);
    const lines = el('ol', 'pr-lines'); lines.id = 'pr-lines'; lines.setAttribute('aria-labelledby', 'pr-lines-title'); proof.append(lines);
    const success = el('div', 'pr-success'); success.id = 'pr-success'; success.setAttribute('role', 'status'); proof.append(success);
    const foot = el('div', 'pr-proof-foot');
    const reset = button('Reiniciar este ejercicio', 'pr-quiet', resetExercise); reset.id = 'pr-reset'; foot.append(reset);
    const saveNote = el('span', 'pr-small'); saveNote.id = 'pr-save-note'; foot.append(saveNote); proof.append(foot);
    const editor = el('section', 'pr-editor'); editor.id = 'pr-editor';
    editor.append(el('p', 'pr-eyebrow', 'UN PASO A LA VEZ'), el('h3', '', 'Añade una línea'));
    const form = el('form'); form.id = 'pr-form'; form.noValidate = true;
    const ruleLabel = el('label', '', '1. Elige la regla'); ruleLabel.htmlFor = 'pr-rule';
    const select = el('select'); select.id = 'pr-rule';
    const recommended = el('optgroup'); recommended.label = 'Para este ejercicio';
    const other = el('optgroup'); other.label = 'Otras reglas · también se aceptan pruebas alternativas';
    for (const [key, value] of Object.entries(bank.rules)) {
      const opt = el('option', '', value.label); opt.value = key;
      (current.rules.includes(key) ? recommended : other).append(opt);
    }
    select.append(recommended, other);
    const savedRule = record(current.id).editor?.rule;
    select.value = typeof savedRule === 'string' && Object.hasOwn(bank.rules, savedRule) ? savedRule : current.rules[0];
    const help = el('p', 'pr-rule-help'); help.id = 'pr-rule-help'; select.setAttribute('aria-describedby', help.id);
    const refsLabel = el('label', '', '2. Cita las líneas, en orden'); refsLabel.htmlFor = 'pr-refs'; refsLabel.id = 'pr-refs-label';
    const refs = el('input'); refs.id = 'pr-refs'; refs.placeholder = 'Ej.: 1, 2'; refs.autocomplete = 'off'; refs.inputMode = 'text';
    refs.setAttribute('aria-describedby', 'pr-refs-help');
    const refsHelp = el('p', 'pr-small', 'Puedes tocar los números de las líneas para citarlas.'); refsHelp.id = 'pr-refs-help';
    const formulaLabel = el('label', '', '3. Escribe la nueva fórmula'); formulaLabel.htmlFor = 'pr-formula';
    const reading = el('p', 'pr-live-reading', 'La lectura en español aparecerá aquí mientras escribes.'); reading.id = 'pr-reading'; reading.setAttribute('aria-live', 'polite');
    const field = el('textarea'); field.id = 'pr-formula'; field.rows = 2; field.maxLength = 500; field.spellcheck = false;
    field.autocomplete = 'off'; field.setAttribute('aria-describedby', 'pr-reading'); field.placeholder = 'Escribe tu siguiente paso…';
    const keys = el('div', 'pr-keyboard'); keys.setAttribute('role', 'group'); keys.setAttribute('aria-label', 'Insertar símbolos formales');
    const symbols = [['¬','negación'],['∧','conjunción'],['∨','disyunción'],['→','implicación'],['↔','equivalencia'],['∀','para todo'],['∃','existe'],['⊥','contradicción'],['=','igualdad'],['(','paréntesis izquierdo'],[')','paréntesis derecho']];
    for (const s of symbols) keys.append(key(s[0], s[1]));
    const tokens = el('div', 'pr-tokens');
    for (const token of [...new Set((current.premises.map(p=>p.formula).join(' ') + ' ' + current.goal.formula).match(/[A-Za-z]+/g) || [])].concat(['x', 'y', 'u', 'v', 't', 'k', 'w', ',']).filter((v,i,a)=>a.indexOf(v)===i)) tokens.append(key(token, token));
    const params = el('div', 'pr-params'); params.id = 'pr-params';
    const feedback = el('div', 'pr-feedback'); feedback.id = 'pr-feedback'; feedback.hidden = true; feedback.setAttribute('role', 'status');
    const submit = el('button', 'pr-button pr-primary pr-submit', 'Comprobar paso'); submit.id = 'pr-check'; submit.type = 'submit';
    form.append(ruleLabel, select, help, refsLabel, refs, refsHelp, formulaLabel, reading, field, keys, tokens, params, feedback, submit);
    form.addEventListener('submit', e => { e.preventDefault(); submitMove(); });
    form.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); submitMove(); } });
    editor.append(form, el('p', 'pr-shortcut', 'Ctrl / ⌘ + Enter para comprobar'));
    const assist = el('div', 'pr-assist');
    const hintButton = button('Necesito una pista', 'pr-quiet', nextHint); hintButton.id = 'pr-hint';
    const hintBox = el('div', 'pr-hints'); hintBox.id = 'pr-hints'; hintBox.setAttribute('aria-live', 'polite'); assist.append(hintButton, hintBox);
    const solution = el('details', 'pr-solution'); solution.append(el('summary', '', 'Ver una solución explicada'));
    solution.addEventListener('toggle', async () => {
      if (!solution.open || solution.dataset.loaded) return;
      solution.dataset.loaded = 'true'; const ticket = generation, id = current.id;
      const host = el('div'); solution.append(host); host.textContent = 'Cargando solución…';
      try {
        const response = await api('solution', {exercise: id}); if (ticket !== generation) return;
        host.replaceChildren(el('p', 'pr-small', 'Esta es una solución posible. Leerla no completa el ejercicio: tu demostración se comprueba por separado.'));
        for (const line of response.lines) {
          const item = el('div', 'pr-solution-line'); item.append(formula(line), el('p', 'pr-small', `${line.n}. ${line.label}${line.refs.length ? ' · líneas ' + line.refs.join(', ') : ''}`)); host.append(item);
        }
      } catch (err) { host.textContent = err.message; delete solution.dataset.loaded; }
    });
    assist.append(solution); editor.append(assist); layout.append(proof, editor); root.append(layout);
    const saved = record(current.id).editor || {};
    field.value = saved.formula || ''; refs.value = saved.refs || ''; lastField = field;
    select.addEventListener('change', () => { renderRule(); rememberEditor(); message(''); schedulePreview(); });
    refs.addEventListener('input', () => { selectReferences(); rememberEditor(); });
    for (const input of [field, refs]) input.addEventListener('focus', () => { if (input === field) lastField = input; });
    field.addEventListener('input', () => { message(''); rememberEditor(); schedulePreview(); });
    renderRule(saved); renderLines(); renderHints(); schedulePreview(); save();
    emit('batz-practice-view', {view: 'exercise', id: current.id});
  }
  function key(symbol, name) {
    const b = button(symbol, 'pr-key', () => {
      const input = lastField?.isConnected ? lastField : byId('formula');
      input.focus(); input.setRangeText(symbol, input.selectionStart, input.selectionEnd, 'end');
      input.dispatchEvent(new Event('input', {bubbles:true}));
    });
    b.title = `Insertar ${name}`; b.setAttribute('aria-label', b.title);
    b.addEventListener('mousedown', e => e.preventDefault()); return b;
  }
  function renderRule(saved = {}) {
    const rule = bank.rules[byId('rule').value];
    byId('rule-help').textContent = rule.help;
    byId('refs').disabled = !rule.refs;
    byId('refs-label').textContent = rule.refs ? `2. Cita ${rule.refs} ${rule.refs === 1 ? 'línea' : 'líneas'}, en orden` : '2. Esta regla no necesita referencias';
    if (!rule.refs) byId('refs').value = '';
    byId('params').replaceChildren();
    const labels = {term: 'Término elegido / testigo', var: 'Variable propia o de la plantilla', template: 'Plantilla de sustitución'};
    for (const param of rule.params) {
      const label = el('label', '', labels[param]); label.htmlFor = `pr-param-${param}`;
      const input = el('input'); input.id = `pr-param-${param}`; input.maxLength = 500; input.spellcheck = false; input.autocomplete = 'off';
      input.value = saved[param] || (param === 'var' && byId('rule').value === 'eq_e' ? 'x' : '');
      input.placeholder = param === 'template' ? 'Ej.: P(x)' : param === 'var' ? 'Ej.: y' : 'Ej.: a';
      if (param === 'template') {
        const translation = el('p', 'pr-live-reading', 'La plantilla muestra dónde sustituir.'); translation.id = 'pr-template-reading'; byId('params').append(label, translation, input);
        input.addEventListener('input', () => schedulePreview(true));
      } else byId('params').append(label, input);
      input.addEventListener('focus', () => { lastField = input; });
      input.addEventListener('input', rememberEditor);
    }
    selectReferences();
  }
  function rememberEditor() {
    if (!current || !byId('formula')) return;
    const draft = {formula:byId('formula').value, refs:byId('refs').value, rule:byId('rule').value};
    for (const param of bank.rules[draft.rule].params) draft[param] = byId(`param-${param}`).value;
    record(current.id).editor = draft; save();
  }
  function refsValue() {
    const value = byId('refs').value.trim();
    if (!value || byId('refs').disabled) return [];
    if (!/^\d+(?:\s*,\s*\d+)*$/.test(value)) throw new Error('Escribe números de línea separados por comas, por ejemplo: 1, 2.');
    return value.split(',').map(n => Number(n.trim()));
  }
  function selectReferences() {
    if (!byId('refs')) return;
    let refs = []; try { refs = refsValue(); } catch { /* se explica al comprobar */ }
    for (const b of root.querySelectorAll('[data-ref]')) {
      const positions = refs.map((r,i)=>r === Number(b.dataset.ref) ? i+1 : 0).filter(Boolean);
      b.setAttribute('aria-pressed', String(positions.length > 0));
      b.title = positions.length ? `Línea ${b.dataset.ref}, referencia ${positions.join(' y ')}` : `Citar línea ${b.dataset.ref}`;
      b.closest('li').classList.toggle('is-selected', positions.length > 0);
    }
  }
  function renderLines() {
    const host = byId('lines'); host.replaceChildren();
    if (!result.lines.length) host.append(el('li', 'pr-empty', 'Sin premisas. Empieza introduciendo una hipótesis temporal.'));
    for (const line of result.lines) {
      const li = el('li', `pr-line ${line.premise ? 'is-premise' : ''}`);
      const n = button(String(line.n).padStart(2,'0'), 'pr-line-number', () => {
        if (byId('refs').disabled || busy || result.complete) return;
        let refs=[]; try { refs = refsValue(); } catch { /* recuperar la selección */ }
        if (refs.includes(line.n)) refs = refs.filter(r=>r!==line.n); else refs.push(line.n);
        byId('refs').value = refs.join(', '); selectReferences(); rememberEditor();
      });
      n.dataset.ref = line.n; n.setAttribute('aria-label', `Citar línea ${line.n}`); n.setAttribute('aria-pressed','false');
      const body = el('div', 'pr-line-body'); body.append(formula(line));
      const meta = el('div', 'pr-line-meta'); meta.append(el('span','', line.label + (line.refs.length ? ' · ' + line.refs.join(', ') : '')));
      if (line.pending.length) {
        const deps = el('span', 'pr-dependency', 'Hipótesis pendiente');
        const details = el('details', 'pr-dependencies'); details.append(el('summary', '', 'Ver dependencias'));
        for (const h of line.pending) details.append(formula(h)); meta.append(deps, details);
      } else if (!line.premise) meta.append(el('span', 'pr-verified', '✓ Verificada'));
      body.append(meta); li.append(n, body); host.append(li);
    }
    byId('undo').disabled = busy || !record(current.id).moves.length;
    const success = byId('success'); success.replaceChildren(); success.hidden = !result.complete;
    byId('form').hidden = result.complete;
    byId('editor').querySelector('h3').textContent = result.complete ? 'Buen trabajo.' : 'Añade una línea';
    if (result.complete) {
      success.append(el('span','pr-success-mark','✓'), el('h3','','Demostración completada'),
        el('p','', 'Cada paso es válido y la conclusión no depende de hipótesis pendientes.'));
      const next = bank.exercises[bank.exercises.indexOf(current)+1];
      const nextLabel = !next ? 'Ver mi recorrido →' : next.category !== current.category
        ? `Entrar en ${categoryOf(next.category).title} →` : 'Siguiente ejercicio →';
      success.append(button(nextLabel, 'pr-primary', () => next ? open(next.id) : home()));
    }
    selectReferences();
    const bar = root.querySelector('.pr-progress'); if (bar) bar.replaceWith(progressBar());
  }
  function schedulePreview() {
    const pairs = [[byId('formula'),byId('reading')], [byId('param-template'),byId('template-reading')]].filter(([f,t])=>f && t);
    const ticket = ++previewGeneration, page = generation;
    clearTimeout(timer);
    // Invalida inmediatamente la lectura anterior, incluso antes del debounce.
    for (const [field,target] of pairs) target.textContent = field.value ? 'Leyendo la expresión…' : 'La lectura en español aparecerá aquí mientras escribes.';
    const exercise = current.id;
    timer = setTimeout(() => Promise.all(pairs.map(async ([field,target]) => {
      try {
        const value = await api('preview', {exercise, formula:field.value});
        if (ticket !== previewGeneration || page !== generation || !target.isConnected) return;
        target.textContent = value.reading;
        field.setAttribute('aria-invalid', String(!value.valid && Boolean(field.value)));
      } catch { if (ticket === previewGeneration && target.isConnected) target.textContent = 'La lectura no está disponible. Puedes comprobar el paso para ver el diagnóstico.'; }
    })), 200);
  }
  async function submitMove() {
    if (busy || result.complete) return;
    const ticket = generation, ex = current;
    try {
      const rule = byId('rule').value;
      const move = {formula:byId('formula').value, rule, refs:refsValue(), params:{}};
      for (const param of bank.rules[rule].params) move.params[param] = byId(`param-${param}`).value;
      if (!move.formula.trim()) { message('Escribe la fórmula que quieres obtener.', 'is-error'); byId('formula').focus(); return; }
      setBusy(true);
      const moves = [...record(ex.id).moves, move];
      const response = await api('check', {exercise:ex.id, moves});
      if (ticket !== generation) return;
      result = response; record(ex.id).moves = moves; record(ex.id).complete = response.complete;
      byId('formula').value = ''; byId('refs').value = ''; rememberEditor();
      renderLines();
      message(response.open_goal ? 'La fórmula coincide con el objetivo, pero depende de una hipótesis pendiente. Descárgala para completar la prueba.' : '✓ Paso correcto. Tu demostración avanza.', response.open_goal ? 'is-warning' : 'is-good');
      schedulePreview(); emit('batz-practice-checked', {ok: true, complete: response.complete});
      if (response.complete) byId('success').scrollIntoView({block:'nearest',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
      else byId('formula').focus({preventScroll:true});
    } catch (err) { if (ticket === generation) { message(err.message, 'is-error'); byId('formula').setAttribute('aria-invalid','true'); emit('batz-practice-checked', {ok: false, complete: false, error: err.message}); } }
    finally { if (ticket === generation) { setBusy(false); byId('undo').disabled = !record(ex.id).moves.length; } }
  }
  async function replaceMoves(moves) {
    if (busy) return; const ticket = generation, id = current.id; setBusy(true);
    try {
      const response = await api('check', {exercise:id, moves}); if (ticket !== generation) return;
      record(id).moves = moves; record(id).complete = response.complete; result = response;
      record(id).editor = {}; save(); renderExercise();
    } catch (err) { if (ticket === generation) message(err.message,'is-error'); }
    finally { if (ticket === generation) { setBusy(false); byId('undo').disabled = !record(id).moves.length; } }
  }
  function undoMove() { replaceMoves(record(current.id).moves.slice(0,-1)); }
  function resetExercise() {
    if (!record(current.id).moves.length && !byId('formula').value) return;
    if (window.confirm('¿Reiniciar esta demostración? Se borrarán los pasos de este ejercicio.')) replaceMoves([]);
  }
  function renderHints() {
    const host = byId('hints'); host.replaceChildren();
    hints.forEach((hint,i) => { const p = el('p'); p.append(el('strong','',`Pista ${i+1}. `),document.createTextNode(hint)); host.append(p); });
    byId('hint').textContent = hintIndex >= current.hint_count ? 'Ya tienes todas las pistas' : hintIndex ? `Otra pista (${hintIndex}/${current.hint_count})` : 'Necesito una pista';
    byId('hint').hidden = hintIndex >= current.hint_count;
  }
  async function nextHint() {
    if (busy || hintIndex >= current.hint_count) return;
    const ticket = generation, id = current.id; byId('hint').disabled = true;
    try {
      const value = await api('hint', {exercise:id,index:hintIndex}); if (ticket !== generation) return;
      hints.push(value.hint); hintIndex++; record(id).hints = hintIndex; save(); renderHints();
    } catch (err) { if (ticket === generation) message(err.message,'is-error'); }
    finally { if (ticket === generation) byId('hint').disabled = false; }
  }
  let initialization;
  async function init() {
    try {
      bank = await api('catalog');
      try { extras = (await import('/features/practice-tutorial/index.js')).attach(bridge); } catch { extras = null; }
      try {
        const stored = JSON.parse(localStorage.getItem(storageKey) || '{}');
        if (stored && typeof stored === 'object' && !Array.isArray(stored)) progress = stored;
      } catch { progress = {}; }
      try { extras?.recover(); } catch { /* sin copia que recuperar */ }
      for (const ex of bank.exercises) {
        const p = progress[ex.id];
        if (!p || typeof p !== 'object' || !Array.isArray(p.moves) || p.moves.length > 100) progress[ex.id] = {moves:[], complete:false,hints:0};
        const saved = record(ex.id);
        const changedLegacy = !saved.revision && ['05','06','10'].includes(ex.id);
        if ((saved.revision && saved.revision !== ex.revision) || (changedLegacy && saved.moves.length)) {
          saved.previous = [...(Array.isArray(saved.previous) ? saved.previous : []),
            {moves:saved.moves, editor:saved.editor || {}, revision:saved.revision || 'first-ten'}].slice(-3);
          saved.moves = []; saved.complete = false; saved.editor = {}; saved.hints = 0; migrated = true;
        }
        saved.revision = ex.revision;
        record(ex.id).hints = Math.max(0,Math.min(ex.hint_count,Number.isInteger(record(ex.id).hints) ? record(ex.id).hints : 0));
      }
      // Una marca en localStorage no sustituye la verificación de la prueba.
      await Promise.all(bank.exercises.map(async ex => {
        const p = record(ex.id); p.complete = false;
        if (!p.moves.length) return;
        try { p.complete = (await api('check',{exercise:ex.id,moves:p.moves})).complete; }
        catch (err) { if (err.status >= 400 && err.status < 500) { p.moves = []; p.editor = {}; } else throw err; }
      }));
      home();
    } catch (err) {
      root.replaceChildren(el('p','pr-load-error',`No se pudieron cargar los ejercicios. ${err.message}`),button('Reintentar','pr-primary',()=>{initialization=init();}));
    }
  }
  window.addEventListener('batz-practice', () => { initialization ||= init(); });
  if (/^#\/?practicar$/.test(location.hash)) initialization ||= init();   // arranque directo en la ruta de práctica
})();
