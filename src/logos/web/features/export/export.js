// Exportar un resultado: documento HTML autónomo (sin recursos externos) para guardar, imprimir o llevar a PDF.
// Funciones puras que construyen texto; solo `download` y `printHtml` tocan el DOM.
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[ch]));
const label = value => (typeof value === 'string' ? JSON.stringify(value) : String(value));
const tuple = items => `(${items.map(label).join(', ')})`;

const STYLE = `
  :root { color-scheme: light; }
  body { font: 16px/1.55 "IBM Plex Sans", system-ui, sans-serif; color: #292f2d; margin: 0; background: #fff; }
  main { max-width: 820px; margin: 0 auto; padding: 32px 28px 48px; }
  header { border-bottom: 4px solid #0dac7f; padding-bottom: 12px; margin-bottom: 24px; }
  header p { margin: 0; color: #56605c; font-size: 13px; letter-spacing: .06em; text-transform: uppercase; }
  h1 { font: 600 28px/1.25 "Literata", Georgia, serif; margin: 4px 0 0; }
  h2 { font: 600 20px/1.3 "Literata", Georgia, serif; margin: 28px 0 8px; }
  code, pre { font-family: "JetBrains Mono NL", ui-monospace, monospace; }
  code.formula { display: block; font-size: 20px; padding: 10px 14px; background: #f5f7f6; border-left: 4px solid #7adbb4; overflow-wrap: anywhere; }
  .verdict { display: inline-block; padding: 6px 16px; border-radius: 4px; font: 600 28px/1.2 "Literata", Georgia, serif; }
  .verdict.true { background: #d4f7e5; color: #005339; } .verdict.false { background: #ffe6e8; color: #722837; } .verdict.neutral { background: #eaeeec; color: #292f2d; }
  table { border-collapse: collapse; margin: 6px 0 12px; } th, td { border: 1px solid #bdc7c2; padding: 3px 10px; text-align: left; font-size: 14px; }
  ol.fitch { list-style: none; padding: 0; margin: 8px 0; font-family: "JetBrains Mono NL", ui-monospace, monospace; font-size: 14px; }
  ol.fitch li { display: grid; grid-template-columns: 2.5em 1fr auto; gap: 8px; padding: 2px 0; } ol.fitch .why { color: #56605c; }
  ul.tree, ul.tree ul { list-style: none; padding-left: 18px; border-left: 2px solid #d6ddd9; } ul.tree { border-left: 0; padding-left: 0; }
  .note { color: #56605c; font-size: 14px; }
  footer { margin-top: 36px; padding-top: 10px; border-top: 1px solid #d6ddd9; color: #56605c; font-size: 12px; }
  @media print { main { padding: 0; } a { color: inherit; text-decoration: none; } }`;

function page(title, body) {
  const date = new Date().toLocaleDateString('es', {year: 'numeric', month: 'long', day: 'numeric'});
  return `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} · Bat’z</title><style>${STYLE}</style></head><body><main>
<header><p>Bat’z · el hilo de la lógica</p><h1>${esc(title)}</h1></header>${body}
<footer>Generado por Bat’z el ${esc(date)}. La verdad se evalúa en la interpretación indicada: verdadera aquí no significa válida en todos los modelos.</footer></main></body></html>`;
}

/** Interpretación: dominio, constantes, funciones y relaciones, como tablas. */
export function modelHtml(model) {
  if (!model) return '';
  const parts = [`<p>Dominio D = {${(model.domain || []).map(label).map(esc).join(', ')}}</p>`];
  const constants = Object.entries(model.constants || {});
  if (constants.length) parts.push(`<table><tr><th>Constante</th><th>Valor</th></tr>${constants.map(([name, value]) => `<tr><td><code>${esc(name)}</code></td><td>${esc(label(value))}</td></tr>`).join('')}</table>`);
  for (const [name, spec] of Object.entries(model.functions || {})) {
    parts.push(`<table><tr><th>Entrada de <code>${esc(name)}</code></th><th>Valor</th></tr>${spec.table.map(([args, value]) => `<tr><td>${esc(tuple(args))}</td><td>${esc(label(value))}</td></tr>`).join('')}</table>`);
  }
  for (const [name, spec] of Object.entries(model.predicates || {})) {
    parts.push(`<p><code>${esc(name)}</code> es verdadera exactamente en: ${spec.tuples.length ? spec.tuples.map(t => esc(tuple(t))).join(', ') : 'ninguna tupla'}.</p>`);
  }
  return parts.join('');
}

function explanationHtml(data) {
  if (!data) return '';
  const env = data.assignment?.length ? ` <span class="note">con ${data.assignment.map(([name, value]) => `${esc(name)} = ${esc(label(value))}`).join(', ')}</span>` : '';
  const details = (data.details || []).map(line => `<div class="note">${esc(line)}</div>`).join('');
  const kids = (data.children || []).map(child => `<li>${explanationHtml(child)}</li>`).join('');
  return `<div><strong>${data.value ? 'V' : 'F'}</strong> <code>${esc(data.formula)}</code>${env} — ${esc(data.summary)}${details}</div>${kids ? `<ul class="tree">${kids}</ul>` : ''}`;
}

export function fitchHtml(lines) {
  return `<ol class="fitch">${lines.map(line => `<li><span>${esc(line.n)}</span><span>${'│ '.repeat(line.depth || 0)}${line.flag ? `<em>${esc(line.flag)}</em> ` : ''}${esc(line.formula || '')}</span><span class="why">${esc(line.refs?.length ? `${line.label} ${line.refs.join(', ')}` : line.label)}</span></li>`).join('')}</ol>`;
}

/** Resultado de Evaluar: fórmula, entorno, veredicto, modelo y razones. */
export function buildEvaluationHtml({formula, assignment = {}, value, explanation, model}) {
  const env = Object.entries(assignment);
  const body = `<h2>Fórmula</h2><code class="formula">${esc(formula)}</code>
${env.length ? `<p class="note">Entorno: ${env.map(([k, v]) => `${esc(k)} = ${esc(label(v))}`).join(', ')}</p>` : ''}
<h2>Resultado</h2><p><span class="verdict ${value ? 'true' : 'false'}">${value ? 'Verdadero' : 'Falso'}</span></p><p>${esc(explanation?.summary)}</p>
<h2>Modelo</h2>${modelHtml(model)}<h2>Por qué</h2>${explanationHtml(explanation)}`;
  return page('Evaluación de una fórmula en un modelo', body);
}

/** Resultado de Demostrar: premisas, conclusión y prueba, contramodelo o búsqueda inconclusa. */
export function buildProofHtml({premises = [], conclusion = '', result}) {
  const head = `<h2>Consecuencia planteada</h2>${premises.length ? premises.map(p => `<code class="formula">${esc(p)}</code>`).join('') : '<p class="note">Sin premisas.</p>'}<p>⊢</p><code class="formula">${esc(conclusion)}</code>`;
  let tail;
  if (result.status === 'proved') {
    tail = `<h2>Resultado</h2><p><span class="verdict true">Prueba verificada</span></p><p class="note">Derivación aceptada por el verificador independiente.</p>${fitchHtml(result.fitch)}`;
  } else if (result.status === 'refuted' && result.countermodel) {
    const found = result.countermodel;
    tail = `<h2>Resultado</h2><p><span class="verdict false">Contramodelo verificado</span></p><p>La conclusión no se sigue: en este modelo las premisas son verdaderas y la conclusión, falsa.</p>${modelHtml(found.model)}${found.explanation ? `<h2>Por qué falla la conclusión</h2>${explanationHtml(found.explanation)}` : ''}`;
  } else if (result.status === 'refuted') {
    // el servidor entrega la valuación como lista de pares [letra, valor]
    const valuation = Array.isArray(result.valuation) ? result.valuation : Object.entries(result.valuation || {});
    tail = `<h2>Resultado</h2><p><span class="verdict false">Contramodelo verificado</span></p><p>Valuación proposicional que hace verdaderas las premisas y falsa la conclusión${valuation.length ? `: ${valuation.map(([k, v]) => `${esc(k)} = ${v ? 'V' : 'F'}`).join(', ')}` : ''}.</p>`;
  } else {
    tail = `<h2>Resultado</h2><p><span class="verdict neutral">Búsqueda inconclusa</span></p><p>Inconcluso no significa falso: la consecuencia queda sin decidir dentro de los límites de búsqueda.</p>`;
  }
  return page('Consecuencia lógica', head + tail);
}

export function download(filename, html) {
  const url = URL.createObjectURL(new Blob([html], {type: 'text/html;charset=utf-8'}));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename;
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Imprime el documento en un marco oculto; el diálogo del navegador permite guardarlo como PDF. */
export function printHtml(html) {
  const frame = document.createElement('iframe');
  frame.setAttribute('aria-hidden', 'true'); frame.style.cssText = 'position:fixed;width:0;height:0;border:0;right:0;bottom:0';
  frame.srcdoc = html;
  frame.addEventListener('load', () => {
    frame.contentWindow.focus(); frame.contentWindow.print();
    setTimeout(() => frame.remove(), 2000);
  });
  document.body.append(frame);
}
