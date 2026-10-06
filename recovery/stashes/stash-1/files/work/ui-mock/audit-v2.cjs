const fs = require('node:fs');
const assert = require('node:assert/strict');
const { JSDOM } = require('../../frontend/node_modules/jsdom');
const html = fs.readFileSync(__dirname + '/cultivo-claro-v2.html', 'utf8');
let errors = [];
let scenario, model, onChange;
const dom = new JSDOM(html, {runScripts:'dangerously',beforeParse(w){
  w.ResizeObserver=class{observe(){}};
  w.addEventListener('error',e=>errors.push(e.message));
  w.Tweak=class{constructor(o){onChange=o.onChange}addSelect(o){scenario=o}addToggle(){}};
  w.openai={setWidgetState(s){model=s;return Promise.resolve();}};
}});
const doc=dom.window.document,q=s=>doc.querySelector(s),all=s=>[...doc.querySelectorAll(s)];
const change=(selector,value)=>{q(selector).value=value;q(selector).dispatchEvent(new dom.window.Event('change'));};
assert.equal(all('.c-day').length,3);
assert.match(q('#c-days').textContent,/75/);
q('[data-nav="history"]').click();
const lastTemp=q('#c-temp').textContent;
change('#c-period','30');
assert.equal(q('#c-temp').textContent,lastTemp,'Latest temperature must not depend on period');
assert.equal(all('#c-rows tr').length,30);
assert.equal(all('[data-chart="history"] circle').length,29);
assert.equal(all('[data-chart="history"] .curve').length,2,'Missing day must split line');
assert.match(q('#c-rows').textContent,/Sin lectura/);
q('[data-nav="notes"]').click();
q('#c-text').value='Borrador norte';
change('#c-sector','sur');
assert.equal(q('#c-text').value,'','Draft must not leak into another sector');
change('#c-sector','norte');
assert.equal(q('#c-text').value,'Borrador norte');
q('#c-text').value='   ';
q('#c-form').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));
assert.equal(all('.c-note').length,0);
q('#c-text').value='<img src=x onerror=alert(1)> Hojas caídas';
q('#c-text').dispatchEvent(new dom.window.Event('input'));
q('#c-form').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));
assert.equal(all('.c-note').length,1);
assert.equal(all('.c-note img').length,0,'Observation is text, never executable markup');
assert.equal(model.privateContent.notes.length,1);
change('#c-sector','sur');
assert.equal(all('.c-note').length,0);
for(const value of ['stale','empty','error','partial','ready']){
  scenario.scenario=value;onChange();
  if(['stale','empty','error'].includes(value))assert.equal(all('.c-day').filter(b=>b.textContent.includes('Sin estimación')).length,3);
  if(value==='stale'){assert.match(q('#c-measure-date').textContent,/10/);assert.match(q('#c-fresh').textContent,/10/);}
  if(value==='empty'||value==='error'){assert.equal(all('#c-rows tr').length,0);assert.equal(q('#c-moisture').textContent,'—');}
  if(value==='partial'){assert.equal(all('.c-day').filter(b=>b.textContent.includes('Sin estimación')).length,1);assert.doesNotMatch(q('#c-summary').textContent,/Hay una alerta/);}
}
const ids=all('[id]').map(e=>e.id);assert.equal(new Set(ids).size,ids.length);
assert.deepEqual(errors,[]);
assert.ok(!/\bfetch\s*\(|XMLHttpRequest|WebSocket/.test(html));
console.log('PASS: 3 horizontes, períodos coherentes, huecos, borradores aislados, validación, guardado, restauración serializable, texto seguro, 5 estados y sin llamadas de red.');
dom.window.close();
