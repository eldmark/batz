import * as THREE from './vendor/three.module.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

// Escenario del paso a paso: el avatar a la izquierda explica; el dominio a la derecha es lo
// que señala. Cada gesto corresponde a un tipo de nodo verificado de la evaluación.

function same(a, b) { return typeof a === typeof b && a === b; }
function indexOf(domain, value) { return domain.findIndex(item => same(item, value)); }
const COLORS = {idle: 0x2f9c78, member: 0x62cfa6, outside: 0x6f7f79, yes: 0xa6f0b8, no: 0xf08aa0, edge: 0xd9b44a};
// Visemas: cada vocal de la palabra que se está diciendo abre la boca un instante; «o» y «u» la redondean.
const SYLLABLE = .11;       // segundos por vocal a velocidad 1
const HOLD = .15;           // cuánto dura abierta cada vocal

function labelSprite(text) {
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 96;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#f6fff7';
  ctx.font = '600 34px "JetBrains Mono NL", ui-monospace, monospace';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(String(text), 128, 48, 238);
  const texture = new THREE.CanvasTexture(canvas);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({map: texture, transparent: true, depthWrite: false}));
  sprite.scale.set(1.35, .5, 1);
  return sprite;
}

export function createStoryScene(container, model, options = {}) {
  const domain = model?.domain || [];
  if (domain.length > 12) throw new Error('Dominio demasiado grande para la vista 3D');
  const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.append(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, .1, 100);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x1b3a30, 2.4));
  const key = new THREE.DirectionalLight(0xffffff, 2.6); key.position.set(2.5, 6, 7); scene.add(key);
  // relleno cálido desde el frente: sin él, la piel del avatar toma el verde del suelo y se ve más morena
  const fill = new THREE.DirectionalLight(0xfff1e6, 1.2); fill.position.set(-3, 2.5, 9); scene.add(fill);

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
    const label = labelSprite(typeof element === 'string' ? element : String(element));
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
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Boca: morph targets «Boca_abierta» y «Boca_redonda» del GLB. Sin ellos, la cabeza asiente al hablar.
  const mouths = [];
  let head = null, nod = 0, speaking = false, mouthOpen = 0, mouthRound = 0;
  const visemes = [];

  function play(name) {
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
    avatar.add(gltf.scene);
    gltf.scene.traverse(object => {
      const names = object.morphTargetDictionary;
      if (object.isMesh && names && 'Boca_abierta' in names) mouths.push({mesh: object, open: names.Boca_abierta, round: names.Boca_redonda});
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
  }, undefined, () => options.onError?.());

  // ── tamaño y cámara: encuadra avatar y dominio; el alto lo decide el CSS (más bajo en el teléfono) ──
  function resize() {
    const width = Math.max(container.clientWidth, 260);
    const height = Math.max(container.clientHeight, 200);
    renderer.setSize(width, height);
    camera.aspect = width / height;
    const span = count ? 7.6 : 4.2;                   // ancho de escena que debe caber
    const distance = Math.max(8.2, span / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect));
    camera.position.set(0, .35, distance); camera.lookAt(0, .1, 0);
    camera.updateProjectionMatrix();
  }
  const observer = new ResizeObserver(resize); observer.observe(container); resize();

  // ── elegir un elemento con clic: «¿y con este?» ──
  const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2();
  function pick(event) {
    const box = renderer.domElement.getBoundingClientRect();
    pointer.set((event.clientX - box.left) / box.width * 2 - 1, -(event.clientY - box.top) / box.height * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    return raycaster.intersectObjects(nodes.map(n => n.mesh))[0]?.object.userData.index;
  }
  renderer.domElement.addEventListener('click', event => {
    const index = pick(event);
    if (index !== undefined) options.onPick?.(domain[index]);
  });
  renderer.domElement.addEventListener('pointermove', event => {
    renderer.domElement.style.cursor = pick(event) !== undefined ? 'pointer' : 'default';
  });

  const timer = new THREE.Timer();
  timer.connect(document);  // con la pestaña oculta no acumula tiempo
  let frame;

  function animateMouth(t, dt) {
    while (visemes.length && visemes[0].at + HOLD < t) visemes.shift();
    const viseme = visemes.find(v => v.at <= t);
    let open = speaking ? .06 : 0, round = 0;         // entre palabras, los labios quedan entreabiertos
    if (viseme) {
      if (viseme.round && mouths.some(m => m.round !== undefined)) round = viseme.strength;
      else open = viseme.strength;
    }
    const ease = Math.min(1, dt * 24);
    mouthOpen += (open - mouthOpen) * ease;
    mouthRound += (round - mouthRound) * ease;
    for (const {mesh, open: i, round: j} of mouths) {
      mesh.morphTargetInfluences[i] = mouthOpen;
      if (j !== undefined) mesh.morphTargetInfluences[j] = mouthRound;
    }
    if (!mouths.length && head && !reduceMotion) {      // respaldo: asiente con cada sílaba
      head.rotation.x -= nod;
      nod = (mouthOpen + mouthRound) * .1;
      head.rotation.x += nod;
    }
  }

  function draw(timestamp) {
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
    frame = requestAnimationFrame(draw);
  }
  frame = requestAnimationFrame(draw);

  return {
    /** Refleja un paso verificado: resalta los elementos que toca y elige el gesto del avatar. */
    setEvent(event) {
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
        if (active) color = event.value ? COLORS.yes : COLORS.no;
        node.mesh.material.color.setHex(color);
        node.target = active ? 1.28 : 1;
      });
      edges.forEach(({name, line}) => { line.visible = name === event.relation; });
      const pointing = count && focused.length && (event.kind === 'predicate' || event.kind === 'equality' || event.element !== null && event.element !== undefined);
      play(pointing ? 'Senala' : event.kind === 'quantifier' ? 'Explica' : event.kind === 'connective' ? 'Piensa' : 'Explica');
    },
    /** Reacción final al valor de la fórmula completa. */
    verdict(value) { play(value ? 'Verdadero' : 'Falso'); },
    gesture(name) { play(name); },
    /** La voz empezó o terminó de hablar. */
    talking(on) { speaking = on; if (!on) visemes.length = 0; },
    /** La voz va a decir `word`: una apertura de boca por vocal, al ritmo de la voz. */
    say(word, rate = 1) {
      const vowels = (word || '').toLowerCase().normalize('NFD').match(/[aeiou]/g) || [];
      const start = Math.max(timer.getElapsed(), (visemes.at(-1)?.at ?? -Infinity) + SYLLABLE / rate);
      vowels.slice(0, 8).forEach((vowel, i) => visemes.push({
        at: start + i * SYLLABLE / rate, round: vowel === 'o' || vowel === 'u',
        strength: vowel === 'a' ? 1 : vowel === 'i' || vowel === 'e' ? .55 : .85}));
    },
    /** Morph targets de boca encontrados en el modelo (para pruebas y para el respaldo). */
    mouthTargets() { return mouths.map(m => ({open: m.open, round: m.round})); },
    /** Cuánto está abierta y redondeada la boca ahora mismo (0 a 1). */
    mouthLevel() { return {open: mouthOpen, round: mouthRound}; },
    dispose() {
      cancelAnimationFrame(frame); observer.disconnect(); timer.dispose();
      for (const {mesh, label} of nodes) { mesh.material.dispose(); label.material.map.dispose(); label.material.dispose(); }
      for (const {line} of edges) { line.geometry.dispose(); line.material.dispose(); }
      avatar.traverse(o => { if (o.isMesh) { o.geometry.dispose(); (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => m.dispose()); } });
      sphere.dispose(); renderer.dispose(); renderer.domElement.remove();
    }
  };
}
