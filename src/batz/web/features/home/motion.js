// Micro-interacciones de Inicio. Solo transform, opacity y clip-path; sin librerías.
// Con prefers-reduced-motion no se añade ningún estado oculto ni se anima nada: todo se ve de inmediato.
const SVG = 'http://www.w3.org/2000/svg';
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));

/** Tres hebras trenzadas (verde, ciruela, azul) que forman el hilo guía. Una capa tenue y otra que se dibuja. */
export function braid() {
  const wrap = document.createElement('div');
  wrap.className = 'home-spine'; wrap.setAttribute('aria-hidden', 'true');
  const PERIOD = 5, H = 100, A = 6.5, C = 10;
  const strand = (phase) => {
    let d = '';
    const x = (y) => C + A * Math.sin((2 * Math.PI * y) / PERIOD + phase);
    const dx = (y) => A * (2 * Math.PI / PERIOD) * Math.cos((2 * Math.PI * y) / PERIOD + phase);
    for (let y = 0; y < H; y += 1) {
      const y1 = y + 1;
      const c1 = x(y) + dx(y) / 3, c2 = x(y1) - dx(y1) / 3;
      d += `${y === 0 ? `M${x(0).toFixed(2)} 0` : ''}C${c1.toFixed(2)} ${(y + 1 / 3).toFixed(2)} ${c2.toFixed(2)} ${(y1 - 1 / 3).toFixed(2)} ${x(y1).toFixed(2)} ${y1}`;
    }
    return d;
  };
  for (const layer of ['track', 'drawn']) {
    const svg = document.createElementNS(SVG, 'svg');
    svg.setAttribute('class', `spine-${layer}`); svg.setAttribute('viewBox', `0 0 20 ${H}`);
    svg.setAttribute('preserveAspectRatio', 'none'); svg.setAttribute('focusable', 'false');
    [0, 2.094, 4.189].forEach((phase, i) => {
      const p = document.createElementNS(SVG, 'path');
      p.setAttribute('d', strand(phase)); p.setAttribute('class', `strand s${i}`);
      svg.append(p);
    });
    wrap.append(svg);
  }
  return wrap;
}

/** Activa aparición escalonada, hilo con el scroll, contadores y foco de luz. Devuelve la función que lo libera todo. */
export function enhanceHome(root) {
  const mqReduce = matchMedia('(prefers-reduced-motion: reduce)');
  const cleanups = [];
  let live = false;
  const stop = () => { while (cleanups.length) cleanups.pop()(); live = false; root.classList.remove('rv-on'); };

  function start() {
    if (live || mqReduce.matches || !('IntersectionObserver' in window)) return;
    live = true;
    // Estados ocultos solo cuando todo lo demás está listo para revelarlos.
    root.querySelectorAll('[data-rv]').forEach((el) => {
      const sec = el.closest('[data-sec]');
      const sibs = sec ? [...sec.querySelectorAll('[data-rv]')] : [el];
      el.style.setProperty('--i', String(Math.min(sibs.indexOf(el), 5)));
    });
    root.classList.add('rv-on');
    const targets = [...root.querySelectorAll('[data-rv],[data-sec]')];
    let pending = targets.length;
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        e.target.classList.add('in'); io.unobserve(e.target); pending -= 1;
        e.target.querySelectorAll('[data-count]').forEach(countUp);
        if (e.target.matches('[data-count]')) countUp(e.target);
      }
      if (pending <= 0) io.disconnect();
    }, {threshold: 0.12, rootMargin: '0px 0px -6% 0px'});
    targets.forEach((t) => io.observe(t));
    cleanups.push(() => io.disconnect());

    // Contadores: suben una sola vez, con raf, solo cambian texto.
    const counted = new WeakSet();
    const rafs = new Set();
    function countUp(el) {
      if (counted.has(el)) return; counted.add(el);
      const end = Number(el.dataset.count), t0 = performance.now(), dur = 900;
      const tick = (now) => {
        const k = clamp((now - t0) / dur);
        el.textContent = String(Math.round(end * (1 - Math.pow(2, -10 * k))));
        if (k < 1) rafs.add(requestAnimationFrame(tick)); else el.textContent = String(end);
      };
      el.textContent = '0';
      rafs.add(requestAnimationFrame(tick));
    }
    cleanups.push(() => { rafs.forEach(cancelAnimationFrame); root.querySelectorAll('[data-count]').forEach((el) => { el.textContent = el.dataset.count; }); });

    // Hilo que se dibuja con el scroll, solo mientras la columna es visible.
    const flow = root.querySelector('.home-flow'), drawn = root.querySelector('.spine-drawn');
    if (flow && drawn) {
      let frame = 0, listening = false;
      const paint = () => {
        frame = 0;
        const r = flow.getBoundingClientRect();
        const p = clamp((innerHeight * 0.72 - r.top) / Math.max(r.height, 1));
        drawn.style.clipPath = `inset(0 0 ${((1 - p) * 100).toFixed(2)}% 0)`;
      };
      const onScroll = () => { if (!frame) frame = requestAnimationFrame(paint); };
      const setListening = (on) => {
        if (on === listening) return; listening = on;
        const f = on ? 'addEventListener' : 'removeEventListener';
        document[f]('scroll', onScroll, {capture: true, passive: true});
        window[f]('resize', onScroll, {passive: true});
        if (on) paint();
      };
      drawn.style.clipPath = 'inset(0 0 100% 0)';
      const vis = new IntersectionObserver((es) => setListening(es.some((e) => e.isIntersecting)), {rootMargin: '10% 0px'});
      vis.observe(flow);
      cleanups.push(() => { vis.disconnect(); setListening(false); if (frame) cancelAnimationFrame(frame); drawn.style.clipPath = ''; });
    }
  }

  // Foco de luz que sigue al puntero: solo puntero fino, y se mueve con transform.
  if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    for (const tool of root.querySelectorAll('.home-tool')) {
      const spot = tool.querySelector('.tool-spot'); if (!spot) continue;
      let rect = null;
      const enter = () => { rect = tool.getBoundingClientRect(); tool.classList.add('is-pointer'); };
      const move = (e) => { if (e.pointerType !== 'mouse') return; if (!rect) enter(); spot.style.transform = `translate3d(${(e.clientX - rect.left).toFixed(1)}px, ${(e.clientY - rect.top).toFixed(1)}px, 0)`; };
      const leave = () => { rect = null; tool.classList.remove('is-pointer'); };
      tool.addEventListener('pointerenter', enter); tool.addEventListener('pointermove', move); tool.addEventListener('pointerleave', leave);
      cleanups.push(() => { tool.removeEventListener('pointerenter', enter); tool.removeEventListener('pointermove', move); tool.removeEventListener('pointerleave', leave); });
    }
  }

  const onMq = () => { if (mqReduce.matches) stop(); else start(); };
  mqReduce.addEventListener('change', onMq);
  start();
  return () => { mqReduce.removeEventListener('change', onMq); stop(); };
}
