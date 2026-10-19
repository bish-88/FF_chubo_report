// 画面側の計算式（前年比・廃棄率・減らす数）を境界値で確かめる。
// node tests/test_formulas.js で実行。template.html から関数を取り出して使う。
const fs = require('fs'), path = require('path'), assert = require('assert');
const src = fs.readFileSync(path.join(__dirname, '..', 'scripts', 'template.html'), 'utf8');
const grab = re => { const m = src.match(re); if (!m) throw new Error('not found: ' + re); return m[0]; };
const code = [
  grab(/const pct=\(a,b\)=>[^\n]*\n/), grab(/const pf=[^\n]*\n/), grab(/const wrOf=[^\n]*\n/),
  grab(/function cutN\(w\)\{[^\n]*\}\n/),
].join('');
const { pct, pf, wrOf, cutN } = new Function(code + 'return {pct,pf,wrOf,cutN};')();
let n = 0; const t = (name, fn) => { fn(); n++; console.log('OK  ', name); };

t('前年比：通常', () => { assert.strictEqual(pct(110, 100).toFixed(6), '10.000000'); assert.strictEqual(pct(90, 100).toFixed(6), '-10.000000'); });
t('前年比：基準0・欠損は null（0%と区別）', () => { assert.strictEqual(pct(5, 0), null); assert.strictEqual(pct(5, null), null); assert.strictEqual(pct(null, 100), null); });
t('前年比：同じ値は0%', () => assert.strictEqual(pct(100, 100), 0));
t('表示：null は「—」、符号付き', () => { assert.strictEqual(pf(null), '—'); assert.strictEqual(pf(3.14), '+3.1%'); assert.strictEqual(pf(-3.14), '-3.1%'); assert.strictEqual(pf(0), '+0.0%'); assert.strictEqual(pf(12.345, 0), '+12%'); });
t('廃棄率：廃棄数÷(販売数＋廃棄数)', () => { assert.strictEqual(wrOf({ 販売数: 90, 廃棄数: 10 }), 10); assert.strictEqual(wrOf({ 販売数: 0, 廃棄数: 5 }), 100); });
t('廃棄率：販売も廃棄もない→0（0除算しない）', () => assert.strictEqual(wrOf({ 販売数: 0, 廃棄数: 0 }), 0));
t('減らす数：境界値', () => {
  assert.strictEqual(cutN(0), '様子見'); assert.strictEqual(cutN(0.29), '様子見');
  assert.strictEqual(cutN(0.3), '2日に1回 1個減'); assert.strictEqual(cutN(0.74), '2日に1回 1個減');
  assert.strictEqual(cutN(0.75), '1個減'); assert.strictEqual(cutN(1.24), '1個減');
  assert.strictEqual(cutN(1.25), '1個減'); assert.strictEqual(cutN(2.5), '2個減'); assert.strictEqual(cutN(5), '4個減');
});
t('減らす数：1日の廃棄数を超えない（約8割まで）', () => {
  for (let w = 1.25; w <= 20; w += 0.05) { const k = parseInt(cutN(w)); assert.ok(k <= w * 0.8 + 1e-9 || k === 1, `w=${w} k=${k}`); }
});
console.log(`${n} tests passed`);
