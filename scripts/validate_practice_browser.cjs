/* Verificación opcional de UI. Requiere Playwright externo, no es dependencia de LOGOS.
   PLAYWRIGHT_MODULE: ruta al paquete playwright/playwright-core.
   LOGOS_PRACTICE_FIXTURES: JSON de EXERCISES exportado por Python.
   LOGOS_BASE_URL: servidor iniciado (por defecto http://127.0.0.1:8765).
   PLAYWRIGHT_CHROMIUM_EXECUTABLE: opcional, navegador ya instalado.
   LOGOS_TEST_OUTPUT: carpeta opcional de capturas.
*/
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.LOGOS_BASE_URL || 'http://127.0.0.1:8765';
const output = process.env.LOGOS_TEST_OUTPUT || path.join(os.tmpdir(), 'logos-practice');

(async () => {
  fs.mkdirSync(output, {recursive:true});
  const exercises = JSON.parse(fs.readFileSync(process.env.LOGOS_PRACTICE_FIXTURES, 'utf8'));
  const browser = await chromium.launch({headless:true, executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined});
  try {
    const context = await browser.newContext({viewport:{width:1440,height:1050}});
    const page = await context.newPage(); const errors=[];
    page.setDefaultTimeout(10000); page.on('pageerror',e=>errors.push(e.message));
    await page.goto(`${base}/#practicar`);
    await page.locator('.pr-exercise').first().waitFor();
    assert.equal(await page.locator('.pr-exercise').count(),10);
    assert.equal(await page.locator('.pr-category').count(),3);
    await page.screenshot({path:path.join(output,'home.png'),fullPage:true});
    for (const ex of exercises) {
      await page.locator(`.pr-category[data-category="${ex.category}"]`).click();
      if (ex.id === '11' || ex.id === '41') await page.screenshot({path:path.join(output,`category-${ex.category}.png`),fullPage:true});
      await page.locator(`.pr-exercise[aria-label^="Abrir ejercicio ${ex.id}:"]`).click();
      await page.locator('#pr-formula').waitFor();
      if (ex.id === '01') {
        await page.screenshot({path:path.join(output,'exercise.png'),fullPage:true});
        // Un error no añade una línea ni pierde el texto.
        await page.locator('#pr-formula').fill('Q'); await page.locator('#pr-refs').fill('1');
        await page.locator('#pr-check').click(); await page.locator('.pr-feedback.is-error').waitFor();
        assert.equal(await page.locator('.pr-line').count(),1);
        assert.equal(await page.locator('#pr-formula').inputValue(),'Q');
        // Una hipótesis igual al objetivo tampoco completa el ejercicio.
        await page.locator('#pr-rule').selectOption('assume'); await page.locator('#pr-formula').fill('P');
        await page.locator('#pr-check').click(); await page.locator('.pr-feedback.is-warning').waitFor();
        assert.equal(await page.locator('#pr-success').isVisible(),false);
        await page.locator('#pr-undo').click(); await page.waitForFunction(()=>document.querySelectorAll('.pr-line').length===1);
        await page.locator('#pr-hint').click(); await page.locator('.pr-hints p').waitFor();
        await page.locator('.pr-solution summary').click(); await page.locator('.pr-solution-line').first().waitFor();
        assert.equal(await page.locator('#pr-success').isVisible(),false);
        await page.locator('.pr-solution summary').click();
      }
      for (let index=0;index<ex.solution.length;index++) {
        const s=ex.solution[index];
        await page.locator('#pr-rule').selectOption(s.rule);
        await page.locator('#pr-formula').fill(s.formula);
        if (s.refs.length) await page.locator('#pr-refs').fill(s.refs.join(', '));
        for(const [k,v] of Object.entries(s.params)) await page.locator(`#pr-param-${k}`).fill(v);
        await page.locator('#pr-check').click();
        await page.waitForFunction(n=>document.querySelectorAll('.pr-line').length===n,ex.premises.length+index+1);
        if(index===ex.solution.length-1) await page.locator('#pr-success:not([hidden])').waitFor();
      }
      console.log(`UI ${ex.id}: demostración completada`);
      if(ex.id==='50') await page.screenshot({path:path.join(output,'success-legend.png'),fullPage:false});
      if(ex.id==='10') assert.equal(await page.getByRole('button',{name:'Entrar en Desafío →',exact:true}).count(),1);
      if(ex.id==='40') assert.equal(await page.getByRole('button',{name:'Entrar en Modo Leyenda →',exact:true}).count(),1);
      await page.getByRole('button',{name:'← Ejercicios',exact:true}).click();
    }
    assert.equal(await page.locator('.pr-summary-count').textContent(),'50 / 50');
    await page.reload(); await page.locator('.pr-exercise').first().waitFor();
    assert.equal(await page.locator('.pr-exercise.is-complete').count(),10);
    for(const [category,count] of [['introduction',10],['challenge',30],['legend',10]]) {
      await page.locator(`.pr-category[data-category="${category}"]`).click();
      assert.equal(await page.locator('.pr-exercise.is-complete').count(),count);
    }
    // Otra pestaña no ve los controles del editor ni acciones de importación.
    await page.locator('#tab-evaluate').click(); assert.equal(await page.locator('#mode-evaluate').isVisible(),true);
    await page.locator('#tab-practice').click(); assert.equal(await page.locator('.topbar-actions').isVisible(),false);
    // Contexto móvil limpio: teclado, referencias pulsables y traducción en vivo.
    const mobile = await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    const m=await mobile.newPage(); m.setDefaultTimeout(10000); m.on('pageerror',e=>errors.push(e.message));
    await m.goto(`${base}/#practicar`); await m.locator('.pr-exercise').first().waitFor();
    await m.screenshot({path:path.join(output,'mobile-home.png'),fullPage:true});
    await m.locator('.pr-exercise').first().click(); await m.locator('#pr-formula').waitFor();
    await m.getByRole('button',{name:'Citar línea 1',exact:true}).click();
    assert.equal(await m.locator('#pr-refs').inputValue(),'1');
    await m.locator('#pr-formula').focus(); await m.getByRole('button',{name:'Insertar P',exact:true}).click();
    assert.equal(await m.locator('#pr-formula').inputValue(),'P');
    await m.waitForFunction(()=>document.getElementById('pr-reading').textContent==='Se cumple P');
    assert.equal(await m.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await m.screenshot({path:path.join(output,'mobile-exercise.png'),fullPage:true});
    await m.locator('#pr-check').click(); await m.locator('#pr-success:not([hidden])').waitFor();
    await m.getByRole('button',{name:'← Ejercicios',exact:true}).click();
    await m.locator('.pr-category[data-category="legend"]').click();
    await m.setViewportSize({width:320,height:740});
    assert.equal(await m.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await m.screenshot({path:path.join(output,'mobile-legend.png'),fullPage:true});
    // La actualización preserva las pruebas compatibles y archiva las reemplazadas.
    const migration = await browser.newContext();
    await migration.addInitScript(() => localStorage.setItem('logos.practice.v1',JSON.stringify({
      '01':{moves:[{formula:'P',rule:'and_e1',refs:[1],params:{}}],complete:true,hints:1},
      '05':{moves:[{formula:'P',rule:'assume',refs:[],params:{}}],complete:true,hints:2}
    })));
    const old = await migration.newPage(); await old.goto(`${base}/#practicar`);
    await old.locator('.pr-exercise').first().waitFor();
    assert.equal(await old.locator('.pr-exercise.is-complete').count(),1);
    const recovered=await old.evaluate(()=>JSON.parse(localStorage.getItem('logos.practice.v1')));
    assert.equal(recovered['05'].previous.length,1); assert.equal(recovered['05'].moves.length,0);
    assert.equal(recovered['01'].complete,true);
    assert.deepEqual(errors,[]);
    console.log('OK: 50 soluciones, tres categorías, migración, errores, hipótesis pendientes, pistas, persistencia y móvil.');
    console.log(`Capturas: ${output}`);
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
