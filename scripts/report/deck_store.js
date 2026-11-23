// FF・厨房レポート（全店＋店舗別）を alld.json（ダッシュボードのデータ＋prep.py の追加分）から作る。
// node deck_store.js alld.json [出力フォルダ] [店舗...]   店舗を省くと 全店＋全店舗（使い方は prep.py の先頭）
const pptxgen = require('pptxgenjs');
const path = require('path');
const { applyTheme } = require('/mnt/skills/public/pptx/scripts/apply_theme.js');
const D = require(path.resolve(process.argv[2]));
const OUT = process.argv[3] || path.join(path.dirname(path.resolve(process.argv[2])), 'out');
const M = D.meta, N = M.N, MO = M.MO, Y = M.Y, LY = M.LY, DIM = M.DIM, STORES = M.stores, NS = STORES.length;

const THEME = { name: 'FF Report', headFontFace: 'Meiryo', bodyFontFace: 'Meiryo',
  colors: { dk1: '0E1A2B', lt1: 'FFFFFF', dk2: '0B1D33', lt2: 'F3F5F8', accent1: '163F6E', accent2: 'D9822B', accent3: '2A9D8F', accent4: '8E6BB8', accent5: 'C2A23A', accent6: 'B0302A', hlink: '1F5FA6', folHlink: '8E6BB8' } };
const HEX = { ty: '163F6E', ly: 'C3CCD6', ink: '0E1A2B', ink2: '465467', ink3: '8290A1', rule: 'E2E7EE', bg: 'F3F5F8',
  good: '16704A', goodBg: 'E7F4ED', bad: 'B0302A', badBg: 'FBECEB', warn: '94650A', warnBg: 'FBF2DC', accSoft: 'EAF1FA', star: 'FFF6DB' };
const CATCOL = { 'からあげクン': 'D9822B', 'マチカフェ': '7A5C45', 'ホットFF': '8E6BB8', '常温FF': '2A9D8F', 'サーマル常温': 'C2A23A', '中華まん': '1F5FA6', '弁当': '1F5FA6', '調理パン': 'D9822B', '惣菜': '2A9D8F' };

// ---------- 書式 ----------
const yen = v => (v < 0 ? '-' : '') + '¥' + Math.abs(Math.round(v)).toLocaleString('ja-JP');
const syen = v => (v >= 0 ? '+' : '-') + '¥' + Math.abs(Math.round(v)).toLocaleString('ja-JP');
const n0 = v => Math.round(v).toLocaleString('ja-JP');
const sn = v => (v >= 0 ? '+' : '-') + Math.abs(Math.round(v)).toLocaleString('ja-JP');
const ratio = (a, b) => b ? a / b * 100 : null;                      // 前年（先週）＝100%
const rtxt = v => v == null ? '—' : v.toFixed(1) + '%';
const ptxt = v => (v >= 0 ? '+' : '') + v.toFixed(1) + 'pt';
const wrOf = o => (o.販売数 + o.廃棄数) ? o.廃棄数 / (o.販売数 + o.廃棄数) * 100 : 0;
const short = (s, n) => { s = s.replace(/^(ＦＦ|ＨＯＴ)\s*/, ''); return n && s.length > n ? s.slice(0, n) + '…' : s; };
const DT = d => new Date(Y, MO - 1, d), WD = '日月火水木金土';
const wdOf = d => WD[DT(d).getDay()];
const isOff = d => DT(d).getDay() === 0 || DT(d).getDay() === 6 || !!M.hol26[d];
const md = d => `${MO}/${d}`;
function cutN(w) { if (w >= 1.25) return Math.max(1, Math.floor(w * 0.8)) + '個減'; if (w >= 0.75) return '1個減'; if (w >= 0.3) return '2日に1回 1個減'; return '様子見'; }
function cutAdv(r, unit) { if (r.wwk != null && r.wwe != null && Math.abs(r.wwe - r.wwk) >= 1) return `平日 ${cutN(r.wwk)}・土日 ${cutN(r.wwe)}`; return (unit ? unit + ' ' : '') + cutN(r.wpd); }

const PER = Object.fromEntries(M.periods.map(p => [p.k, p]));
const CUR = M.periods.find(p => p.tag === '今週'), PRV = M.periods.find(p => p.tag === '先週');
const wkLabel = p => `${md(p.d0)}（${wdOf(p.d0)}）〜${md(p.d1)}（${wdOf(p.d1)}）・${p.n}日間`;

function build(scope) {
  const isAll = scope === 'ALL', SNAME = isAll ? '全店' : scope;
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE'; pres.author = 'Biswash'; pres.title = `${SNAME} FF・厨房レポート ${N}日時点`;
  pres.theme = { headFontFace: 'Meiryo', bodyFontFace: 'Meiryo' };
  pres.defineSlideMaster({ title: 'CONTENT', background: { color: 'FFFFFF' }, margin: [0.5, 0.5, 0.6, 0.5],
    objects: [
      { placeholder: { options: { name: 'title', type: 'title', x: 0.5, y: 0.3, w: 11.6, h: 0.65, fontSize: 24, bold: true, color: HEX.ink, align: 'center', valign: 'middle', margin: 0 }, text: '' } },
      { text: { text: 'Made by Biswash', options: { x: 9.8, y: 7.05, w: 3.0, h: 0.3, fontSize: 10, color: HEX.ink3, align: 'right', margin: 0 } } },
      { text: { text: `${SNAME}｜比較：${Y}年${MO}/1〜${N} vs ${LY}年${MO}/1〜${N}（同じ日付）　データ：${MO}/${N}締め`, options: { x: 0.5, y: 7.05, w: 8.5, h: 0.3, fontSize: 10, color: HEX.ink3, margin: 0 } } },
    ], slideNumber: { x: 12.4, y: 0.35, w: 0.5, h: 0.3, fontSize: 10, color: HEX.ink3, align: 'right' } });

  const H = (t, o = {}) => ({ text: t, options: Object.assign({ bold: true, color: HEX.ink2, fill: { color: HEX.bg }, fontSize: 10.5, align: 'right', valign: 'middle' }, o) });
  const Tc = (t, o = {}) => ({ text: String(t), options: Object.assign({ color: HEX.ink, fontSize: 11, align: 'right', valign: 'middle' }, o) });
  // 比率（前年・先週＝100%）。売上は100%以上が良い、廃棄（inv）は100%未満が良い
  const RC = (v, inv, o = {}) => { if (v == null || !isFinite(v)) return Tc('—', Object.assign({ color: HEX.ink3 }, o)); const good = inv ? v < 100 : v > 100, flat = Math.abs(v - 100) < 1;
    return Tc(rtxt(v), Object.assign({ color: flat ? HEX.warn : good ? HEX.good : HEX.bad, bold: true }, o)); };
  const DY = (v, inv, o = {}) => { const good = inv ? v < 0 : v > 0, flat = Math.abs(v) < 0.5; return Tc(syen(v), Object.assign({ color: flat ? HEX.ink2 : good ? HEX.good : HEX.bad, bold: true }, o)); };
  const DN = (v, inv, o = {}) => { const good = inv ? v < 0 : v > 0, flat = Math.abs(v) < 0.5; return Tc(sn(v) + '個', Object.assign({ color: flat ? HEX.ink2 : good ? HEX.good : HEX.bad }, o)); };
  const DP = (v, o = {}) => Tc(ptxt(v), Object.assign({ color: Math.abs(v) < 0.1 ? HEX.ink2 : v < 0 ? HEX.good : HEX.bad, bold: true }, o));
  const tblOpts = (x, y, w, colW, rowH = 0.34) => ({ x, y, w, colW, border: { type: 'solid', pt: 0.75, color: HEX.rule }, fontFace: 'Meiryo', margin: [0.03, 0.07, 0.03, 0.07], rowH });
  const chartBase = () => ({ catAxisLabelColor: HEX.ink2, valAxisLabelColor: HEX.ink2, catAxisLabelFontFace: '+mn-lt', valAxisLabelFontFace: '+mn-lt', catAxisLabelFontSize: 10, valAxisLabelFontSize: 10,
    valGridLine: { color: HEX.rule, size: 0.75 }, catGridLine: { style: 'none' }, legendFontFace: '+mn-lt', legendFontSize: 10, legendColor: HEX.ink2, titleFontFace: '+mn-lt', titleColor: HEX.ink, titleFontSize: 12,
    dataLabelFontFace: '+mn-lt', dataLabelFontSize: 9, dataLabelColor: HEX.ink2 });
  const card = (s, x, y, w, h, name) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: 'FFFFFF' }, line: { color: HEX.rule, width: 0.75 }, objectName: name,
    shadow: { type: 'outer', color: '0E1A2B', opacity: 0.08, blur: 4, offset: 1, angle: 90 } });
  const note = (s, text, x, y, w, h, fs = 12) => { s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: HEX.accSoft }, line: { color: HEX.accSoft }, objectName: 'note-bg' });
    s.addText(text, { x: x + 0.18, y, w: w - 0.36, h, fontSize: fs, color: HEX.ink, valign: 'middle', isTextBox: true, margin: 0, objectName: 'note', paraSpaceAfter: 3 }); };
  const sub = (s, t, y = 1.0) => s.addText(t, { x: 0.5, y, w: 12.33, h: 0.3, fontSize: 11, color: HEX.ink2, margin: 0, isTextBox: true });

  for (const dp of ['FF', '厨房']) {
    const A = D[dp], S = A[scope], k25 = S.kpi.p25, k26 = S.kpi.p26, m25 = S.kpi.m25, nc = S.nc;
    const cats = A.cats, wcats = cats.filter(c => !A.excl.includes(c));
    const FC = D.fc[dp][scope];
    const C = D.P[CUR.k][dp], P = D.P[PRV.k][dp];      // 今週・先週
    const SC = C[scope], SP = P[scope];
    const sec = dp; pres.addSection({ title: sec });
    const T = t => `${dp}｜${t}`;
    const add = t => { const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: sec }); s.addText(t, { placeholder: 'title' }); return s; };
    const ranked = STORES.map(st => { const o = A.stores[st]; return { st, s: ratio(o.p26.販売高, o.p25.販売高), g: ratio(o.p26.荒利益高, o.p25.荒利益高), w: wrOf(o.nc26), w25: wrOf(o.nc25), o }; });
    const rk = (key, asc) => { const a = [...ranked].sort((x, y) => asc ? x[key] - y[key] : y[key] - x[key]); return a.findIndex(x => x.st === scope) + 1; };

    // ===== 1 サマリー =====
    let s = add(T(`${SNAME} サマリー`));
    sub(s, `${Y}年${MO}/1〜${N}（${N}日間）と ${LY}年の同じ日付の比較`);
    const K = [['販売高（売上）', yen(k26.販売高), ratio(k26.販売高, k25.販売高), false, '前年 ' + yen(k25.販売高)],
      ['荒利益高', yen(k26.荒利益高), ratio(k26.荒利益高, k25.荒利益高), false, '前年 ' + yen(k25.荒利益高)],
      ['販売数', n0(k26.販売数) + '個', ratio(k26.販売数, k25.販売数), false, '前年 ' + n0(k25.販売数) + '個'],
      ['廃棄高', yen(nc.p26.廃棄高), ratio(nc.p26.廃棄高, nc.p25.廃棄高), true, '前年 ' + yen(nc.p25.廃棄高)],
      ['廃棄率', wrOf(nc.p26).toFixed(1) + '%', wrOf(nc.p26) - wrOf(nc.p25), true, '前年 ' + wrOf(nc.p25).toFixed(1) + '%', 'pt']];
    const cw = 2.3, gap = 0.2;
    K.forEach(([k, v, d, inv, ly, u], i) => {
      const x = 0.5 + i * (cw + gap), y = 1.4;
      card(s, x, y, cw, 1.7, 'kpi-' + i);
      s.addText(k, { x: x + 0.2, y: y + 0.14, w: cw - 0.4, h: 0.28, fontSize: 11, color: HEX.ink3, bold: true, margin: 0, isTextBox: true });
      s.addText(v, { x: x + 0.2, y: y + 0.42, w: cw - 0.4, h: 0.58, fontSize: 22, bold: true, color: HEX.ink, margin: 0, isTextBox: true, fit: 'shrink' });
      const good = u ? d < 0 : inv ? d < 100 : d > 100;
      s.addText(u ? ptxt(d) : '前年比 ' + rtxt(d), { x: x + 0.2, y: y + 1.04, w: 1.55, h: 0.27, fontSize: 10.5, bold: true, color: good ? HEX.good : HEX.bad, fill: { color: good ? HEX.goodBg : HEX.badBg }, align: 'center', margin: 0, isTextBox: true });
      s.addText(ly, { x: x + 0.2, y: y + 1.36, w: cw - 0.4, h: 0.24, fontSize: 10, color: HEX.ink3, margin: 0, isTextBox: true });
    });
    const catsD = cats.filter(c => S.cat.p25[c] && S.cat.p25[c].荒利益高 > 0).map(c => ({ c, diff: S.cat.p26[c].荒利益高 - S.cat.p25[c].荒利益高 }));
    const best = [...catsD].sort((a, b) => b.diff - a.diff)[0], worst = [...catsD].sort((a, b) => a.diff - b.diff)[0];
    const hw = [...ranked].sort((a, b) => b.w - a.w)[0], lw = [...ranked].sort((a, b) => a.w - b.w)[0];
    const lo = ranked.filter(x => x.g < 100).map(x => `${x.st}（${rtxt(x.g)}）`);
    const c1 = SC.kpi.p26, c0 = SP.kpi.p26, cL = SC.kpi.p25;
    const B = [
      `荒利益率 ${(k25.荒利益高 / k25.販売高 * 100).toFixed(1)}% → ${(k26.荒利益高 / k26.販売高 * 100).toFixed(1)}%。1個あたり荒利益 ${yen(k25.荒利益高 / k25.販売数)} → ${yen(k26.荒利益高 / k26.販売数)}`,
      `荒利益高で伸びたのは ${best.c}（${syen(best.diff)}）、${worst.diff < 0 ? '落ちたのは' : '伸びが一番小さいのは'} ${worst.c}（${syen(worst.diff)}）`,
      isAll ? `荒利益高が前年割れの店舗：${lo.length ? lo.join('、') : 'なし'}。廃棄率が最も高いのは ${hw.st}（${hw.w.toFixed(1)}%）、最も低いのは ${lw.st}（${lw.w.toFixed(1)}%）`
            : `${NS}店舗の中で：売上の伸び ${rk('s')}位（${rtxt(ratio(k26.販売高, k25.販売高))}）、荒利益の伸び ${rk('g')}位（${rtxt(ratio(k26.荒利益高, k25.荒利益高))}）、廃棄率の低さ ${rk('w', true)}位（${wrOf(nc.p26).toFixed(1)}%）`,
      `今週（${CUR.range}）：売上 ${yen(c1.販売高)}（先週比 ${rtxt(ratio(c1.販売高, c0.販売高))}・前年比 ${rtxt(ratio(c1.販売高, cL.販売高))}）、荒利益高 ${yen(c1.荒利益高)}（先週比 ${rtxt(ratio(c1.荒利益高, c0.荒利益高))}・前年比 ${rtxt(ratio(c1.荒利益高, cL.荒利益高))}）`,
      `${MO}月着地見込み：販売高 ${yen(FC.販売高.fc)}（前年 ${yen(m25.販売高)}・${rtxt(ratio(FC.販売高.fc, m25.販売高))}）、荒利益高 ${yen(FC.荒利益高.fc)}（前年 ${yen(m25.荒利益高)}・${rtxt(ratio(FC.荒利益高.fc, m25.荒利益高))}）`];
    card(s, 0.5, 3.35, 12.33, 3.5, 'summary');
    s.addText('現状', { x: 0.75, y: 3.5, w: 3, h: 0.32, fontSize: 12, bold: true, color: HEX.ty, margin: 0, isTextBox: true });
    s.addText(B.map((b, i) => ({ text: b, options: { bullet: true, breakLine: i < B.length - 1, paraSpaceAfter: 7 } })), { x: 0.75, y: 3.88, w: 11.85, h: 2.85, fontSize: 14, color: HEX.ink, valign: 'top', margin: 0, isTextBox: true, fit: 'shrink' });

    // ===== 2 日別 販売高 =====
    s = add(T('日別 販売高（売上）の推移'));
    const lab = Array.from({ length: DIM }, (_, i) => String(i + 1));
    const lineOpt = (x, y, w, h, t) => Object.assign(chartBase(), { x, y, w, h, chartColors: [HEX.ly, HEX.ty], lineSize: 2, lineDataSymbol: 'circle', lineDataSymbolSize: 5, showLegend: true, legendPos: 't', valAxisLabelFormatCode: '#,##0', showCatAxisTitle: true, catAxisTitle: '日', catAxisTitleFontSize: 10, catAxisTitleColor: HEX.ink3 }, t ? { showTitle: true, title: t } : {});
    s.addChart(pres.charts.LINE, [{ name: `${LY}年${MO}月`, labels: lab, values: S.daily25.販売高 }, { name: `${Y}年${MO}月（${N}日まで）`, labels: lab.slice(0, N), values: S.daily26.販売高.slice(0, N) }], lineOpt(0.5, 1.1, 8.2, 5.75));
    s.addText(`${MO}月 着地見込み`, { x: 9.0, y: 1.2, w: 3.8, h: 0.32, fontSize: 13, bold: true, color: HEX.ink, margin: 0, isTextBox: true });
    s.addTable([[H('', { align: 'left' }), H(`前年${MO}月 実績`), H(`${Y}年${MO}月 見込み`), H('前年比')],
      [Tc('販売高（売上）', { align: 'left', bold: true }), Tc(yen(m25.販売高)), Tc(yen(FC.販売高.fc), { bold: true }), RC(ratio(FC.販売高.fc, m25.販売高))],
      [Tc('荒利益高', { align: 'left', bold: true }), Tc(yen(m25.荒利益高)), Tc(yen(FC.荒利益高.fc), { bold: true }), RC(ratio(FC.荒利益高.fc, m25.荒利益高))]], Object.assign(tblOpts(9.0, 1.6, 3.83, [0.95, 1.0, 1.18, 0.7], 0.42), { fontSize: 10 }));
    note(s, `実績 ${MO}/1〜${N}：販売高 ${yen(k26.販売高)}（前年比 ${rtxt(ratio(k26.販売高, k25.販売高))}）。\n見込みは、${MO}/1〜${N}の前年比（販売 ${rtxt(FC.販売高.r * 100)}・荒利 ${rtxt(FC.荒利益高.r * 100)}）を前年の${MO}/${N + 1}〜${DIM}の実績に掛けた試算です。\n曜日の並び：${Y}年は${M.w26.first}〜${M.w26.last}（土日祝${M.w26.we}日）、${LY}年は${M.w25.first}〜${M.w25.last}（土日祝${M.w25.we}日）。`, 9.0, 3.35, 3.83, 3.0, 11);

    // ===== 3 荒利益高 =====
    s = add(T('荒利益高の推移とカテゴリー別'));
    s.addChart(pres.charts.LINE, [{ name: `${LY}年${MO}月`, labels: lab, values: S.daily25.荒利益高 }, { name: `${Y}年${MO}月（${N}日まで）`, labels: lab.slice(0, N), values: S.daily26.荒利益高.slice(0, N) }], lineOpt(0.5, 1.1, 6.3, 4.4, '日別 荒利益高'));
    s.addChart(pres.charts.BAR, [{ name: String(LY), labels: cats, values: cats.map(c => S.cat.p25[c].荒利益高) }, { name: String(Y), labels: cats, values: cats.map(c => S.cat.p26[c].荒利益高) }],
      Object.assign(chartBase(), { x: 7.05, y: 1.1, w: 5.78, h: 4.4, barDir: 'col', barGrouping: 'clustered', chartColors: [HEX.ly, HEX.ty], showLegend: true, legendPos: 't', showTitle: true, title: `カテゴリー別 荒利益高（${MO}/1〜${N}）`, valAxisLabelFormatCode: '#,##0', barGapWidthPct: 60 }));
    note(s, `荒利益高 ${yen(k26.荒利益高)}（前年 ${yen(k25.荒利益高)}・前年比 ${rtxt(ratio(k26.荒利益高, k25.荒利益高))}）。荒利益率 ${(k25.荒利益高 / k25.販売高 * 100).toFixed(1)}% → ${(k26.荒利益高 / k26.販売高 * 100).toFixed(1)}%。\nカテゴリー別の前年比：${cats.filter(c => S.cat.p25[c].荒利益高 > 0).map(c => `${c} ${rtxt(ratio(S.cat.p26[c].荒利益高, S.cat.p25[c].荒利益高))}`).join('、')}`, 0.5, 5.7, 12.33, 1.15, 12);

    // ===== 4 先週比＋前年 =====
    s = add(T(`先週 vs 今週・前年　いくら上がった？下がった？（${SNAME}）`));
    sub(s, `今週 ${wkLabel(CUR)}　vs　先週 ${wkLabel(PRV)}　｜　前年＝${LY}年の今週と同じ日付（${CUR.range}）`, 0.98);
    const n1 = SC.nc.p26, n0_ = SP.nc.p26, nL = SC.nc.p25;
    const kt = [[H('指標', { align: 'left' }), H('先週'), H('今週'), H('先週との差'), H('先週比'), H('前年同日'), H('前年比')]];
    [['販売高（売上）', '販売高', 0, 0, c1, c0, cL], ['荒利益高', '荒利益高', 0, 0, c1, c0, cL], ['販売数', '販売数', 1, 0, c1, c0, cL], ['廃棄高', '廃棄高', 0, 1, n1, n0_, nL]].forEach(([lb, k, isN, inv, a, b, l]) => {
      kt.push([Tc(lb, { align: 'left', bold: true }), Tc(isN ? n0(b[k]) + '個' : yen(b[k]), { color: HEX.ink2 }), Tc(isN ? n0(a[k]) + '個' : yen(a[k]), { bold: true }), isN ? DN(a[k] - b[k], inv) : DY(a[k] - b[k], inv), RC(ratio(a[k], b[k]), inv), Tc(isN ? n0(l[k]) + '個' : yen(l[k]), { color: HEX.ink2 }), RC(ratio(a[k], l[k]), inv)]); });
    kt.push([Tc('廃棄率', { align: 'left', bold: true }), Tc(wrOf(n0_).toFixed(1) + '%', { color: HEX.ink2 }), Tc(wrOf(n1).toFixed(1) + '%', { bold: true }), DP(wrOf(n1) - wrOf(n0_)), Tc(''), Tc(wrOf(nL).toFixed(1) + '%', { color: HEX.ink2 }), DP(wrOf(n1) - wrOf(nL))]);
    s.addTable(kt, tblOpts(0.5, 1.35, 7.0, [1.25, 1.0, 1.0, 1.0, 0.85, 1.1, 0.8], 0.31));
    const ct4 = [[H('カテゴリー', { align: 'left' }), H('売上 先週'), H('売上 今週'), H('売上の差'), H('先週比'), H('前年比'), H('荒利の差')]];
    cats.forEach(c => { const a = SC.cat.p26[c], b = SP.cat.p26[c], l = SC.cat.p25[c];
      ct4.push([Tc(c, { align: 'left', bold: true, color: CATCOL[c] }), Tc(yen(b.販売高), { color: HEX.ink2 }), Tc(yen(a.販売高), { bold: true }), DY(a.販売高 - b.販売高), RC(ratio(a.販売高, b.販売高)), RC(ratio(a.販売高, l.販売高)), DY(a.荒利益高 - b.荒利益高)]); });
    const yCat = 1.35 + 0.31 * 6 + 0.22;
    s.addTable(ct4, tblOpts(0.5, yCat, 7.0, [1.3, 1.0, 1.0, 1.0, 0.85, 0.85, 1.0], 0.29));
    const pc = {}, pp = {}; SC.prod.forEach(r => pc[r.name] = r); SP.prod.forEach(r => pp[r.name] = r);
    const mv = [...new Set([...Object.keys(pc), ...Object.keys(pp)])].map(n => { const a = pc[n] || { amt: 0, sold: 0 }, b = pp[n] || { amt: 0, sold: 0 }; return { n, d: a.amt - b.amt, q: a.sold - b.sold, a0: b.amt, a1: a.amt }; });
    const mvT = (ttl, rows, col, bg) => { const t = [[H(ttl, { align: 'left', color: col, fill: { color: bg } }), H('先週 → 今週', { fill: { color: bg } }), H('個数', { fill: { color: bg } }), H('売上の差', { fill: { color: bg } })]];
      rows.forEach(r => t.push([Tc(short(r.n, 12), { align: 'left', fontSize: 9.5 }), Tc(`${yen(r.a0)} → ${yen(r.a1)}`, { fontSize: 9, color: HEX.ink2 }), DN(r.q, false, { fontSize: 9.5 }), DY(r.d, false, { fontSize: 9.5 })]));
      if (!rows.length) t.push([Tc('なし', { align: 'left' }), Tc(''), Tc(''), Tc('')]); return t; };
    s.addTable(mvT('上がった単品 TOP5', mv.filter(r => r.d > 0).sort((a, b) => b.d - a.d).slice(0, 5), HEX.good, HEX.goodBg), tblOpts(7.75, 1.35, 5.08, [2.0, 1.55, 0.68, 0.85], 0.31));
    s.addTable(mvT('下がった単品 TOP5', mv.filter(r => r.d < 0).sort((a, b) => a.d - b.d).slice(0, 5), HEX.bad, HEX.badBg), tblOpts(7.75, 3.65, 5.08, [2.0, 1.55, 0.68, 0.85], 0.31));
    const cd = cats.map(c => ({ c, d: SC.cat.p26[c].販売高 - SP.cat.p26[c].販売高 })).sort((a, b) => b.d - a.d);
    note(s, `売上は先週より ${syen(c1.販売高 - c0.販売高)}（先週比 ${rtxt(ratio(c1.販売高, c0.販売高))}）、荒利益高は ${syen(c1.荒利益高 - c0.荒利益高)}（${rtxt(ratio(c1.荒利益高, c0.荒利益高))}）。前年の同じ日付と比べると 売上 ${rtxt(ratio(c1.販売高, cL.販売高))}・荒利 ${rtxt(ratio(c1.荒利益高, cL.荒利益高))}。\n一番伸びたカテゴリーは ${cd[0].c}（${syen(cd[0].d)}）、一番落ちたのは ${cd[cd.length - 1].c}（${syen(cd[cd.length - 1].d)}）。`, 0.5, yCat + 0.29 * (cats.length + 1) + 0.3, 7.0, 6.85 - (yCat + 0.29 * (cats.length + 1) + 0.3), 11.5);

    // ===== 5 店舗別 先週比（全店のみ） =====
    if (isAll) {
      s = add(T('店舗別 先週比・前年比（先週から上がった順）'));
      sub(s, `今週 ${wkLabel(CUR)}　vs　先週 ${wkLabel(PRV)}　｜　前年比＝今週と ${LY}年の同じ日付の比較`, 0.98);
      const rows = STORES.map(st => ({ st, a: C.stores[st].p26, b: P.stores[st].p26, l: C.stores[st].p25, wa: C.stores[st].nc26, wb: P.stores[st].nc26 })).sort((x, y) => (y.a.販売高 - y.b.販売高) - (x.a.販売高 - x.b.販売高));
      const sh = [[H('店舗', { align: 'left' }), H('売上 先週'), H('売上 今週'), H('売上の差'), H('先週比'), H('前年比'), H('荒利 先週'), H('荒利 今週'), H('荒利の差'), H('先週比'), H('前年比'), H('廃棄高の差')]];
      const rowOf = (nm, a, b, l, wa, wb, o = {}) => [Tc(nm, Object.assign({ align: 'left', bold: true }, o)), Tc(yen(b.販売高), Object.assign({ color: HEX.ink2 }, o)), Tc(yen(a.販売高), Object.assign({ bold: true }, o)), DY(a.販売高 - b.販売高, false, o), RC(ratio(a.販売高, b.販売高), false, o), RC(ratio(a.販売高, l.販売高), false, o),
        Tc(yen(b.荒利益高), Object.assign({ color: HEX.ink2 }, o)), Tc(yen(a.荒利益高), Object.assign({ bold: true }, o)), DY(a.荒利益高 - b.荒利益高, false, o), RC(ratio(a.荒利益高, b.荒利益高), false, o), RC(ratio(a.荒利益高, l.荒利益高), false, o), DY(wa.廃棄高 - wb.廃棄高, true, o)];
      rows.forEach(r => sh.push(rowOf(r.st, r.a, r.b, r.l, r.wa, r.wb)));
      sh.push(rowOf(`${NS}店合計`, c1, c0, cL, n1, n0_, { fill: { color: HEX.accSoft } }));
      s.addTable(sh, tblOpts(0.5, 1.4, 12.33, [1.2, 1.05, 1.05, 1.0, 0.85, 0.85, 1.0, 1.0, 1.0, 0.85, 0.85, 1.0], 0.38));
      const up = rows[0], dn = rows[rows.length - 1], yl = rows.filter(r => r.a.販売高 < r.l.販売高).map(r => r.st);
      note(s, `先週から一番上がったのは ${up.st}（売上 ${syen(up.a.販売高 - up.b.販売高)}）、一番下がったのは ${dn.st}（売上 ${syen(dn.a.販売高 - dn.b.販売高)}）。\n今週の売上が前年の同じ日付を下回った店舗：${yl.length ? yl.join('、') : 'なし'}。`, 0.5, 1.4 + 0.38 * (NS + 2) + 0.35, 12.33, 1.05, 12);
    }

    // ===== 週別の推移（前年比と 1日あたりの金額）。ダッシュボードの「販売高・荒利益高・廃棄高の推移（週別）」と同じデータ =====
    const WR = ((D.WTR || {})[dp] || {})[scope] || [];
    if (WR.length) {
      s = add(T(`曜日別の販売数（カテゴリー別）・週別の推移`));
      const per = isAll ? '1店1日あたり' : '1日あたり', wl = WR.map(r => r.label);
      const q = (a, b) => b > 0 ? +(a / b * 100).toFixed(1) : null, pdv = (r, k) => r.sd ? Math.round(r[k] / r.sd) : null;
      const lo = (x, y, t, colors, fmt, extra = {}) => Object.assign(chartBase(), { x, y, w: 6.05, h: 2.72, chartColors: colors, lineSize: 2, lineDataSymbol: 'circle', lineDataSymbolSize: 5, showLegend: true, legendPos: 't', showTitle: true, title: t,
        valAxisLabelFormatCode: fmt, catAxisLabelFontSize: 9, showValue: false }, extra);
      // 左上：曜日別・カテゴリー別の 1日あたり販売数（今年 1日〜N日）。祝日は「日・祝」に入れる。全店は全店合計の1日あたり
      const WDL = ['月', '火', '水', '木', '金', '土', '日・祝'], wdi = d => M.hol26[d] ? 6 : (DT(d).getDay() + 6) % 7;
      const Q = D.tcat[dp][scope]['q' + Y], wcnt = WDL.map(() => 0);
      for (let d = 1; d <= N; d++) if (S.cov26[d - 1]) wcnt[wdi(d)] += isAll ? 1 : S.cov26[d - 1];
      const wq = cats.map(c => WDL.map((_, k) => { let a = 0; for (let d = 1; d <= N; d++) if (S.cov26[d - 1] && wdi(d) === k) a += Q[c][d - 1]; return wcnt[k] ? Math.round(a / wcnt[k]) : null; }));
      const ndays = WDL.map((_, k) => { let n = 0; for (let d = 1; d <= N; d++) if (S.cov26[d - 1] && wdi(d) === k) n++; return n; });
      s.addChart(pres.charts.LINE, cats.map((c, ci) => ({ name: c, labels: WDL, values: wq[ci] })),
        Object.assign(chartBase(), { x: 0.5, y: 1.33, w: 6.05, h: 2.72, chartColors: cats.map(c => CATCOL[c]), lineSize: 2, lineDataSymbol: 'circle', lineDataSymbolSize: 6, showLegend: true, legendPos: 'r', showTitle: true,
          title: `曜日別 カテゴリー別の販売数（${isAll ? '全店合計・' : ''}1日あたり）`, valAxisLabelFormatCode: '#,##0', catAxisLabelFontSize: 9, legendFontSize: 9 }));
      const am = (x, y, k, ttl, col) => s.addChart(pres.charts.LINE, [{ name: `${LY}年（同じ日付）`, labels: wl, values: WR.map(r => pdv(r, k + '25')) }, { name: String(Y), labels: wl, values: WR.map(r => pdv(r, k + '26')) }],
        lo(x, y, `${ttl}（${per}）`, [HEX.ly, col], '#,##0'));
      am(6.78, 1.33, 's', '販売高', HEX.ty); am(0.5, 4.17, 'g', '荒利益高', '1F5FA6'); am(6.78, 4.17, 'w', '廃棄高', HEX.bad);
      const L = WR[WR.length - 1];
      s.addNotes(`最新の週 ${L.label}：販売前年比 ${rtxt(ratio(L.s26, L.s25))}、荒利前年比 ${rtxt(ratio(L.g26, L.g25))}、廃棄前年比 ${rtxt(ratio(L.w26, L.w25))}。` + (WR.some(r => r.miss.length) ? '（〇〇を除く）の週は、そのカテゴリーのデータが片方の年にしかないため除いています。' : ''));
    }

    // ===== 6 PSA/D =====
    s = add(T('先週比（1店1日あたり PSA/D）'));
    const cov = S.cov26, NCD = D.ncd[dp][scope];
    const grp = (p, f) => { const ds = []; for (let d = p.d0; d <= p.d1; d++) if (f(d) && cov[d - 1]) ds.push(d); return ds; };
    const sumOf = (arr, ds) => ds.reduce((a, d) => a + (arr[d - 1] || 0), 0), sd = ds => ds.reduce((a, d) => a + cov[d - 1], 0);
    const psa = (p, f) => { const ds = grp(p, f), n = sd(ds); if (!n) return null; const o = {}; ['販売高', '荒利益高', '販売数'].forEach(k => o[k] = sumOf(S.daily26[k], ds) / n);
      o.廃棄高 = wcats.reduce((a, c) => a + sumOf(S.dcat26[c].廃棄高, ds), 0) / n;
      const q = sumOf(NCD.販売数, ds), w = sumOf(NCD.廃棄数, ds); o.wr = q + w ? w / (q + w) * 100 : 0; o.days = ds.length; return o; };
    const F = { all: () => true, wk: d => !isOff(d), we: d => isOff(d) };
    const G = Object.fromEntries(Object.keys(F).map(k => [k, [psa(PRV, F[k]), psa(CUR, F[k])]]));
    sub(s, `先週＝${PRV.range}（${G.all[0].days}日）　今週＝${CUR.range}（${G.all[1].days}日）　平日：先週${G.wk[0] ? G.wk[0].days : 0}日・今週${G.wk[1] ? G.wk[1].days : 0}日／土日祝：先週${G.we[0] ? G.we[0].days : 0}日・今週${G.we[1] ? G.we[1].days : 0}日${isAll ? `　（${NS}店の平均）` : ''}`, 0.98);
    const pt6 = [[H('', { align: 'left' }), H('全体 先週'), H('全体 今週'), H('先週比'), H('平日 先週'), H('平日 今週'), H('先週比'), H('土日祝 先週'), H('土日祝 今週'), H('先週比')]];
    [['販売高（売上）', '販売高', 0, 0], ['荒利益高', '荒利益高', 0, 0], ['販売数', '販売数', 1, 0], ['廃棄高', '廃棄高', 0, 1]].forEach(([lb, k, isN, inv]) => {
      const row = [Tc(lb, { align: 'left', bold: true })];
      ['all', 'wk', 'we'].forEach(g => { const [b, a] = G[g]; if (!a || !b) { row.push(Tc('—'), Tc('—'), Tc('—')); return; }
        row.push(Tc(isN ? b[k].toFixed(1) + '個' : yen(b[k]), { color: HEX.ink2 }), Tc(isN ? a[k].toFixed(1) + '個' : yen(a[k]), { bold: true }), RC(ratio(a[k], b[k]), inv)); });
      pt6.push(row); });
    { const row = [Tc('廃棄率', { align: 'left', bold: true })];
      ['all', 'wk', 'we'].forEach(g => { const [b, a] = G[g]; if (!a || !b) { row.push(Tc('—'), Tc('—'), Tc('—')); return; } row.push(Tc(b.wr.toFixed(1) + '%', { color: HEX.ink2 }), Tc(a.wr.toFixed(1) + '%', { bold: true }), DP(a.wr - b.wr)); });
      pt6.push(row); }
    s.addTable(pt6, tblOpts(0.5, 1.38, 8.3, [1.3, 0.8, 0.8, 0.7, 0.8, 0.8, 0.7, 0.8, 0.8, 0.8].map(v => v * 8.3 / 8.3), 0.33));
    const dowV = p => { const o = {}; for (let d = p.d0; d <= p.d1; d++) if (cov[d - 1]) o[wdOf(d)] = S.daily26.販売高[d - 1] / cov[d - 1]; return o; };
    const W7 = ['月', '火', '水', '木', '金', '土', '日'], dv0 = dowV(PRV), dv1 = dowV(CUR);
    s.addChart(pres.charts.BAR, [{ name: '先週', labels: W7, values: W7.map(w => dv0[w] || 0) }, { name: '今週', labels: W7, values: W7.map(w => dv1[w] || 0) }],
      Object.assign(chartBase(), { x: 9.05, y: 1.3, w: 3.78, h: 3.3, barDir: 'col', barGrouping: 'clustered', chartColors: [HEX.ly, HEX.ty], showLegend: true, legendPos: 't', showTitle: true, title: '曜日別 販売高（1店あたり）', valAxisLabelFormatCode: '#,##0', barGapWidthPct: 50 }));
    const pc6 = [[H('カテゴリー', { align: 'left' }), H('売上 先週'), H('売上 今週'), H('先週比'), H('荒利 今週'), H('先週比'), H('廃棄 先週'), H('廃棄 今週')]];
    const cps = (p, c, k) => { const ds = grp(p, F.all); return sumOf(S.dcat26[c][k], ds) / sd(ds); };
    cats.forEach(c => { const ex = A.excl.includes(c);
      pc6.push([Tc(c, { align: 'left', bold: true, color: CATCOL[c] }), Tc(yen(cps(PRV, c, '販売高')), { color: HEX.ink2 }), Tc(yen(cps(CUR, c, '販売高')), { bold: true }), RC(ratio(cps(CUR, c, '販売高'), cps(PRV, c, '販売高'))),
        Tc(yen(cps(CUR, c, '荒利益高'))), cps(PRV, c, '荒利益高') > 0 ? RC(ratio(cps(CUR, c, '荒利益高'), cps(PRV, c, '荒利益高'))) : Tc('—'), Tc(ex ? '—' : yen(cps(PRV, c, '廃棄高')), { color: HEX.ink2 }), Tc(ex ? '—' : yen(cps(CUR, c, '廃棄高')))]); });
    const yPc = 1.38 + 0.33 * 6 + 0.25;
    s.addTable(pc6, tblOpts(0.5, yPc, 8.3, [1.3, 1.0, 1.0, 0.85, 1.0, 0.85, 1.15, 1.15], 0.29));
    const ga = G.all;
    note(s, `売上（1店1日）は平日 ${G.wk[0] && G.wk[1] ? rtxt(ratio(G.wk[1].販売高, G.wk[0].販売高)) : '—'}、土日祝 ${G.we[0] && G.we[1] ? rtxt(ratio(G.we[1].販売高, G.we[0].販売高)) : '—'}（先週＝100%）。\n1店1日あたりの廃棄高は ${yen(ga[0].廃棄高)} → ${yen(ga[1].廃棄高)}（${rtxt(ratio(ga[1].廃棄高, ga[0].廃棄高))}）。${ga[1].廃棄高 <= ga[0].廃棄高 ? '改善しています。' : '増えています。仕込み量を見直します。'}`, 9.05, 4.8, 3.78, 1.7, 10.5);

    // ===== 7 カテゴリー別 =====
    s = add(T('カテゴリー別'));
    s.addChart(pres.charts.BAR, [{ name: String(LY), labels: cats, values: cats.map(c => S.cat.p25[c].販売高) }, { name: String(Y), labels: cats, values: cats.map(c => S.cat.p26[c].販売高) }],
      Object.assign(chartBase(), { x: 0.5, y: 1.1, w: 5.3, h: 5.75, barDir: 'col', barGrouping: 'clustered', chartColors: [HEX.ly, HEX.ty], showLegend: true, legendPos: 't', showTitle: true, title: `販売高（${MO}/1〜${N}）`, valAxisLabelFormatCode: '#,##0', barGapWidthPct: 60 }));
    const ct = [[H('カテゴリー', { align: 'left' }), H(`販売高 ${Y}`), H('前年比'), H(`荒利益高 ${Y}`), H('前年比'), H('廃棄高'), H('廃棄率')]];
    cats.forEach(c => { const a = S.cat.p25[c], b = S.cat.p26[c], ex = A.excl.includes(c);
      ct.push([Tc(c, { align: 'left', bold: true, color: CATCOL[c] }), Tc(yen(b.販売高)), RC(ratio(b.販売高, a.販売高)), Tc(yen(b.荒利益高)), RC(ratio(b.荒利益高, a.荒利益高)), Tc(ex ? '—' : yen(b.廃棄高)), Tc(ex ? '—' : wrOf(b).toFixed(1) + '%', { color: !ex && wrOf(b) >= 15 ? HEX.bad : HEX.ink, bold: !ex && wrOf(b) >= 15 })]); });
    s.addTable(ct, tblOpts(6.1, 1.2, 6.73, [1.35, 1.0, 0.8, 1.05, 0.8, 0.88, 0.85], 0.36));
    note(s, `売上の前年比：${cats.map(c => `${c} ${rtxt(ratio(S.cat.p26[c].販売高, S.cat.p25[c].販売高))}`).join('、')}${dp === 'FF' ? '\nマチカフェは廃棄が出ないため、廃棄高・廃棄率から除いています。' : ''}`, 6.1, 1.2 + 0.36 * (cats.length + 1) + 0.35, 6.73, 1.35, 12);

    // ===== 8 構成比 =====
    s = add(T(`販売高と廃棄高の構成比（${Y}年${MO}/1〜${N}）`));
    const pieOpt = (x, t) => Object.assign(chartBase(), { x, y: 1.1, w: 6.0, h: 5.75, holeSize: 55, showPercent: true, showValue: false, showLegend: true, legendPos: 'r', showTitle: true, title: t, dataLabelColor: 'FFFFFF', dataLabelFontSize: 10 });
    s.addChart(pres.charts.DOUGHNUT, [{ name: '販売高', labels: cats, values: cats.map(c => S.cat.p26[c].販売高) }], Object.assign(pieOpt(0.5, `販売高 構成比（合計 ${yen(k26.販売高)}）`), { chartColors: cats.map(c => CATCOL[c]) }));
    s.addChart(pres.charts.DOUGHNUT, [{ name: '廃棄高', labels: wcats, values: wcats.map(c => S.cat.p26[c].廃棄高) }], Object.assign(pieOpt(6.83, `廃棄高 構成比（合計 ${yen(nc.p26.廃棄高)}）`), { chartColors: wcats.map(c => CATCOL[c]) }));

    // ===== 9 店舗比較 =====
    s = add(T(isAll ? '店舗別 売上・荒利益・廃棄' : `${NS}店舗の中での${scope}`));
    const st9 = [[H('店舗', { align: 'left' }), H('販売高'), H('前年比'), H('荒利益高'), H('前年比'), H('廃棄高'), H('前年比'), H('廃棄率'), H('前年 廃棄率')]];
    ranked.forEach(r => { const o = r.o, me = r.st === scope, f = me ? { fill: { color: HEX.star } } : {};
      st9.push([Tc((me ? '★ ' : '') + r.st, Object.assign({ align: 'left', bold: true }, f)), Tc(yen(o.p26.販売高), f), RC(r.s, false, f), Tc(yen(o.p26.荒利益高), f), RC(r.g, false, f), Tc(yen(o.nc26.廃棄高), f), RC(ratio(o.nc26.廃棄高, o.nc25.廃棄高), true, f),
        Tc(r.w.toFixed(1) + '%', Object.assign({ bold: true, color: r.w >= 10 ? HEX.bad : HEX.ink }, f)), Tc(r.w25.toFixed(1) + '%', Object.assign({ color: HEX.ink2 }, f))]); });
    const ac = A.ALL, af = { fill: { color: HEX.accSoft } };
    st9.push([Tc('全店', Object.assign({ align: 'left', bold: true }, af)), Tc(yen(ac.kpi.p26.販売高), Object.assign({ bold: true }, af)), RC(ratio(ac.kpi.p26.販売高, ac.kpi.p25.販売高), false, af), Tc(yen(ac.kpi.p26.荒利益高), Object.assign({ bold: true }, af)), RC(ratio(ac.kpi.p26.荒利益高, ac.kpi.p25.荒利益高), false, af),
      Tc(yen(ac.nc.p26.廃棄高), Object.assign({ bold: true }, af)), RC(ratio(ac.nc.p26.廃棄高, ac.nc.p25.廃棄高), true, af), Tc(wrOf(ac.nc.p26).toFixed(1) + '%', Object.assign({ bold: true }, af)), Tc(wrOf(ac.nc.p25).toFixed(1) + '%', af)]);
    s.addTable(st9, tblOpts(0.5, 1.15, 12.33, [1.4, 1.45, 1.05, 1.45, 1.05, 1.35, 1.05, 1.25, 1.28], 0.32));
    const yS = 1.15 + 0.32 * (NS + 2) + 0.2;
    s.addChart(pres.charts.BAR, [{ name: String(LY), labels: STORES, values: ranked.map(r => +r.w25.toFixed(1)) }, { name: String(Y), labels: STORES, values: ranked.map(r => +r.w.toFixed(1)) }],
      Object.assign(chartBase(), { x: 0.5, y: yS, w: 7.2, h: 6.9 - yS, barDir: 'bar', barGrouping: 'clustered', chartColors: [HEX.ly, HEX.bad], showLegend: true, legendPos: 'r', showTitle: true, title: '店舗別 廃棄率（%）', valAxisLabelFormatCode: '0.0', showValue: true, dataLabelFormatCode: '0.0', dataLabelPosition: 'outEnd', barGapWidthPct: 40 }));
    const me = ranked.find(r => r.st === scope);
    note(s, isAll ? `廃棄率が最も高いのは ${hw.st}（${hw.w.toFixed(1)}%）。最も低い ${lw.st}（${lw.w.toFixed(1)}%）の仕込み量とタイミングを他店に共有します。`
      : `${scope}の廃棄率は ${me.w.toFixed(1)}%（前年 ${me.w25.toFixed(1)}%）。${lw.st === scope ? `${NS}店舗の中で最も低い水準です。` : `最も低い ${lw.st}（${lw.w.toFixed(1)}%）の仕込み量とタイミングを参考にします。`}`, 8.0, yS + 0.15, 4.83, 6.9 - yS - 0.3, 12);

    // ===== 10 単品別 生産判断 =====
    s = add(T('単品別 生産判断（荒利益高 上位14）'));
    sub(s, `${MO}/1〜${N}（${N}日間）。廃棄率＝廃棄数 ÷（販売数＋廃棄数）。完売日率＝販売のあった日のうち廃棄ゼロの日の割合`, 0.98);
    const VL = { increase: ['増産', HEX.good, HEX.goodBg], keep: ['維持', HEX.ty, HEX.accSoft], watch: ['注意', HEX.warn, HEX.warnBg], reduce: ['減産', HEX.bad, HEX.badBg], hold: ['保留', HEX.ink3, HEX.bg] };
    const pt = [[H('判定', { align: 'center' }), H('商品名', { align: 'left' }), H('販売数'), H('販売高'), H('荒利益高'), H('廃棄高'), H('廃棄率'), H('完売日率'), H('生産の目安', { align: 'left' })]];
    [...S.prod].sort((a, b) => b.gp - a.gp).slice(0, 14).forEach(r => { const [lb, c, bg] = VL[r.v] || VL.keep;
      const adv = r.v === 'hold' ? 'データ不足のため判定しない' : r.v === 'reduce' ? cutAdv(r, isAll ? '1店1日' : '1日') : r.v === 'increase' ? '売切れ時 +1〜2個' : r.v === 'watch' ? 'ピーク後の追加を控える' : '現状維持';
      pt.push([Tc(lb, { align: 'center', bold: true, color: c, fill: { color: bg }, fontSize: 10.5 }), Tc(short(r.name), { align: 'left', fontSize: 10.5 }), Tc(n0(r.sold)), Tc(yen(r.amt)), Tc(yen(r.gp)), Tc(yen(r.wy)), Tc((r.wr * 100).toFixed(1) + '%', { color: r.wr >= 0.15 ? HEX.bad : HEX.ink, bold: r.wr >= 0.15 }), Tc((r.so * 100).toFixed(0) + '%'), Tc(adv, { align: 'left', fontSize: 10.5 })]); });
    s.addTable(pt, tblOpts(0.5, 1.35, 12.33, [0.7, 3.5, 0.8, 1.05, 1.05, 0.9, 0.85, 0.88, 2.6], 0.355));

    // ===== 11 アクション =====
    s = add(T('店舗 × 単品 アクション'));
    const it = [[H('増産（機会ロスの可能性）', { align: 'left', color: HEX.good, fill: { color: HEX.goodBg } }), H('店舗', { fill: { color: HEX.goodBg } }), H('販売/日', { fill: { color: HEX.goodBg } })]];
    S.inc.slice(0, 10).forEach(r => it.push([Tc(short(r.name), { align: 'left', fontSize: 10.5 }), Tc(r.store), Tc(r.per.toFixed(1) + '個')]));
    if (!S.inc.length) it.push([Tc('該当なし', { align: 'left' }), Tc(''), Tc('')]);
    s.addTable(it, tblOpts(0.5, 1.15, 5.9, [3.6, 1.1, 1.2], 0.36));
    const dt = [[H('減産（作りすぎ）', { align: 'left', color: HEX.bad, fill: { color: HEX.badBg } }), H('店舗', { fill: { color: HEX.badBg } }), H('廃棄率', { fill: { color: HEX.badBg } }), H('減らす数', { align: 'left', fill: { color: HEX.badBg } })]];
    S.dec.slice(0, 10).forEach(r => dt.push([Tc(short(r.name), { align: 'left', fontSize: 10.5 }), Tc(r.store), Tc((r.wr * 100).toFixed(0) + '%', { color: HEX.bad, bold: true }), Tc(cutAdv(r), { align: 'left', fontSize: 10.5 })]));
    if (!S.dec.length) dt.push([Tc('該当なし', { align: 'left' }), Tc(''), Tc(''), Tc('')]);
    s.addTable(dt, tblOpts(6.65, 1.15, 6.18, [2.65, 0.85, 0.78, 1.9], 0.36));
    s.addText(`増産：期間中（${N}日間）廃棄ゼロで、毎日安定して売れている単品。減産：廃棄率20%以上。減らす数は廃棄の約8割まで（売り切れ防止）。`, { x: 0.5, y: 6.55, w: 12.33, h: 0.35, fontSize: 10.5, color: HEX.ink3, margin: 0, isTextBox: true });

    // ===== 12 曜日・天気 =====
    // 1日あたりの売上（販売高）を 平日・土曜・日曜祝日 で、前年（前年同月の全日）と今年（今月1日〜N日）の両方で出す。全店の行は全店合計の1日あたり
    s = add(T(`曜日・祝日・天気の影響（1日あたりの売上）`));
    sub(s, `前年＝${LY}年${MO}月の全日、今年＝${Y}年${MO}/1〜${N}。全店は${NS}店合計の1日あたり、店舗は1店の1日あたり。平日比＝平日を100%とした売上`, 0.98);
    const offT = d => M.hol26[d] || DT(d).getDay() === 0 ? '日祝' : DT(d).getDay() === 6 ? '土' : '平日';
    const ty26 = (x, typ) => { const Q = A[x], st = x === 'ALL'; let a = 0, n = 0, nd = 0;
      for (let d = 1; d <= N; d++) { if (!Q.cov26[d - 1] || offT(d) !== typ) continue; a += Q.daily26.販売高[d - 1]; n += Q.cov26[d - 1]; nd++; }
      return n ? (st ? a / nd : a / n) : null; };
    const PR = (v, o = {}) => v == null ? Tc('—', o) : Tc(v.toFixed(0) + '%', Object.assign({ bold: true, color: v >= 105 ? HEX.good : v <= 90 ? HEX.bad : HEX.warn }, o));
    const wt = [[H('店舗', { align: 'left' }), H(`平日 ${LY}`), H(`平日 ${Y}`), H(`土曜 ${LY}`), H(`土曜 ${Y}`), H('土曜 平日比'), H(`日祝 ${LY}`), H(`日祝 ${Y}`), H('日祝 平日比'), H('雨の日 荒利'), H('雨の日 廃棄')]];
    ['ALL', ...STORES].forEach(x => { const o = A[x].st, me = x === scope && !isAll, f = me ? { fill: { color: HEX.star } } : {}, g = { color: HEX.ink2 };
      const w6 = ty26(x, '平日'), sa6 = ty26(x, '土'), su6 = ty26(x, '日祝');
      wt.push([Tc((me ? '★ ' : '') + (x === 'ALL' ? '全店' : x), Object.assign({ align: 'left', bold: true }, f)),
        Tc(yen(o['平日'].amt), Object.assign({}, g, f)), Tc(w6 == null ? '—' : yen(w6), Object.assign({ bold: true }, f)),
        Tc(yen(o['土'].amt), Object.assign({}, g, f)), Tc(sa6 == null ? '—' : yen(sa6), Object.assign({ bold: true }, f)), PR(sa6 != null && w6 ? sa6 / w6 * 100 : null, f),
        Tc(yen(o['日祝'].amt), Object.assign({}, g, f)), Tc(su6 == null ? '—' : yen(su6), Object.assign({ bold: true }, f)), PR(su6 != null && w6 ? su6 / w6 * 100 : null, f),
        RC(100 + o.wet.gp * 100, false, f), RC(100 + o.wet.wy * 100, true, f)]); });
    s.addTable(wt, tblOpts(0.5, 1.35, 12.33, [1.05, 1.13, 1.13, 1.13, 1.13, 1.0, 1.13, 1.13, 1.0, 1.06, 1.24], 0.31));
    const yW = 1.35 + 0.31 * (NS + 2) + 0.06;
    s.addText(`薄い数字＝前年、太い数字＝今年。雨の日は前年${MO}月の雨でない日＝100%（荒利益高・廃棄高）`, { x: 0.5, y: yW, w: 12.33, h: 0.26, fontSize: 10, color: HEX.ink3, margin: 0, isTextBox: true });
    const R = A.wx.res;
    s.addChart(pres.charts.BAR, [{ name: '土曜', labels: cats, values: cats.map(c => +((R[c] || R.ALL).qty.sat * 100).toFixed(1)) }, { name: '日曜・祝日', labels: cats, values: cats.map(c => +((R[c] || R.ALL).qty.sun * 100).toFixed(1)) }, { name: '雨の日', labels: cats, values: cats.map(c => +((R[c] || R.ALL).qty.wet * 100).toFixed(1)) }],
      Object.assign(chartBase(), { x: 0.5, y: yW + 0.32, w: 7.6, h: 6.9 - yW - 0.32, barDir: 'bar', barGrouping: 'clustered', chartColors: ['1F5FA6', 'D9822B', '8E6BB8'], showLegend: true, legendPos: 'r', showTitle: true, title: `カテゴリー別 販売数への影響（%・全店・前年${MO}月）`, valAxisLabelFormatCode: '0', barGapWidthPct: 40, catAxisLabelPos: 'low' }));
    const cb = A.wx.chukaBand;
    const ftx = A.ff && cb ? `気温が下がると中華まんが売れます。前年は最高${cb[0].hi}℃未満の日に1日平均 ${Math.round(cb[0].avg)}個、${cb[2].lo}℃以上の日は ${Math.round(cb[2].avg)}個（${NS}店合計）。` : '厨房は気温より曜日の影響が大きい（日曜・祝日は弁当が大きく減少）。';
    const me12 = A[scope], w6s = ty26(scope, '平日'), su6s = ty26(scope, '日祝');
    const ext = !isAll && w6s && su6s && Math.abs(su6s / w6s - me12.st['日祝'].amt / me12.st['平日'].amt) >= 0.3 ? `\n${scope}の日曜・祝日は、前年は平日の${(me12.st['日祝'].amt / me12.st['平日'].amt * 100).toFixed(0)}%でしたが、今年は${(su6s / w6s * 100).toFixed(0)}%。今年の売れ方を目安にします。` : '';
    note(s, ftx + ext, 8.4, yW + 0.45, 4.43, 6.9 - yW - 0.6, 11.5);

    // ===== 13 仕込みカレンダー =====
    const cal = S.cal.filter(r => r.d <= N + 7);   // 来週＝データ最終日の翌日から7日間（月末まで）
    s = add(T(`来週の仕込みカレンダー（${SNAME}${cal.length ? `・${md(cal[0].d)}〜${cal[cal.length - 1].d}` : ''}）`));
    if (M.fc) s.addText(`天気予報：${M.fc}`, { x: 0.5, y: 0.92, w: 10.3, h: 0.22, fontSize: 10, color: HEX.ink3, margin: 0, isTextBox: true });
    const ctab = [[H('日付', { align: 'left' }), H('区分', { align: 'left' }), H('天気予報', { align: 'left' }), H('最高'), H('降水'), H('予想 販売高'), H('平日比（荒利）'), H('判定', { align: 'center' })]];
    cal.forEach(r => { const sg = r.sig === 'chance' ? ['チャンス', HEX.good, HEX.goodBg] : r.sig === 'risk' ? ['リスク', HEX.bad, HEX.badBg] : ['通常', HEX.ink3, 'FFFFFF'];
      const we = r.typ !== '平日' ? { fill: { color: HEX.accSoft } } : {};
      ctab.push([Tc(`${md(r.d)}（${r.wd}）`, Object.assign({ align: 'left', bold: true }, we)), Tc(r.typ + (r.hol ? '・' + r.hol : ''), Object.assign({ align: 'left', fontSize: 10.5 }, we)), Tc(r.wx || '未確定', Object.assign({ align: 'left', fontSize: 10.5, color: r.wx ? HEX.ink : HEX.ink3 }, we)),
        Tc(r.tmax != null ? r.tmax + '℃' : '—', we), Tc(r.pop != null ? r.pop + '%' : '—', we), Tc(yen(r.exps), we), Tc((r.idx * 100).toFixed(0) + '%', Object.assign({ bold: true, color: r.idx >= 1.05 ? HEX.good : r.idx <= 0.9 ? HEX.bad : HEX.ink }, we)), Tc(sg[0], { align: 'center', bold: true, color: sg[1], fill: { color: sg[2] }, fontSize: 10.5 })]); });
    if (!cal.length) ctab.push([Tc(`${MO}月の残りの日はありません。`, { align: 'left', colspan: 8, color: HEX.ink2 })]);
    s.addTable(ctab, tblOpts(0.5, 1.1, 10.3, [1.25, 1.85, 1.35, 0.8, 0.8, 1.6, 1.05, 1.6], 0.355));
    const ST = S.st;
    // 今年の実績（1店1日）で、土曜・日祝が平日の何%か。前年の傾向と大きく違えば注意を書く
    const avg26 = f => { let a = 0, n = 0; for (let d = 1; d <= N; d++) if (S.cov26[d - 1] && f(d)) { a += S.daily26.販売高[d - 1]; n += S.cov26[d - 1]; } return n ? a / n : null; };
    const wkA = avg26(d => !isOff(d)), satA = avg26(d => DT(d).getDay() === 6 && !M.hol26[d]), sunA = avg26(d => DT(d).getDay() === 0 || !!M.hol26[d]);
    const warn = [['土曜', satA, ST['土'].amt / ST['平日'].amt], ['日曜・祝日', sunA, ST['日祝'].amt / ST['平日'].amt]].filter(([, a, ix]) => a != null && wkA && Math.abs(a / wkA - ix) >= 0.25)
      .map(([lb, a, ix]) => `注意：${lb}の売上は前年が平日の${(ix * 100).toFixed(0)}%でしたが、今年（${MO}/1〜${N}）は平日の${(a / wkA * 100).toFixed(0)}%売れています。予想販売高より今年の実績（1日 ${yen(a)}）を目安にしてください。`);
    note(s, `雨の日：荒利 ${rtxt(100 + ST.wet.gp * 100)}・廃棄 ${rtxt(100 + ST.wet.wy * 100)}（雨でない日＝100%）\n\n荒利益高（前年${MO}月）\n土曜：平日の${(ST['土'].idx * 100).toFixed(0)}%\n日曜・祝日：平日の${(ST['日祝'].idx * 100).toFixed(0)}%\n\n予想販売高は前年${MO}月の曜日の傾向と、今年の前年比から試算。天気は前日の予報で見直します。` + (warn.length ? '\n\n' + warn.join('\n') : ''), 11.0, 1.1, 1.83, 5.75, warn.length ? 9 : 10);
  }
  return pres;
}

(async () => {
  const fs = require('fs'); fs.mkdirSync(OUT, { recursive: true });
  const list = process.argv.slice(4).length ? process.argv.slice(4) : ['ALL', ...STORES];
  for (const sc of list) {
    const pres = build(sc), name = `${sc === 'ALL' ? '全店' : sc}FF・厨房レポート${N}日時点`;
    const f = await pres.writeFile({ fileName: path.join(OUT, name + '.pptx') });
    await applyTheme(f, THEME); console.log('written', f);
  }
})();
