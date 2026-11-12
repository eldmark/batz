import * as THREE from './vendor/three.module.js';

function same(a, b) { return typeof a === typeof b && a === b; }
function indexOf(domain, value) { return domain.findIndex(item => same(item, value)); }

function labelSprite(text) {
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 96;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#f6fff7';
  ctx.font = 'bold 33px system-ui, sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(String(text), 128, 48, 238);
  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({map: texture, transparent: true, depthWrite: false});
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(1.35, .5, 1);
  return sprite;
}

export function createStoryScene(container, model) {
  if (model.domain.length > 12) throw new Error('Dominio demasiado grande para la vista 3D');
  const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(Math.max(container.clientWidth, 320), 300);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.append(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(46, Math.max(container.clientWidth, 320) / 300, .1, 100);
  camera.position.set(0, 4.2, 9.5); camera.lookAt(0, 0, 0);
  scene.add(new THREE.AmbientLight(0xffffff, 2.1));
  const light = new THREE.DirectionalLight(0xffffff, 3);
  light.position.set(3, 8, 6); scene.add(light);
  const group = new THREE.Group(); scene.add(group);
  const sphere = new THREE.SphereGeometry(.45, 28, 20);
  const nodes = [];
  const count = model.domain.length;
  const radius = Math.max(1.35, count * .43);
  const positions = model.domain.map((_, i) => {
    if (count === 1) return new THREE.Vector3(0, 0, 0);
    const angle = Math.PI * 2 * i / count;
    return new THREE.Vector3(radius * Math.cos(angle), .55 * radius * Math.sin(angle),
      .3 * radius * Math.sin(angle));
  });
  model.domain.forEach((element, i) => {
    const material = new THREE.MeshStandardMaterial({color: 0x2f9c78, metalness: .1, roughness: .42,
      emissive: 0x0b3324, emissiveIntensity: .16});
    const mesh = new THREE.Mesh(sphere, material);
    mesh.position.copy(positions[i]); group.add(mesh);
    const label = labelSprite(typeof element === 'string' ? element : String(element));
    label.position.copy(positions[i]).add(new THREE.Vector3(0, .73, 0)); group.add(label);
    nodes.push({mesh, label});
  });

  const edges = [];
  for (const [name, relation] of Object.entries(model.predicates)) {
    if (relation.arity !== 2) continue;
    for (const tuple of relation.tuples) {
      const a = indexOf(model.domain, tuple[0]), b = indexOf(model.domain, tuple[1]);
      if (a < 0 || b < 0) continue;
      const start = positions[a].clone(), end = positions[b].clone();
      if (a === b) end.add(new THREE.Vector3(.45, .65, .2));
      const geometry = new THREE.BufferGeometry().setFromPoints([start, end]);
      const material = new THREE.LineBasicMaterial({color: 0xd9b44a, linewidth: 2});
      const line = new THREE.Line(geometry, material);
      line.visible = false; group.add(line); edges.push({name, line});
    }
  }

  const onResize = () => {
    const width = Math.max(container.clientWidth, 320);
    camera.aspect = width / 300; camera.updateProjectionMatrix();
    renderer.setSize(width, 300);
  };
  const observer = new ResizeObserver(onResize); observer.observe(container);
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let frame;
  function draw() {
    if (!reduceMotion) group.rotation.y += .0025;
    renderer.render(scene, camera);
    frame = requestAnimationFrame(draw);
  }
  draw();

  return {
    setEvent(event) {
      const relation = event.relation ? model.predicates[event.relation] : null;
      const focused = (event.term_values?.length ? event.term_values :
        event.element !== null && event.element !== undefined ? [event.element] :
        Object.values(event.assignment || {}));
      nodes.forEach(({mesh}, i) => {
        const element = model.domain[i];
        const active = focused.some(value => same(value, element));
        let color = 0x2f9c78;
        if (relation?.arity === 1) {
          color = relation.tuples.some(tuple => same(tuple[0], element)) ? 0x62cfa6 : 0x6f7f79;
        }
        if (active) color = event.value ? 0xa6f0b8 : 0xf08aa0;
        mesh.material.color.setHex(color);
        mesh.scale.setScalar(active ? 1.22 : 1);
      });
      edges.forEach(({name, line}) => { line.visible = name === event.relation; });
    },
    dispose() {
      cancelAnimationFrame(frame); observer.disconnect();
      for (const {mesh, label} of nodes) {
        mesh.material.dispose(); label.material.map.dispose(); label.material.dispose();
      }
      for (const {line} of edges) { line.geometry.dispose(); line.material.dispose(); }
      sphere.dispose(); renderer.dispose(); renderer.domElement.remove();
    }
  };
}
