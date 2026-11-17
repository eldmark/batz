import {createExplanationPlayer} from '/features/explanation-player/index.js';

const fixtures = await (await fetch('/fixtures.json')).json();
const log = [], states = [];
const player = createExplanationPlayer({
  host: document.getElementById('player'),
  onStepChange: entry => {
    log.push(entry);
    document.getElementById('demo-log').textContent = `${entry.resultId} · ${entry.index + 1}/${entry.total} · ${entry.event.text_es}`;
  },
  onStateChange: state => states.push(state),
});
const other = createExplanationPlayer({host: document.getElementById('other')});
const load = (name, id = name) => player.load({...fixtures[name], resultId: id});
document.getElementById('load').onclick = () => load(document.getElementById('fixture').value);
document.getElementById('open').onclick = () => player.open();
document.getElementById('invalidate').onclick = () => player.invalidate('El modelo cambió. Vuelve a evaluar.');
document.getElementById('second').onclick = () => { other.load({...fixtures.proof, resultId: 'other-proof'}); other.open(); };
// Exposición limitada a la demo: el reproductor de producción no escribe en window.
window.demo = {player, other, fixtures, log, states, load};
load('evaluation');
