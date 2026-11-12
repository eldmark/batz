import * as THREE from './vendor/three.module.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

// Escenario del paso a paso: el avatar a la izquierda explica; el dominio a la derecha es lo
// que señala. Cada gesto corresponde a un tipo de nodo verificado de la evaluación.

function same(a, b) { return typeof a === typeof b && a === b; }
function indexOf(domain, value) { return domain.findIndex(item => same(item, value)); }
const HEIGHT = 380;
const COLORS = {idle: 0x2f9c78, member: 0x62cfa6, outside: 0x6f7f79, yes: 0xa6f0b8, no: 0xf08aa0, edge: 0xd9b44a};

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
  avatar.position.set(count ? -2.1 : 0, -1.75, 0); avatar.scale.setScalar(1.55); avatar.rotation.y = count ? .22 : 0;
  scene.add(avatar);
  let mixer = null, current = null, wanted = 'Saluda';
  const clips = {};
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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
    mixer = new THREE.AnimationMixer(gltf.scene);
    for (const clip of gltf.animations) clips[clip.name] = clip;
    mixer.addEventListener('finished', event => {
      const name = event.action.getClip().name;
      if (name !== 'Senala') play('Idle');           // tras un gesto único vuelve al reposo
    });
    play(wanted);
    options.onReady?.();
  }, undefined, () => options.onError?.());

  // ── tamaño y cámara: encuadra avatar y dominio ──
  function resize() {
    const width = Math.max(container.clientWidth, 320);
    renderer.setSize(width, HEIGHT);
    camera.aspect = width / HEIGHT;
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

  const clock = new THREE.Clock();
  let frame;
  function draw() {
    const dt = Math.min(clock.getDelta(), .05);
    if (mixer && !reduceMotion) mixer.update(dt);
    const t = clock.elapsedTime;
    nodes.forEach((node, i) => {
      const s = node.mesh.scale.x + (node.target - node.mesh.scale.x) * Math.min(1, dt * 9);
      node.mesh.scale.setScalar(s);
      if (!reduceMotion) node.mesh.position.y = positions[i].y + Math.sin(t * 1.3 + i) * .035;
    });
    renderer.render(scene, camera);
    frame = requestAnimationFrame(draw);
  }
  draw();

  return {
    /** Refleja un paso verificado: resalta los elementos que toca y elige el gesto del avatar. */
    setEvent(event) {
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
    dispose() {
      cancelAnimationFrame(frame); observer.disconnect();
      for (const {mesh, label} of nodes) { mesh.material.dispose(); label.material.map.dispose(); label.material.dispose(); }
      for (const {line} of edges) { line.geometry.dispose(); line.material.dispose(); }
      avatar.traverse(o => { if (o.isMesh) { o.geometry.dispose(); (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => m.dispose()); } });
      sphere.dispose(); renderer.dispose(); renderer.domElement.remove();
    }
  };
}
