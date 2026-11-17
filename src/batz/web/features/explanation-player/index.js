import {browserSpanishVoices, caseIndex, chooseVoice, domainPresentation, eventLabel, eventVerdict, loadServerVoices, noVoiceHelp, readVoicePref, resetServerVoices, readingTime, saveVoicePref, valueLabel, wordTimings} from './events.js';
import {createFullscreen} from './fullscreen.js';

// La síntesis del navegador es compartida. Solo el dueño activo puede cancelarla.
let activePlayer = null;
let instanceNumber = 0;

/** Reproductor sin dependencias del estado/DOM de Evaluar, Demostrar o Cuadernos. */
export function createExplanationPlayer({host, onStepChange = () => {}, onStateChange = () => {}}) {
  if (!host?.ownerDocument) throw new TypeError('Se necesita un elemento host.');
  const doc = host.ownerDocument, win = doc.defaultView, serial = ++instanceNumber;
  const synthesis = win.speechSynthesis;
  const controller = new win.AbortController();
  const listen = (target, name, action) => target?.addEventListener(name, action, {signal: controller.signal});
  const element = (tag, text, cls) => {
    const el = doc.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  };
  const button = (text, action) => {
    const el = element('button', text, 'ep-button'); el.type = 'button';
    // Los botones transitorios del 2D/lista se recolectan con su DOM, sin quedar
    // retenidos por el AbortSignal de la instancia en cada renderizado.
    el.addEventListener('click', action); return el;
  };
  const root = element('section', undefined, 'ep-player'); root.dataset.explanationPlayer = '';
  root.setAttribute('aria-labelledby', `ep-title-${serial}`); root.hidden = true;
  const header = element('div', undefined, 'ep-header');
  const heading = element('h2', 'Explicación guiada', 'ep-heading'); heading.id = `ep-title-${serial}`;
  const title = element('p', undefined, 'ep-title');
  const progress = element('p', undefined, 'ep-progress'); progress.setAttribute('role', 'status');
  const titles = element('div'); titles.append(heading, title, progress);
  const headerActions = element('div', undefined, 'ep-actions');
  const restore = button('Restaurar', () => open());
  const minimizeButton = button('Minimizar', () => minimize());
  const closeButton = button('Cerrar', () => close());
  headerActions.append(restore, minimizeButton, closeButton); header.append(titles, headerActions);
  const staleNote = element('p', undefined, 'ep-stale'); staleNote.setAttribute('role', 'status'); staleNote.hidden = true;
  const body = element('div', undefined, 'ep-body');
  const stage = element('div', undefined, 'ep-stage');
  const visual = element('div', undefined, 'ep-visual'); visual.hidden = true;
  visual.setAttribute('role', 'img'); visual.setAttribute('aria-label', 'Avatar y elementos del modelo. La explicación está disponible en texto.');
  const flat = element('div', undefined, 'ep-flat');
  const sceneStatus = element('p', undefined, 'ep-note'); sceneStatus.setAttribute('role', 'status');
  const fsButton = button('Pantalla completa', () => fullscreen.isOn() ? fullscreen.exit() : fullscreen.enter());
  fsButton.setAttribute('aria-pressed', 'false');
  stage.append(visual, flat, sceneStatus, fsButton);
  const detail = element('div', undefined, 'ep-detail');
  const location = element('p', undefined, 'ep-note');
  const formula = element('p', undefined, 'ep-formula');
  const context = element('p', undefined, 'ep-context');
  const narration = element('p', undefined, 'ep-narration');
  const badge = element('span', undefined, 'ep-badge');
  detail.append(location, formula, context, narration, badge); body.append(stage, detail);
  const controls = element('div', undefined, 'ep-controls'); controls.setAttribute('role', 'group');
  controls.setAttribute('aria-label', 'Recorrer los pasos');
  const previous = button('Anterior', () => go(index - 1)); previous.dataset.action = 'previous';
  const playButton = button('Reproducir', () => playing ? pause() : start()); playButton.dataset.action = 'play';
  const next = button('Siguiente', () => go(index + 1)); next.dataset.action = 'next';
  const repeat = button('Repetir paso', () => { if (ready()) { stepChanged(); start(); } });
  const restart = button('Desde el inicio', () => { if (ready()) { go(0); start(); } });
  controls.append(previous, playButton, next, repeat, restart);
  const options = element('div', undefined, 'ep-options');
  function checkbox(text) {
    const label = element('label', undefined, 'ep-check'), input = element('input'); input.type = 'checkbox';
    label.append(input, doc.createTextNode(text)); options.append(label); return input;
  }
  const voiceInput = checkbox('Narración por voz');
  const threeInput = checkbox('Vista 3D'); threeInput.checked = true;
  const rateLabel = element('label', 'Velocidad ', 'ep-rate');
  const rateInput = element('select');
  for (const value of [.75, 1, 1.25, 1.5]) {
    const option = element('option', `${String(value).replace('.', ',')}×`); option.value = String(value); rateInput.append(option);
  }
  rateInput.value = '1'; rateLabel.append(rateInput); options.append(rateLabel);
  const voiceLabel = element('label', 'Voz ', 'ep-voice');
  const voiceSelect = element('select'); voiceSelect.setAttribute('aria-describedby', `ep-voice-help-${serial}`);
  voiceLabel.append(voiceSelect); options.append(voiceLabel);
  const voiceTest = button('Probar voz', () => playSample()); voiceTest.classList.add('ep-voice-test');
  const voiceRescan = button('Volver a buscar voces', () => rescanVoices()); voiceRescan.classList.add('ep-voice-rescan'); voiceRescan.hidden = true;
  options.append(voiceTest, voiceRescan);
  const voiceHelp = element('p', undefined, 'ep-note'); voiceHelp.id = `ep-voice-help-${serial}`;
  const all = element('details', undefined, 'ep-all');
  all.append(element('summary', 'Ver todos los pasos'));
  const list = element('ol', undefined, 'ep-list'); all.append(list);
  root.append(header, staleNote, body, controls, options, voiceHelp, all); host.append(root);

  let payload = null, events = [], index = null, presentation = 'closed', stale = false, reason = '';
  let dead = false, playing = false, voiceEnabled = false, threeDEnabled = true, rate = 1, returnFocus = null;
  let scene = null, sceneGeneration = 0, loadingScene = false, sceneFailed = false;
  let utterance = null, run = 0;
  let serverVoices = [], serverHint = null, serverReason = null, voicePref = readVoicePref(win.localStorage), serverAudio = null, serverAbort = null, sample = null;
  const audioTimers = new Set();
  const fullscreen = createFullscreen(root, fsButton, {onExit() {
    if (presentation === 'closed' && returnFocus?.isConnected) returnFocus.focus({preventScroll:true});
    if (presentation === 'minimized') restore.focus({preventScroll:true});
  }});
  const ready = () => !dead && !stale && events.length > 0;
  const currentEvent = () => events[index];
  const snapshot = () => ({
    resultId: payload?.resultId ?? null, origin: payload?.origin ?? null, kind: payload?.kind ?? null,
    status: !events.length ? 'empty' : stale ? 'stale' : 'ready', presentation,
    index, total: events.length, playing, voiceEnabled, threeDEnabled, rate,
  });
  const notify = () => { if (!dead) onStateChange(snapshot()); };
  function stepChanged() {
    if (index !== null && !dead) onStepChange({resultId: payload.resultId, event: currentEvent(), index, total: events.length});
  }

  function renderFlat() {
    const focusedLabel = flat.contains(doc.activeElement) ? doc.activeElement.getAttribute('aria-label') : null;
    flat.replaceChildren();
    const event = currentEvent();
    if (!event) return;
    const domain = domainPresentation(event, payload.model);
    if (domain.length && event.kind !== 'proof') {
      const row = element('div', undefined, 'ep-domain'); row.setAttribute('role', 'group'); row.setAttribute('aria-label', 'Elementos del dominio');
      for (const item of domain.filter(item => item.visible)) {
        const b = button(valueLabel(item.value), () => pick(item.value)); b.classList.add('ep-node');
        b.setAttribute('aria-label', `Ver caso con ${valueLabel(item.value)}`);
        b.setAttribute('aria-pressed', String(item.active));
        if (item.active && typeof event.value === 'boolean') b.dataset.value = String(event.value);
        // El 2D permite el mismo salto por teclado que la escena por clic.
        b.disabled = !ready() || caseIndex(events, index, item.value) < 0;
        row.append(b);
      }
      if (!row.children.length) row.append(element('span', 'Todavía sin dominio', 'ep-note'));
      flat.append(row);
      const relation = payload.model?.predicates?.[event.relation];
      if (relation) {
        flat.append(element('p', `${event.relation}ᴵ = {${relation.tuples.map(tuple => `(${tuple.map(valueLabel).join(', ')})`).join(', ')}}`, 'ep-relation'));
      } else if (event.kind !== 'search') flat.append(element('p', `D = {${domain.map(item => valueLabel(item.value)).join(', ')}}`, 'ep-relation'));
    } else {
      flat.append(element('p', event.kind === 'proof' ? 'Deducción desde las premisas' : 'Representación del paso', 'ep-note'));
      if (event.refs?.length) flat.append(element('p', `Usa las líneas ${event.refs.join(', ')}`, 'ep-relation'));
    }
    if (focusedLabel) [...flat.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === focusedLabel && !b.disabled)?.focus({preventScroll:true});
  }

  function render() {
    if (dead) return;
    root.hidden = presentation === 'closed' || !events.length;
    root.dataset.presentation = presentation; root.dataset.status = snapshot().status;
    title.textContent = payload?.title || ({evaluation: 'Evaluación semántica', proof: 'Demostración', countermodel: 'Contramodelo'}[payload?.kind] || '');
    progress.textContent = index === null ? '' : `Paso ${index + 1} de ${events.length}`;
    restore.hidden = presentation !== 'minimized'; minimizeButton.hidden = presentation === 'minimized';
    for (const el of [body, controls, options, voiceHelp, all]) el.hidden = presentation !== 'expanded';
    staleNote.hidden = !stale; staleNote.textContent = reason;
    const event = currentEvent();
    if (event) {
      location.textContent = eventLabel(event);
      formula.textContent = event.formula || ''; formula.hidden = !event.formula;
      narration.textContent = event.text_es || '';
      const parts = [];
      const assignment = Object.entries(event.assignment || {});
      if (assignment.length) parts.push('Asignación: ' + assignment.map(([name, value]) => `${name} = ${valueLabel(value)}`).join(', '));
      if (event.refs?.length) parts.push(`Referencias: ${event.refs.join(', ')}`);
      if (event.context?.length) parts.push(`Hipótesis abiertas: ${event.context.join('; ')}`);
      context.textContent = parts.join(' · '); context.hidden = !parts.length;
      const verdict = eventVerdict(event); badge.textContent = verdict.label; badge.dataset.tone = verdict.tone;
      scene?.setEvent(event); renderFlat();
    }
    previous.disabled = !ready() || index === 0; next.disabled = !ready() || index === events.length - 1;
    for (const b of [playButton, repeat, restart]) b.disabled = !ready();
    playButton.textContent = playing ? 'Pausar' : 'Reproducir'; playButton.setAttribute('aria-pressed', String(playing));
    list.querySelectorAll('button').forEach((b, i) => {
      b.disabled = !ready();
      if (i === index) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current');
    });
    threeInput.checked = threeDEnabled; rateInput.value = String(rate);
    visual.hidden = !scene || !threeDEnabled;
  }

  function releaseScene() {
    ++sceneGeneration; loadingScene = false;
    scene?.dispose(); scene = null; visual.replaceChildren(); visual.hidden = true;
  }

  async function ensureScene() {
    if (!ready() || presentation !== 'expanded' || !threeDEnabled || scene || loadingScene || sceneFailed) return;
    const token = ++sceneGeneration; loadingScene = true;
    sceneStatus.textContent = 'Cargando vista 3D…';
    const valid = () => !dead && token === sceneGeneration && ready() && presentation === 'expanded' && threeDEnabled;
    const fail = () => {
      if (!valid()) return;
      sceneFailed = true; releaseScene();
      sceneStatus.textContent = 'No se pudo cargar la vista 3D. Puedes seguir con el texto y la vista 2D.';
    };
    try {
      const {createStoryScene} = await import('../../story3d.js');
      if (!valid()) return;
      // La URL es relativa a features/explanation-player/, sin dependencias del shell.
      visual.hidden = false;
      const candidate = createStoryScene(visual, payload.model, {
        onPick: pick,
        onReady: () => { if (valid()) sceneStatus.textContent = 'Vista 3D lista. Los elementos también están disponibles debajo por teclado.'; },
        onError: fail,
      });
      if (!valid()) { candidate.dispose(); return; }
      scene = candidate; scene.setEvent(currentEvent());
      if (playing) scene.setActive?.(true);
    } catch { fail(); }
    finally { if (token === sceneGeneration) loadingScene = false; }
  }

  const chosen = () => chooseVoice({browser: browserSpanishVoices(synthesis), server: serverVoices, pref: voicePref});

  function fillVoiceSelect() {
    const browser = win.SpeechSynthesisUtterance ? browserSpanishVoices(synthesis) : [];
    voiceSelect.replaceChildren();
    const auto = element('option', 'Automática'); auto.value = 'auto'; voiceSelect.append(auto);
    const group = (label, items) => {
      if (!items.length) return;
      const box = element('optgroup'); box.label = label;
      for (const [value, text] of items) { const option = element('option', text); option.value = value; box.append(option); }
      voiceSelect.append(box);
    };
    group('Voces del navegador', browser.map(voice => [`browser:${voice.voiceURI}`, `${voice.name} (${voice.lang})`]));
    group('Voces de este equipo (espeak-ng)', serverVoices.map(voice => [`server:${voice.id}`, voice.label]));
    const known = [...voiceSelect.querySelectorAll('option')].some(option => option.value === voicePref);
    voiceSelect.value = known ? voicePref : 'auto';
  }

  function refreshVoice() {
    if (dead) return;
    const voice = chosen();
    fillVoiceSelect();
    const supported = Boolean(voice) && (voice.kind === 'server' || Boolean(win.SpeechSynthesisUtterance));
    voiceInput.disabled = !supported; voiceSelect.disabled = !supported; voiceTest.disabled = !supported;
    voiceHelp.textContent = supported ? `Voz: ${voice.name}${voice.kind === 'server' ? ' (generada en este equipo)' : ' (local del navegador)'}.`
      : noVoiceHelp(serverReason, serverHint);
    voiceRescan.hidden = supported;
    if (!supported && voiceEnabled) { voiceEnabled = false; if (playing) narrate(); notify(); }
    voiceInput.checked = voiceEnabled;
  }

  // Las voces del equipo se piden una vez por página; si llegan, se refresca la lista de todas las instancias.
  const applyServerVoices = result => { if (dead) return; serverVoices = result.voices; serverHint = result.hint; serverReason = result.reason; refreshVoice(); };
  loadServerVoices(win).then(applyServerVoices);
  function rescanVoices() { voiceHelp.textContent = 'Buscando voces…'; resetServerVoices(); loadServerVoices(win).then(applyServerVoices); }

  async function speakServer(text, voiceId, signal) {
    const response = await win.fetch('/api/voice/speak', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, voice: voiceId, rate}), signal});
    if (!response.ok) throw new Error('voz no disponible');
    return response.blob();
  }

  /** «Probar voz»: una frase corta con la voz elegida, para saber si suena. */
  async function playSample() {
    const voice = chosen(); if (!voice || dead) return;
    pause(); stopSample();
    const text = 'Hola, soy tu guía en Bat’z.';
    voiceHelp.textContent = `Probando ${voice.name}…`;
    if (voice.kind === 'browser') {
      const speech = new win.SpeechSynthesisUtterance(text); speech.lang = voice.voice.lang; speech.voice = voice.voice; speech.rate = .92 * rate;
      speech.onend = () => { voiceHelp.textContent = `Voz: ${voice.name} (local del navegador).`; };
      speech.onerror = () => { voiceHelp.textContent = 'El navegador no pudo reproducir esa voz. Prueba otra.'; };
      sample = {speech}; try { synthesis.cancel(); synthesis.speak(speech); } catch { speech.onerror(); }
      return;
    }
    const abort = new win.AbortController(); sample = {abort};
    try {
      const blob = await speakServer(text, voice.id, abort.signal);
      if (abort.signal.aborted || dead) return;
      const url = win.URL.createObjectURL(blob), audio = new win.Audio(url);
      sample = {audio, url};
      audio.onended = () => { stopSample(); voiceHelp.textContent = `Voz: ${voice.name} (generada en este equipo).`; };
      await audio.play();
    } catch (error) {
      if (abort.signal.aborted) return;
      stopSample(); voiceHelp.textContent = 'No se pudo reproducir la voz del equipo. Revisa que espeak-ng esté instalado.';
    }
  }
  function stopSample() {
    if (!sample) return;
    sample.abort?.abort(); sample.speech && (sample.speech.onend = sample.speech.onerror = null);
    if (sample.audio) { sample.audio.onended = null; sample.audio.pause(); }
    if (sample.url) win.URL.revokeObjectURL(sample.url);
    sample = null;
  }

  function later(action, delay) {
    const id = win.setTimeout(() => { audioTimers.delete(id); action(); }, delay); audioTimers.add(id);
  }

  function stopAudio() {
    ++run;
    audioTimers.forEach(id => win.clearTimeout(id)); audioTimers.clear();
    if (utterance) { utterance.onstart = utterance.onboundary = utterance.onend = utterance.onerror = null; utterance = null; }
    stopSample();
    if (serverAbort) { serverAbort.abort(); serverAbort = null; }
    if (serverAudio) { serverAudio.audio.onplaying = serverAudio.audio.onended = serverAudio.audio.onerror = null; serverAudio.audio.pause(); win.URL.revokeObjectURL(serverAudio.url); serverAudio = null; }
    if (activePlayer === api) { synthesis?.cancel(); activePlayer = null; }
    scene?.talking(false);
  }

  function pause() {
    if (dead) return;
    playing = false; stopAudio(); scene?.setActive?.(false); render(); notify();
  }

  function advance() {
    if (!playing || !ready()) return;
    if (index === events.length - 1) {
      pause();
      const rootEvent = events.find(e => e.kind !== 'search' && e.kind !== 'premise');
      if (typeof rootEvent?.value === 'boolean') scene?.verdict(rootEvent.value);
      return;
    }
    go(index + 1);
  }

  function narrate() {
    stopAudio();
    if (!playing || !ready() || presentation !== 'expanded') return;
    activePlayer?.pause(); activePlayer = api;
    const token = run, event = currentEvent(), at = index;
    const valid = () => !dead && token === run && playing && ready() && index === at;
    const finish = () => {
      if (!valid()) return;
      stopAudio(); advance();
    };
    const choice = voiceEnabled ? chosen() : null;
    if (!choice || !event.text_es || (choice.kind === 'browser' && !win.SpeechSynthesisUtterance)) {
      later(finish, readingTime(event.text_es, rate)); return;
    }
    const failVoice = () => {
      if (!valid()) return;
      voiceEnabled = false; voiceInput.checked = false;
      voiceHelp.textContent = 'La narración no está disponible. El recorrido continúa sin audio.';
      notify(); narrate();
    };
    if (choice.kind === 'server') {
      // Audio generado en el equipo: se pide, se reproduce y la boca se reparte en su duración.
      const abort = new win.AbortController(); serverAbort = abort;
      speakServer(event.text_es, choice.id, abort.signal).then(blob => {
        if (!valid() || abort.signal.aborted) return;
        const url = win.URL.createObjectURL(blob), audio = new win.Audio(url);
        serverAudio = {audio, url};
        audio.onplaying = () => {
          if (!valid()) return;
          scene?.talking(true);
          const ms = (Number.isFinite(audio.duration) ? audio.duration : readingTime(event.text_es, rate) / 1000) * 1000;
          for (const item of wordTimings(event.text_es, word => scene?.syllableCount(word) ?? ((word.normalize('NFD').match(/[aeiouy]+/gi) || []).length || 1), ms)) {
            later(() => { if (valid()) scene?.say(item.word, 1, item.pause); }, item.at);
          }
        };
        audio.onended = finish; audio.onerror = failVoice;
        return audio.play();
      }).catch(() => { if (!abort.signal.aborted) failVoice(); });
      return;
    }
    const voice = choice.voice;
    const speech = new win.SpeechSynthesisUtterance(event.text_es); utterance = speech;
    speech.lang = voice.lang; speech.voice = voice; speech.rate = .92 * rate;
    let spoken = 0, gotWord = false;
    speech.onstart = () => {
      if (!valid()) return;
      scene?.talking(true);
      let ms = 0;
      for (const raw of event.text_es.match(/\S+/g) || []) {
        const word = raw.replace(/[,.;:!?¡¿()]/g, '');
        const beats = scene?.syllableCount(word) ?? ((word.normalize('NFD').match(/[aeiouy]+/gi) || []).length || 1);
        later(() => { if (valid() && !gotWord) scene?.say(word, speech.rate); }, ms);
        ms += Math.max(1, beats) * 185 / speech.rate + (/[,.;:!?)]$/.test(raw) ? 300 : 35);
      }
    };
    speech.onboundary = boundary => {
      if (!valid() || boundary.name && boundary.name !== 'word') return;
      gotWord = true;
      const suffix = event.text_es.slice(boundary.charIndex);
      const word = (boundary.charLength ? suffix.slice(0, boundary.charLength) : suffix).split(/[\s,.;:]/)[0];
      const hasPause = /[,.;:!?¡¿()]/.test(event.text_es.slice(spoken, boundary.charIndex));
      spoken = boundary.charIndex + word.length;
      scene?.say(word, speech.rate, hasPause);
    };
    speech.onend = finish;
    speech.onerror = () => {
      if (!valid()) return;
      voiceEnabled = false; voiceInput.checked = false;
      voiceHelp.textContent = 'La narración no está disponible. El recorrido continúa sin audio.';
      notify(); narrate();
    };
    try { synthesis.speak(speech); }
    catch { speech.onerror(); }
  }

  function start() {
    if (!ready() || presentation !== 'expanded' || doc.hidden) return;
    activePlayer?.pause(); playing = true; scene?.setActive?.(true);
    render(); notify(); narrate();
  }

  function go(target) {
    if (!ready() || target < 0 || target >= events.length) return;
    stopAudio(); index = target; render(); stepChanged(); notify();
    if (playing) narrate();
  }

  function pick(value) {
    if (!ready()) return;
    const target = caseIndex(events, index, value);
    if (target < 0) { sceneStatus.textContent = 'Ese elemento no tiene un caso disponible en este paso.'; return; }
    pause(); go(target);
  }

  function load(data) {
    if (dead) return;
    if (!data || typeof data.resultId !== 'string' || !data.resultId) throw new TypeError('resultId debe identificar el resultado.');
    if (payload?.resultId === data.resultId) return;
    if (data.story?.schema_version !== undefined && data.story.schema_version !== '1') throw new TypeError('Versión de guion incompatible.');
    pause(); fullscreen.exit(); releaseScene();
    // Copia independiente: el consumidor no puede mutar por accidente un guion en reproducción.
    payload = structuredClone(data); events = Array.isArray(payload.story?.events) ? payload.story.events : [];
    index = events.length ? 0 : null; stale = false; reason = ''; sceneFailed = false; presentation = 'closed';
    sceneStatus.textContent = ''; all.open = false; list.replaceChildren();
    for (const [i, event] of events.entries()) {
      const li = element('li');
      const b = button(`${i + 1}. ${eventLabel(event)} · ${event.text_es || ''}`, () => { pause(); go(i); });
      li.append(b); list.append(li);
    }
    render(); stepChanged(); notify();
  }

  function open() {
    if (dead || !events.length) return;
    if (!root.contains(doc.activeElement)) returnFocus = doc.activeElement;
    presentation = 'expanded'; render(); scene?.setActive?.(true); notify(); ensureScene();
  }
  function minimize() {
    if (dead || !events.length) return;
    const ownedFocus = root.contains(doc.activeElement);
    pause(); fullscreen.exit(); presentation = 'minimized'; releaseScene(); render(); notify();
    if (ownedFocus) restore.focus({preventScroll:true});
  }
  function close() {
    if (dead) return;
    const ownedFocus = root.contains(doc.activeElement);
    pause(); fullscreen.exit(); presentation = 'closed'; releaseScene(); render(); notify();
    if (ownedFocus && returnFocus?.isConnected) returnFocus.focus({preventScroll:true});
  }
  function invalidate(message = 'Los datos cambiaron. Vuelve a ejecutar la comprobación.') {
    if (dead || !events.length) return;
    pause(); fullscreen.exit(); stale = true; reason = message; releaseScene(); render(); notify();
  }
  function clear() {
    if (dead) return;
    pause(); fullscreen.exit(); releaseScene(); payload = null; events = []; index = null;
    stale = false; reason = ''; presentation = 'closed'; list.replaceChildren(); render(); notify();
  }
  function destroy() {
    if (dead) return;
    clear(); fullscreen.destroy(); controller.abort(); root.remove(); dead = true;
  }

  listen(voiceSelect, 'change', () => { voicePref = voiceSelect.value; saveVoicePref(win.localStorage, voicePref); refreshVoice(); if (playing) narrate(); notify(); });
  listen(voiceInput, 'change', () => { voiceEnabled = voiceInput.checked && !voiceInput.disabled; notify(); if (playing) narrate(); });
  listen(threeInput, 'change', () => {
    threeDEnabled = threeInput.checked; sceneFailed = false;
    if (!threeDEnabled) { releaseScene(); sceneStatus.textContent = 'Vista 2D activa.'; }
    else ensureScene();
    render(); notify();
  });
  listen(rateInput, 'change', () => { rate = Number(rateInput.value); notify(); if (playing) narrate(); });
  listen(synthesis, 'voiceschanged', refreshVoice);
  listen(doc, 'visibilitychange', () => { if (doc.hidden) pause(); });
  listen(root, 'keydown', event => {
    if (!fullscreen.isOn() || event.target.closest('input, select, textarea') || !ready()) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); go(index + 1); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); go(index - 1); }
  });
  // Método adicional para que el shell pueda salir de fullscreen sin cerrar la
  // presentación ni conocer sus clases o el respaldo de Safari.
  const api = {load, open, pause, minimize, close, invalidate, clear, destroy, getSnapshot: snapshot,
    exitFullscreen: () => { if (!dead) fullscreen.exit(); }};
  refreshVoice(); render();
  return api;
}
