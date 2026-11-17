import * as THREE from './vendor/three.module.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

// Escenario del paso a paso: el avatar a la izquierda explica; el dominio a la derecha es lo
// que señala. Cada gesto corresponde a un tipo de nodo verificado de la evaluación.

function same(a, b) { return typeof a === typeof b && a === b; }
function indexOf(domain, value) { return domain.findIndex(item => same(item, value)); }
const COLORS = {idle: 0x2f9c78, member: 0x62cfa6, outside: 0x6f7f79, yes: 0xa6f0b8, no: 0xf08aa0, edge: 0xd9b44a};
// Lectura de labios. La voz avisa cuando empieza cada palabra; la palabra se parte en sílabas (español) y cada
// sílaba abre la boca con la forma de su vocal, al ritmo medido de la voz. Entre sílabas la boca se cierra un poco;
// en m, b, p y v los labios se juntan.
const SHAPES = {a: {open: .85, round: 0}, e: {open: .55, round: 0}, i: {open: .4, round: 0},
                o: {open: .45, round: .75}, u: {open: .2, round: .9}};
const SAID = {   // lo que la voz dice cuando el texto trae una letra suelta, una cifra o un símbolo
  b: 'be', c: 'ce', d: 'de', f: 'efe', g: 'ge', h: 'hache', j: 'jota', k: 'ka', l: 'ele', m: 'eme', n: 'ene',
  p: 'pe', q: 'cu', r: 'erre', s: 'ese', t: 'te', v: 'uve', w: 'uve doble', x: 'equis', z: 'zeta',
  0: 'cero', 1: 'uno', 2: 'dos', 3: 'tres', 4: 'cuatro', 5: 'cinco', 6: 'seis', 7: 'siete', 8: 'ocho', 9: 'nueve',
  '=': 'igual a', '≠': 'distinto de', '∧': 'y', '∨': 'o', '¬': 'no', '→': 'implica', '↔': 'si y solo si',
  '∀': 'para todo', '∃': 'existe', '∈': 'pertenece a', '⊥': 'falso'};
const LEAD = .04;           // la vocal suena un poco después de que empieza la palabra

/** Sílabas de una palabra tal como suena: forma de la boca de cada una y si los labios se juntan antes. */
export function syllables(word) {
  let w = (word || '').trim();
  if (!w) return [];
  if (w.length === 1 && SAID[w.toLowerCase()]) w = SAID[w.toLowerCase()];            // letra suelta o símbolo: su nombre
  else w = [...w].map(ch => (/\d/.test(ch) || (SAID[ch] && !/\p{L}/u.test(ch))) ? ` ${SAID[ch]} ` : ch).join('');
  w = w.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/qu(?=[ei])/g, 'k').replace(/gu(?=[ei])/g, 'g')                        // u muda: que, qui, gue, gui
    .replace(/y(?=$|[^aeiou])/g, 'i');                                               // «y» final suena «i»
  const out = [];
  for (const [, onset, group] of w.matchAll(/([^aeiou]*)([aeiou]+)/g)) {
    const parts = [];                                                                // fuerte + fuerte: hiato (dos sílabas)
    for (const ch of group) {
      const last = parts.at(-1);
      if (last && 'aeo'.includes(ch) && 'aeo'.includes(last.at(-1))) parts.push(ch);
      else if (last) parts[parts.length - 1] += ch;
      else parts.push(ch);
    }
    parts.forEach((part, k) => {
      const nucleus = [...part].find(c => 'aeo'.includes(c)) || part.at(-1);          // en el diptongo manda la fuerte
      out.push({...SHAPES[nucleus], closed: k === 0 && /[mbpv]$/.test(onset)});
    });
  }
  if (!out.length && /[\p{L}\p{N}]/u.test(w)) out.push({...SHAPES.e, closed: false}); // sigla sin vocales: una sílaba
  return out;
}

function labelSprite(text, color) {
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 96;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = color;
  ctx.font = '600 34px "JetBrains Mono NL", ui-monospace, monospace';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(String(text), 128, 48, 238);
  const texture = new THREE.CanvasTexture(canvas);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({map: texture, transparent: true, depthWrite: false}));
  sprite.scale.set(1.35, .5, 1);
  return sprite;
}

export function createStoryScene(container, model, options = {}) {
  let disposed = false, active = true, frame = null;
  const resources = object => {
    const geometries = new Set(), materials = new Set(), textures = new Set(), skeletons = new Set();
    object.traverse(o => {
      if (o.geometry) geometries.add(o.geometry);
      if (o.skeleton) skeletons.add(o.skeleton);
      for (const material of (Array.isArray(o.material) ? o.material : [o.material])) {
        if (!material) continue;
        materials.add(material);
        for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
      }
    });
    textures.forEach(texture => texture.dispose()); materials.forEach(material => material.dispose());
    geometries.forEach(geometry => geometry.dispose());
    skeletons.forEach(skeleton => skeleton.dispose());
  };
  const domain = model?.domain || [];
  if (domain.length > 12) throw new Error('Dominio demasiado grande para la vista 3D');
  const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.setAttribute('aria-hidden', 'true');
  container.append(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, .1, 100);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x1b3a30, 2.4));
  const key = new THREE.DirectionalLight(0xffffff, 2.6); key.position.set(2.5, 6, 7); scene.add(key);
  // relleno cálido desde el frente: sin él, la piel del avatar toma el verde del suelo y se ve más morena
  const fill = new THREE.DirectionalLight(0xfff4ec, .9); fill.position.set(-3, 2.5, 9); scene.add(fill);

  // ── dominio: un arco a la derecha del avatar ──
  const stage = new THREE.Group(); scene.add(stage);
  const sphere = new THREE.SphereGeometry(.42, 28, 20);
  const count = domain.length;
  const radius = Math.max(1.15, count * .36);
  const centre = new THREE.Vector3(count ? 1.9 : 0, .55, 0);
  const positions = domain.map((_, i) => {
    if (count === 1) return centre.clone();
    const angle = Math.PI * 2 * i / count + Math.PI / 2;
    return centre.clone().add(new THREE.Vector3(radius * Math.cos(angle), radius * .78 * Math.sin(angle), .25 * Math.sin(angle)));
  });
  const nodes = domain.map((element, i) => {
    const material = new THREE.MeshStandardMaterial({color: COLORS.idle, roughness: .4, metalness: .05, emissive: 0x0b3324, emissiveIntensity: .18});
    const mesh = new THREE.Mesh(sphere, material);
    mesh.position.copy(positions[i]); mesh.userData.index = i; stage.add(mesh);
    const textColor = getComputedStyle(container).getPropertyValue('--text').trim() || '#292f2d';
    const label = labelSprite(typeof element === 'string' ? element : String(element), textColor);
    label.position.copy(positions[i]).add(new THREE.Vector3(0, .7, 0)); stage.add(label);
    return {mesh, label, target: 1};
  });
  const edges = [];
  for (const [name, relation] of Object.entries(model?.predicates || {})) {
    if (relation.arity !== 2) continue;
    for (const tuple of relation.tuples) {
      const a = indexOf(domain, tuple[0]), b = indexOf(domain, tuple[1]);
      if (a < 0 || b < 0) continue;
      const start = positions[a].clone(), end = positions[b].clone();
      if (a === b) end.add(new THREE.Vector3(.45, .6, .2));
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([start, end]), new THREE.LineBasicMaterial({color: COLORS.edge}));
      line.visible = false; stage.add(line); edges.push({name, line});
    }
  }

  // ── avatar ──
  const avatar = new THREE.Group();
  // Avatar de proporciones reales (1,78 m): encuadre de medio cuerpo para que la cara se vea grande.
  const AVATAR_SCALE = 5.0;
  avatar.position.set(count ? -2.55 : 0, 1.95 - 1.78 * AVATAR_SCALE, 0); avatar.scale.setScalar(AVATAR_SCALE); avatar.rotation.y = count ? .22 : 0;
  scene.add(avatar);
  let mixer = null, current = null, wanted = 'Saluda';
  const clips = {};
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let reduceMotion = motion.matches;
  // Boca: morph targets «Boca_abierta» y «Boca_redonda» del GLB. Sin ellos, la cabeza asiente al hablar.
  const mouths = [];
  let head = null, nod = 0, speaking = false, mouthOpen = 0, mouthRound = 0;
  const visemes = [];
  let secPerSyllable = null, lastWord = null;      // ritmo de la voz, medido entre palabras
  let mouthWasOpen = false;

  function play(name) {
    if (disposed) return;
    wanted = name;
    if (!mixer || !clips[name]) return;
    const loop = name === 'Idle' || name === 'Explica' || name === 'Piensa';
    const action = mixer.clipAction(clips[name]);
    action.reset(); action.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, loop ? Infinity : 1);
    action.clampWhenFinished = name === 'Senala';   // se queda señalando hasta el siguiente paso
    if (reduceMotion) { mixer.stopAllAction(); action.play(); action.time = Math.min(clips[name].duration * .45, .6); action.paused = true; }
    else { if (current && current !== action) action.crossFadeFrom(current, .28, false); action.play(); }
    current = action;
  }

  new GLTFLoader().load('/avatar/logos.glb', gltf => {
    if (disposed) { resources(gltf.scene); return; }
    avatar.add(gltf.scene);
    gltf.scene.traverse(object => {
      const names = object.morphTargetDictionary;
      if (object.isMesh && names && 'Boca_abierta' in names) mouths.push({mesh: object, open: names.Boca_abierta, round: names.Boca_redonda, blink: names.Parpadeo});
    });
    head = gltf.scene.getObjectByName('head');
    mixer = new THREE.AnimationMixer(gltf.scene);
    for (const clip of gltf.animations) clips[clip.name] = clip;
    mixer.addEventListener('finished', event => {
      const name = event.action.getClip().name;
      if (name !== 'Senala') play('Idle');           // tras un gesto único vuelve al reposo
    });
    play(wanted);
    options.onReady?.();
  }, undefined, error => { if (!disposed) options.onError?.(error); });

  // ── tamaño y cámara: encuadra avatar y dominio; el alto lo decide el CSS (más bajo en el teléfono) ──
  function resize() {
    if (disposed) return;
    const width = Math.max(container.clientWidth || 260, 1);
    const height = Math.max(container.clientHeight, 200);
    renderer.setSize(width, height);
    camera.aspect = width / height;
    const span = count ? 7.6 : 4.2;                   // ancho de escena que debe caber
    const distance = Math.max(8.2, span / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect));
    camera.position.set(0, .35, distance); camera.lookAt(0, .1, 0);
    camera.updateProjectionMatrix();
    schedule();
  }
  const observer = new ResizeObserver(resize); observer.observe(container); resize();

  // ── elegir un elemento con clic: «¿y con este?» ──
  const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2();
  function pick(event) {
    const box = renderer.domElement.getBoundingClientRect();
    pointer.set((event.clientX - box.left) / box.width * 2 - 1, -(event.clientY - box.top) / box.height * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    return raycaster.intersectObjects(nodes.filter(n => n.label.visible).map(n => n.mesh))[0]?.object.userData.index;
  }
  function onClick(event) {
    const index = pick(event);
    if (index !== undefined) options.onPick?.(domain[index]);
  }
  function onPointerMove(event) {
    renderer.domElement.style.cursor = pick(event) !== undefined ? 'pointer' : 'default';
  }
  const onContextLost = event => {
    event.preventDefault();
    if (!disposed) options.onError?.(new Error('Se perdió el contexto WebGL.'));
  };
  renderer.domElement.addEventListener('click', onClick);
  renderer.domElement.addEventListener('pointermove', onPointerMove);
  renderer.domElement.addEventListener('webglcontextlost', onContextLost);

  const timer = new THREE.Timer();
  timer.connect(document);  // con la pestaña oculta no acumula tiempo

  // Parpadeo: morph target «Parpadeo», cada 2–6 s al azar (a veces doble); cierra en 70 ms y abre en 110 ms.
  let nextBlink = 1.5 + Math.random() * 2, blinkStart = -1;
  function blinkLevel(phase) {
    if (phase < .07) return phase / .07;
    if (phase < .12) return 1;
    return Math.max(0, 1 - (phase - .12) / .11);
  }
  function animateBlink(t) {
    if (reduceMotion) return;
    if (blinkStart < 0 && t >= nextBlink) blinkStart = t;
    let level = 0;
    if (blinkStart >= 0) {
      const phase = t - blinkStart;
      level = blinkLevel(phase);
      if (phase >= .23) { blinkStart = -1; nextBlink = t + (Math.random() < .15 ? .18 : 2 + Math.random() * 4); }
    }
    for (const {mesh, blink} of mouths) if (blink !== undefined) mesh.morphTargetInfluences[blink] = level;
  }

  function animateMouth(t, dt) {
    // Manda lo que suena en este instante. Con cuadros lentos (equipo cargado, teléfono) una sílaba entera puede caer
    // entre dos cuadros: entonces se muestra, salvo que el cuadro anterior ya estuviera abierto (así la boca alterna
    // en vez de quedarse abierta).
    const from = t - dt;
    while (visemes.length && visemes[0].until < from) visemes.shift();
    const now = visemes.find(v => v.at <= t && t < v.until);
    let open = speaking ? .06 : 0, round = 0;         // entre palabras y entre sílabas, los labios quedan entreabiertos
    if (now) {
      if (t < now.close) open = 0;                    // m, b, p, v: labios juntos antes de la vocal
      else { open = now.open; round = now.round; }
    } else {
      const skipped = visemes.find(v => v.close > from && v.until <= t);
      if (skipped && !mouthWasOpen) { open = skipped.open; round = skipped.round; }
    }
    mouthWasOpen = open > .2 || round > .2;
    if (round && !mouths.some(m => m.round !== undefined)) { open = Math.max(open, round * .7); round = 0; }   // modelo sin forma redonda
    const ease = Math.min(1, dt * 26);
    mouthOpen += (open - mouthOpen) * ease;
    mouthRound += (round - mouthRound) * ease;
    for (const {mesh, open: i, round: j} of mouths) {
      mesh.morphTargetInfluences[i] = mouthOpen;
      if (j !== undefined) mesh.morphTargetInfluences[j] = mouthRound;
    }
    animateBlink(t);
    if (!mouths.length && head && !reduceMotion) {      // respaldo: asiente con cada sílaba
      head.rotation.x -= nod;
      nod = (mouthOpen + mouthRound) * .1;
      head.rotation.x += nod;
    }
  }

  function draw(timestamp) {
    frame = null;
    if (disposed || document.hidden) return;
    timer.update(timestamp);
    const dt = Math.min(timer.getDelta(), .05);
    if (head && nod) { head.rotation.x -= nod; nod = 0; }  // la animación pone su pose; el gesto de hablar va encima
    if (mixer && !reduceMotion) mixer.update(dt);
    const t = timer.getElapsed();
    animateMouth(t, dt);
    nodes.forEach((node, i) => {
      const s = node.mesh.scale.x + (node.target - node.mesh.scale.x) * Math.min(1, dt * 9);
      node.mesh.scale.setScalar(s);
      if (!reduceMotion) node.mesh.position.y = positions[i].y + Math.sin(t * 1.3 + i) * .035;
    });
    renderer.render(scene, camera);
    if (active) schedule();
  }
  function schedule() {
    if (!disposed && frame === null && !document.hidden) frame = requestAnimationFrame(draw);
  }
  function onVisibility() { if (!document.hidden && active) schedule(); }
  function onMotion() {
    reduceMotion = motion.matches;
    for (const {mesh, blink} of mouths) if (blink !== undefined) mesh.morphTargetInfluences[blink] = 0;
    play(wanted); schedule();
  }
  document.addEventListener('visibilitychange', onVisibility);
  motion.addEventListener('change', onMotion);
  schedule();

  return {
    /** Refleja un paso verificado: resalta los elementos que toca y elige el gesto del avatar. */
    setEvent(event) {
      if (disposed) return;
      schedule();
      if (event.kind === 'search') {
        // Búsqueda: solo existen los elementos del tamaño que se prueba; al hallarlo, el avatar lo presenta.
        const found = event.phase === 'found';
        nodes.forEach((node, i) => {
          const visible = i < event.size;
          node.target = visible ? (found ? 1.18 : 1) : .001;
          node.label.visible = visible;
          node.mesh.material.color.setHex(found && visible ? COLORS.yes : COLORS.idle);
        });
        edges.forEach(({line}) => { line.visible = false; });
        play(found ? 'Saluda' : 'Piensa');
        return;
      }
      nodes.forEach(node => { node.label.visible = true; });
      if (event.kind === 'premise') {
        nodes.forEach(node => { node.target = 1; node.mesh.material.color.setHex(COLORS.idle); });
        edges.forEach(({line}) => { line.visible = false; });
        play('Explica');
        return;
      }
      const relation = event.relation ? model?.predicates?.[event.relation] : null;
      const focused = (event.term_values?.length ? event.term_values :
        event.element !== null && event.element !== undefined ? [event.element] :
        Object.values(event.assignment || {}));
      nodes.forEach((node, i) => {
        const element = domain[i];
        const active = focused.some(value => same(value, element));
        let color = COLORS.idle;
        if (relation?.arity === 1) color = relation.tuples.some(tuple => same(tuple[0], element)) ? COLORS.member : COLORS.outside;
        if (active && typeof event.value === 'boolean') color = event.value ? COLORS.yes : COLORS.no;
        node.mesh.material.color.setHex(color);
        node.target = active ? 1.28 : 1;
      });
      edges.forEach(({name, line}) => { line.visible = name === event.relation; });
      const pointing = count && focused.length && (event.kind === 'predicate' || event.kind === 'equality' || event.element !== null && event.element !== undefined);
      play(pointing ? 'Senala' : event.kind === 'quantifier' ? 'Explica' : event.kind === 'connective' ? 'Piensa' : 'Explica');
    },
    /** Reacción final al valor de la fórmula completa. */
    verdict(value) { active = true; play(value ? 'Verdadero' : 'Falso'); schedule(); },
    gesture(name) { play(name); },
    /** La voz empezó o terminó de hablar. */
    talking(on) {
      speaking = on; visemes.length = 0; lastWord = null; secPerSyllable = null;
      if (!on) {
        mouthOpen = mouthRound = 0;
        for (const {mesh, open, round} of mouths) {
          mesh.morphTargetInfluences[open] = 0;
          if (round !== undefined) mesh.morphTargetInfluences[round] = 0;
        }
      }
      schedule();
    },
    /** Detiene el bucle al pausar o esconder el reproductor, sin perder su pose. */
    setActive(on) { active = Boolean(on); if (active) schedule(); },
    /** La voz empieza a decir `word`; `pause`: antes hubo una pausa (coma, punto), así que ese hueco no mide el ritmo. */
    say(word, rate = 1, pause = false) {
      const now = timer.getElapsed();
      secPerSyllable ??= .15 / rate;
      if (lastWord?.count && !pause) {                // ritmo real: lo que tardó la palabra anterior, por sílaba
        const measured = (now - lastWord.at) / lastWord.count;
        if (measured > .06 && measured < .45) secPerSyllable += (measured - secPerSyllable) * .4;
      }
      const shapes = syllables(word);
      lastWord = {at: now, count: shapes.length};
      visemes.length = 0;                             // lo pendiente de la palabra anterior ya no va: la voz siguió
      const step = Math.min(secPerSyllable, .3);
      shapes.slice(0, 12).forEach((s, i) => {
        const at = now + LEAD + i * step;
        visemes.push({at, close: s.closed ? at + step * .3 : at, until: at + step * .8, open: s.open, round: s.round});
      });
    },
    /** Cuántas sílabas suena `word` (letras, cifras y símbolos por su nombre). */
    syllableCount(word) { return syllables(word).length; },
    /** Morph targets de boca encontrados en el modelo (para pruebas y para el respaldo). */
    mouthTargets() { return mouths.map(m => ({open: m.open, round: m.round, blink: m.blink})); },
    /** Cuánto están cerrados los párpados ahora mismo (0 a 1). */
    blinkLevel() { return mouths.find(m => m.blink !== undefined)?.mesh.morphTargetInfluences[mouths.find(m => m.blink !== undefined).blink] ?? 0; },
    /** Cuánto está abierta y redondeada la boca ahora mismo (0 a 1). */
    mouthLevel() { return {open: mouthOpen, round: mouthRound}; },
    dispose() {
      if (disposed) return;
      disposed = true;
      cancelAnimationFrame(frame); observer.disconnect(); timer.dispose();
      document.removeEventListener('visibilitychange', onVisibility); motion.removeEventListener('change', onMotion);
      renderer.domElement.removeEventListener('click', onClick);
      renderer.domElement.removeEventListener('pointermove', onPointerMove);
      renderer.domElement.removeEventListener('webglcontextlost', onContextLost);
      mixer?.stopAllAction();
      resources(scene); if (!nodes.length) sphere.dispose(); renderer.dispose(); renderer.domElement.remove();
    }
  };
}
