/* Servidor Bat’z iniciado, Playwright externo mediante PLAYWRIGHT_MODULE.
   BATZ_BASE_URL y BATZ_TEST_OUTPUT permiten elegir servidor y capturas.
   Ejecuta también los ejemplos contra los verificadores reales de /api/proof. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.BATZ_BASE_URL || 'http://127.0.0.1:8765';
const output = process.env.BATZ_TEST_OUTPUT || '/tmp/batz-learn';

(async () => {
  fs.mkdirSync(output, {recursive: true});
  const browser = await chromium.launch({headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/#/aprender`);
    await page.locator('.tl2-main').waitFor();
    await page.evaluate(() => document.fonts.ready);
    // Anchos CSS equivalentes a reducir el zoom del navegador, más zoom CSS
    // explícito para comprobar el reflujo sin depender de atajos del navegador.
    for (const width of [360, 768, 1024, 1440, 1920, 2560, 3840]) {
      await page.setViewportSize({width, height: 1000});
      for (const zoom of [0.5, 0.8, 1, 1.25, 2]) {
        await page.evaluate(zoom => { document.documentElement.style.zoom = zoom; }, zoom);
        const sizes = await page.evaluate(() => {
          const box = selector => document.querySelector(selector).getBoundingClientRect();
          const center = selector => { const r = box(selector); return (r.left + r.right) / 2; };
          return {history: center('#learn-history'), cards: center('#learn-cards'),
            timeline: center('.tl2-main'), card: center('.fc-card'),
            toolbar: center('#learn-cards .learn-toolbar'),
            overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth};
        });
        for (const key of ['cards', 'timeline', 'card', 'toolbar']) {
          assert.ok(Math.abs(sizes.history - sizes[key]) < 2, `${width}px × ${zoom}: ${key} fuera de eje: ${JSON.stringify(sizes)}`);
        }
        assert.ok(sizes.overflow <= 1, `${width}px × ${zoom}: desbordamiento de ${sizes.overflow}px`);
      }
      await page.evaluate(() => { document.documentElement.style.zoom = 1; });
      if ([360, 1440, 2560].includes(width)) await page.screenshot({path: path.join(output, `aprender-${width}.png`), fullPage: true});
    }
    await page.setViewportSize({width: 1440, height: 1000});
    await page.locator('.tl2-node').nth(6).click();
    await page.locator('#learn-cards .fc-flip').click();
    await page.setViewportSize({width: 360, height: 900});
    assert.equal(await page.locator('.tl2-node').nth(6).getAttribute('aria-current'), 'step');
    assert.equal(await page.locator('.fc-card').getAttribute('data-flipped'), 'true');

    await page.goto(`${base}/#/demostrar`);
    const examples = await page.evaluate(async () => (await import('/features/prover/examples.js')).PROOF_EXAMPLES);
    assert.equal(new Set(examples.map(item => item.id)).size, examples.length);
    assert.equal(await page.locator('#proof-example optgroup').count(), 4);
    await page.locator('#proof-premises').fill('p');
    await page.locator('#proof-conclusion').fill('p');
    await page.locator('#proof-example').selectOption('socrates');
    await page.getByRole('button', {name: 'Deshacer', exact: true}).click();
    assert.equal(await page.locator('#proof-premises').inputValue(), 'p');
    assert.equal(await page.locator('#proof-conclusion').inputValue(), 'p');
    for (const example of examples) {
      await page.locator('#proof-example').selectOption(example.id);
      assert.equal(await page.locator('#proof-premises').inputValue(), example.premises);
      assert.equal(await page.locator('#proof-conclusion').inputValue(), example.conclusion);
      assert.equal(await page.locator('#proof-constants').inputValue(), example.constants);
      await page.waitForFunction(() => !document.getElementById('prove').disabled);
      const response = page.waitForResponse(response => response.url().endsWith('/api/proof'));
      await page.locator('#prove').click();
      const result = await (await response).json();
      assert.equal(result.status, example.expected, `${example.id}: ${JSON.stringify(result)}`);
      await page.waitForFunction(() => !document.getElementById('prove').disabled);
      console.log(`${example.id}: ${result.status}`);
    }
    assert.deepEqual(errors, []);
    await page.screenshot({path: path.join(output, 'demostrar.png'), fullPage: true});
    console.log('OK: 35 combinaciones de ancho y zoom, conservación de estado, selector, deshacer y 15 veredictos.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
