const fs = require('node:fs');
const assert = require('node:assert/strict');
const { JSDOM } = require('../../frontend/node_modules/jsdom');
const html = fs.readFileSync(__dirname + '/cultivo-claro.html', 'utf8');
const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  beforeParse(window) {
    window.ResizeObserver = class { observe() {} };
  },
});
const doc = dom.window.document;
assert.equal(doc.querySelectorAll('.farm-day').length, 3);
assert.match(doc.querySelector('#farm-days').textContent, /75 %/);
doc.querySelector('[data-page="mediciones"]').click();
assert.equal(doc.querySelector('[data-view="mediciones"]').hidden, false);
const period = doc.querySelector('#farm-period');
period.value = '30';
period.dispatchEvent(new dom.window.Event('change'));
assert.equal(doc.querySelectorAll('[data-chart="long"] circle').length, 29);
doc.querySelector('[data-page="observaciones"]').click();
doc.querySelector('#farm-note').value = 'Hojas caídas por la tarde.';
doc.querySelector('#farm-form').dispatchEvent(new dom.window.Event('submit', { cancelable: true }));
assert.match(doc.querySelector('#farm-notes').textContent, /Hojas caídas/);
const sector = doc.querySelector('#farm-sector');
sector.value = 'sur';
sector.dispatchEvent(new dom.window.Event('change'));
assert.doesNotMatch(doc.querySelector('#farm-notes').textContent, /Hojas caídas/);
assert.match(doc.querySelector('#farm-days').textContent, /30 %/);
assert.equal(doc.querySelectorAll('.is-alert').length, 0);
doc.querySelector('#farm-help-toggle').click();
assert.equal(doc.querySelector('#farm-help').hidden, false);
console.log('Mock verificado: navegación, períodos, sector, observación local y ayuda.');
dom.window.close();
