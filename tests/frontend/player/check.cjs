/* Ejecutar con NODE_PATH apuntando a una instalación externa de Playwright. */
const assert = require('node:assert/strict');
const {mkdir} = require('node:fs/promises');
const path = require('node:path');
const {chromium} = require('playwright');

const base = process.env.BATZ_PLAYER_URL || 'http://127.0.0.1:8877';
const artifacts = process.env.BATZ_PLAYER_ARTIFACTS || '/tmp/logos-player-verification';
const stubScene = `
window.sceneStats ||= {created: 0, disposed: 0, events: [], live: 0};
export function createStoryScene(host, model, options) {
  if (window.sceneMode === 'fail') throw Error('WebGL no disponible');
  const stats = window.sceneStats; stats.created++; stats.live++;
  const canvas = document.createElement('canvas'); host.append(canvas);
  let dead = false;
  queueMicrotask(() => {if (!dead) options.onReady?.()});
  return {
    setEvent(event) {stats.events.push(event)}, talking(on) {stats.talking = on},
    say(word) {stats.word = word}, syllableCount() {return 1}, setActive(on) {stats.active = on}, verdict() {},
    dispose() {if (!dead) {dead = true; stats.disposed++; stats.live--; canvas.remove()}},
  };
}`;

async function speechMock() {
  class Utterance {constructor(text) {this.text = text;}}
  class Speech extends EventTarget {
    constructor() {super(); this.spoken = []; this.cancelled = 0; this.available = true;}
    getVoices() {return this.available ? [{name:'Español local de prueba', lang:'es-GT', localService:true}] : [];}
    cancel() {this.cancelled++;}
    speak(utterance) {this.spoken.push(utterance); this.current = utterance; queueMicrotask(() => utterance.onstart?.());}
  }
  Object.defineProperty(window, 'SpeechSynthesisUtterance', {value: Utterance, configurable:true});
  Object.defineProperty(window, 'speechSynthesis', {value:new Speech(), configurable:true});
}

(async () => {
  await mkdir(artifacts, {recursive:true});
  const browser = await chromium.launch({
    executablePath: process.env.BATZ_BROWSER || undefined,
    headless: true,
    args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
  });
  let count = 0;
  async function check(name, task, {stub=true, mockSpeech=false, setup=null} = {}) {
    if (process.env.BATZ_PLAYER_FILTER && !name.includes(process.env.BATZ_PLAYER_FILTER)) return;
    const context = await browser.newContext({viewport:{width:1440,height:1000}});
    const page = await context.newPage(), errors = [], external = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {
      const url = request.url();
      if (!url.startsWith(base) && !url.startsWith('data:') && !url.startsWith(`blob:${base}/`)) external.push(url);
    });
    if (stub) await page.route('**/story3d.js', route => route.fulfill({contentType:'text/javascript',body:stubScene}));
    if (mockSpeech) await page.addInitScript(speechMock);
    if (setup) await setup(page);
    try {
      await page.goto(base); await page.waitForFunction(() => Boolean(window.demo));
      await task(page, page.locator('#player'));
      assert.deepEqual(errors, [], 'Errores JavaScript');
      assert.deepEqual(external, [], 'Solicitudes externas');
      console.log(`OK ${++count} ${name}`);
    } catch(error) {
      await page.screenshot({path:path.join(artifacts, `fallo-${count+1}.png`),fullPage:true}).catch(() => {});
      throw new Error(`${name}: ${error.stack}`);
    } finally {await context.close();}
  }

  try {
    await check('ciclo de vida, identidad y revisión', async (page, host) => {
      assert.equal(await host.locator('.ep-player').isVisible(), false);
      await page.click('#open');
      await host.getByRole('button',{name:'Siguiente',exact:true}).click();
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
      await page.evaluate(() => demo.player.load({...demo.fixtures.evaluation, story:{events:[]}}));
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
      await host.getByRole('button',{name:'Minimizar',exact:true}).click();
      assert.equal(await host.locator('.ep-body').isVisible(), false);
      await host.getByRole('button',{name:'Restaurar',exact:true}).click();
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
      await host.getByRole('button',{name:'Cerrar',exact:true}).click(); await page.click('#open');
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
      await page.click('#invalidate');
      assert.equal(await host.locator('[data-action=play]').isDisabled(), true);
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().status), 'stale');
      await page.evaluate(() => demo.load('evaluation','revision-2'));
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 0);
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().presentation), 'closed');
      await page.evaluate(() => {demo.player.clear(); demo.player.clear(); demo.player.pause(); demo.player.close();});
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().status), 'empty');
      await page.evaluate(() => demo.load('empty')); await page.click('#open');
      assert.equal(await host.locator('.ep-player').isVisible(), false);
    });

    await check('mismo evento en texto, escena y callback; elemento cero', async (page, host) => {
      await page.click('#open');
      await page.waitForFunction(() => window.sceneStats?.events.length);
      await host.getByRole('button',{name:'Ver caso con 0',exact:true}).click();
      assert.equal(await page.evaluate(() => demo.log.at(-1).event.element), 0);
      await page.waitForFunction(() => sceneStats.events.at(-1).trace_path === demo.log.at(-1).event.trace_path);
      assert.equal(await host.locator('.ep-narration').textContent(), await page.evaluate(() => demo.log.at(-1).event.text_es));
      await page.evaluate(() => demo.load('proof')); await page.click('#open');
      assert.equal(await host.locator('.ep-node').count(), 0);
      assert.match(await host.locator('.ep-detail').textContent(), /Línea/);
      await page.evaluate(() => demo.load('countermodel')); await page.click('#open');
      assert.equal(await host.locator('.ep-badge').textContent(), 'Búsqueda acotada');
      await host.locator('summary').click();
      const premise = await page.evaluate(() => demo.fixtures.countermodel.story.events.findIndex(e => e.kind === 'premise'));
      await host.locator('.ep-list button').nth(premise).click();
      assert.match(await host.locator('.ep-note').first().textContent() || '', /./);
      assert.equal(await host.locator('.ep-detail .ep-note').textContent(), 'Comprobación de premisa');
    });

    await check('sin voz y fallo de escena conserva 2D', async (page, host) => {
      await page.evaluate(() => {window.sceneMode = 'fail'; speechSynthesis.available = false; speechSynthesis.dispatchEvent(new Event('voiceschanged'));});
      await page.click('#open');
      await host.getByText(/No se pudo cargar la vista 3D/).waitFor();
      assert.equal(await host.getByRole('checkbox',{name:'Narración por voz'}).isDisabled(), true);
      assert.equal(await host.locator('.ep-node').count(), 2);
      await host.locator('[data-action=play]').click();
      await page.waitForFunction(() => demo.player.getSnapshot().index > 0, {timeout:10000});
      await page.evaluate(() => demo.player.pause());
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().playing), false);
    }, {mockSpeech:true});

    await check('voz, velocidad, callbacks obsoletos y exclusión entre instancias', async (page, host) => {
      await page.click('#open');
      await host.getByRole('checkbox',{name:'Narración por voz'}).check();
      await host.locator('[data-action=play]').click();
      await page.evaluate(() => {window.oldEnd = speechSynthesis.current.onend; window.oldBoundary = speechSynthesis.current.onboundary;});
      await host.getByRole('combobox',{name:'Velocidad'}).selectOption('1.5');
      assert.equal(await page.evaluate(() => speechSynthesis.current.rate), .92*1.5);
      await page.evaluate(() => {window.oldEnd(); window.oldBoundary({charIndex:0,charLength:1,name:'word'});});
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 0);
      await host.getByRole('button',{name:'Siguiente',exact:true}).click();
      const step = await page.evaluate(() => demo.player.getSnapshot().index);
      await page.evaluate(() => {window.oldEnd();});
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), step);
      await page.click('#second');
      await page.locator('#other [data-action=play]').click();
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().playing), false);
      assert.equal(await page.evaluate(() => demo.other.getSnapshot().playing), true);
      await page.evaluate(() => {demo.other.pause(); demo.player.load({...demo.fixtures.true,resultId:'new'}); window.oldEnd();});
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 0);
    }, {mockSpeech:true});

    await check('cancelar voz al repetir, invalidar y destruir', async (page, host) => {
      await page.click('#open'); await host.getByRole('checkbox',{name:'Narración por voz'}).check();
      await host.getByRole('button',{name:'Siguiente',exact:true}).click();
      await host.getByRole('button',{name:'Repetir paso',exact:true}).click();
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
      await page.evaluate(() => {window.oldEnd=speechSynthesis.current.onend; demo.player.invalidate(); window.oldEnd();});
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().playing), false);
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
      await page.evaluate(() => {demo.player.destroy(); demo.player.destroy(); window.oldEnd();});
      assert.equal(await host.locator('.ep-player').count(), 0);
    }, {mockSpeech:true});

    await check('pantalla completa de respaldo, teclado, foco y scroll', async (page, host) => {
      await page.click('#open');
      await page.evaluate(() => {
        Object.defineProperty(document,'fullscreenEnabled',{value:false,configurable:true});
        document.querySelector('main').style.paddingTop='600px';
      });
      const fs = host.getByRole('button',{name:'Pantalla completa',exact:true});
      await fs.scrollIntoViewIfNeeded(); await fs.focus();
      const before = await host.locator('.ep-player').boundingBox();
      await fs.click();
      assert.equal(await host.locator('.ep-fallback-fullscreen').count(), 1);
      await page.keyboard.press('ArrowRight');
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
      await page.keyboard.press('Escape'); await page.waitForTimeout(500);
      assert.equal(await host.locator('.ep-fullscreen').count(), 0);
      assert.equal(await fs.evaluate(el => document.activeElement === el), true);
      const after = await host.locator('.ep-player').boundingBox();
      assert.ok(Math.abs(before.y-after.y)<3, `desplazamiento ${before.y} -> ${after.y}`);
      assert.notEqual(await page.evaluate(() => document.documentElement.style.overflow), 'hidden');
    });

    await check('mover host y tamaños móviles conservan paso', async (page, host) => {
      await page.click('#open'); await host.getByRole('button',{name:'Siguiente',exact:true}).click();
      for (const size of [{width:1024,height:768},{width:768,height:1024},{width:390,height:844},{width:360,height:800},{width:844,height:390}]) {
        await page.setViewportSize(size); await page.waitForTimeout(80);
        assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, JSON.stringify(size));
      }
      await page.evaluate(() => document.querySelector('main').append(document.getElementById('player')));
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
      await page.setViewportSize({width:390,height:844});
      await page.screenshot({path:path.join(artifacts,'movil.png'),fullPage:true});
    });

    await check('import pendiente no revive una instancia destruida', async (page, host) => {
      let release; const gate = new Promise(resolve => release=resolve);
      await page.route('**/story3d.js', async route => {await gate; await route.fulfill({contentType:'text/javascript',body:stubScene}).catch(() => {});});
      await page.click('#open'); await page.waitForTimeout(60);
      await page.evaluate(() => demo.player.destroy()); release(); await page.waitForTimeout(150);
      assert.equal(await host.locator('canvas').count(), 0);
      assert.equal(await page.evaluate(() => window.sceneStats?.created || 0), 0);
    });

    await check('avatar real, morph targets y selección sincronizada', async (page, host) => {
      await page.click('#open');
      await host.getByText(/Vista 3D lista/).waitFor({timeout:30000});
      assert.equal(await host.locator('canvas').count(), 1);
      await host.getByRole('button',{name:'Siguiente',exact:true}).click();
      await page.screenshot({path:path.join(artifacts,'escritorio-3d.png'),fullPage:true});
      await host.getByRole('button',{name:'Minimizar',exact:true}).click();
      assert.equal(await host.locator('canvas').count(), 0);
      await host.getByRole('button',{name:'Restaurar',exact:true}).click();
      await host.getByText(/Vista 3D lista/).waitFor({timeout:30000});
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
      await page.setViewportSize({width:390,height:844}); await page.waitForTimeout(300);
      await page.screenshot({path:path.join(artifacts,'movil-3d.png'),fullPage:true});
      await host.getByRole('button',{name:'Cerrar',exact:true}).click();
      assert.equal(await host.locator('canvas').count(), 0);
    }, {stub:false});

    await check('GLB fallido conserva la explicación', async (page, host) => {
      await page.route('**/avatar/logos.glb', route => route.fulfill({status:404,body:'No encontrado'}));
      await page.click('#open'); await host.getByText(/No se pudo cargar la vista 3D/).waitFor();
      assert.equal(await host.locator('canvas').count(), 0);
      assert.ok((await host.locator('.ep-narration').textContent()).length>0);
    }, {stub:false});

    await check('WebGL ausente conserva texto y controles', async (page, host) => {
      await page.click('#open'); await host.getByText(/No se pudo cargar la vista 3D/).waitFor();
      assert.equal(await host.locator('canvas').count(), 0);
      await host.getByRole('button',{name:'Siguiente',exact:true}).click();
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index), 1);
    }, {stub:false, setup: async page => {
      await page.addInitScript(() => {
        const original = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, ...args) {
          return /^webgl/.test(type) ? null : original.call(this,type,...args);
        };
      });
    }});

    await check('pantalla completa nativa y cierre durante reproducción', async (page, host) => {
      await page.click('#open');
      await host.getByRole('button',{name:'Pantalla completa',exact:true}).click();
      await page.waitForFunction(() => Boolean(document.fullscreenElement));
      await host.locator('[data-action=play]').click();
      await host.getByRole('button',{name:'Cerrar',exact:true}).click();
      await page.waitForFunction(() => !document.fullscreenElement);
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().playing), false);
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().presentation), 'closed');
      assert.equal(await page.locator('#open').evaluate(el => document.activeElement===el),true);
    });

    await check('avatar real conserva formas de boca y movimiento reducido', async (page) => {
      await page.emulateMedia({reducedMotion:'reduce'});
      const result = await page.evaluate(async () => {
        const {createStoryScene} = await import('/story3d.js');
        const host = document.createElement('div'); host.style.cssText='width:600px;height:300px'; document.body.append(host);
        let scene;
        await new Promise((resolve,reject) => {scene=createStoryScene(host,demo.fixtures.evaluation.model,{onReady:resolve,onError:reject});});
        const targets=scene.mouthTargets();
        scene.talking(true); scene.say('mamá',1);
        // SwiftShader puede tardar varios cuadros en compilar el material.
        // Muestrear una animación por su estado evita asumir una frecuencia fija.
        const until=performance.now()+4000;
        while (performance.now()<until && !scene.mouthLevel().open && !scene.mouthLevel().round) {
          await new Promise(resolve => setTimeout(resolve,50));
        }
        const speaking=scene.mouthLevel();
        scene.talking(false);
        const stopped=scene.mouthLevel(), blink=scene.blinkLevel();
        scene.dispose(); scene.dispose(); host.remove();
        return {targets,speaking,stopped,blink};
      });
      assert.ok(result.targets.some(t => t.open!==undefined && t.round!==undefined && t.blink!==undefined));
      assert.ok(result.speaking.open>0 || result.speaking.round>0);
      assert.deepEqual(result.stopped,{open:0,round:0});
      assert.equal(result.blink,0);
    }, {stub:false});

    await check('GLB pendiente se libera después de destruir', async (page, host) => {
      let release, requested;
      const gate = new Promise(resolve => release=resolve), started = new Promise(resolve => requested=resolve);
      await page.route('**/avatar/logos.glb', async route => {
        const response=await route.fetch(); requested(); await gate;
        await route.fulfill({response}).catch(() => {});
      });
      await page.click('#open'); await started;
      await page.evaluate(() => demo.player.destroy()); release(); await page.waitForTimeout(500);
      assert.equal(await host.locator('canvas').count(),0);
      assert.equal(await host.locator('.ep-player').count(),0);
    }, {stub:false});

    await check('fin del guion y pausa al ocultar la pestaña', async (page, host) => {
      await page.click('#open'); await host.getByRole('checkbox',{name:'Narración por voz'}).check();
      await host.locator('[data-action=play]').click();
      await page.evaluate(() => {
        const total=demo.player.getSnapshot().total;
        for (let i=0; i<total; i++) speechSynthesis.current.onend?.();
      });
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().playing),false);
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index === demo.player.getSnapshot().total-1),true);
      await host.getByRole('button',{name:'Desde el inicio',exact:true}).click();
      await page.evaluate(() => {
        Object.defineProperty(document,'hidden',{get:()=>true,configurable:true});
        document.dispatchEvent(new Event('visibilitychange'));
      });
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().playing),false);
      assert.equal(await page.evaluate(() => demo.player.getSnapshot().index),0);
    }, {mockSpeech:true});

    console.log(`${count} recorridos de navegador correctos. Capturas: ${artifacts}`);
  } finally {await browser.close();}
})().catch(error => {console.error(error); process.exitCode=1;});
