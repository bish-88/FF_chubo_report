"""本物のCSV（data/）とダッシュボードの数字を照合する。data/ がなければスキップ。

python3 tests/check_real.py
集計し直したデータ（暗号化なし）を一時ファイルに作り、元のCSVから別の方法で計算した値と比べる。
"""
import csv, glob, json, os, re, subprocess, sys, tempfile, collections, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get('DATA_DIR', os.path.join(ROOT, 'data'))
if not glob.glob(os.path.join(DATA, 'FF', '*.csv')):
    print('SKIP: data/ にCSVがありません'); sys.exit(0)
out = os.path.join(tempfile.mkdtemp(), 'plain.html')
env = dict(os.environ, OUT_FILE=out); env.pop('REPORT_PASSWORD', None)
subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'build.py')], env=env, check=True, capture_output=True)
D = json.loads(re.search(r'let ALLD=(\{.*?\});\n', open(out, encoding='utf-8').read()).group(1))

SN = {'新御堂筋上新田': '上新田', '吹田朝日町': '朝日町', '豊中服部元町一丁目': '元町一', '吹田豊津中学校前': '豊津中', '吹田青山台三丁目': '青山台'}
ST = list(SN.values())
CM = {'販売）からあげクン他　ホット': 'からあげクン', 'ホットＦＦ': 'ホットFF', '常温ＦＦ': '常温FF', '販売）サーマル　常温': 'サーマル常温', '中華まん　什器販売': '中華まん'}
M = ['販売数', '販売高', '廃棄数', '廃棄高', '荒利益高']
num = lambda v: 0.0 if v in ('*', '') else float(v.replace(',', ''))
clean = lambda n: ' '.join(n.replace('●', '').replace('　', ' ').split())
off26 = lambda d: datetime.date(2026, 10, d).weekday() >= 5 or d == 12
res = collections.Counter(); bad = []

def cmp(lbl, a, b, tol=0.5):
    if b is None and abs(a) < tol: res['ok'] += 1; return
    if b is not None and abs(a - b) < tol: res['ok'] += 1
    else: res['NG'] += 1; bad.append((lbl, a, b))

for dp in ['FF', '厨房']:
    seen, R = set(), []
    for f in glob.glob(os.path.join(DATA, dp, '*.csv')):
        for r in csv.DictReader(open(f, encoding='cp932')):
            c = CM.get(r['CLASS名']) if dp == 'FF' else (r['SUBCLASS名'] if r['SUBCLASS名'] in ('弁当', '調理パン', '惣菜') else None)
            if not c: continue
            key = tuple(r[k] for k in ['年月日', '店舗名', 'SUBCLASS名', '商品名'] + M)
            if key in seen: continue
            seen.add(key); y, _, d = map(int, r['年月日'].split('/'))
            R.append(dict(y=y, d=d, s=SN[r['店舗名']], c=c, n=clean(r['商品名']), **{k: num(r[k]) for k in M}))
    for p in D['meta']['periods']:
        X = D[dp] if p['k'] == 'all' else D['P'][p['k']][dp]
        for sc in ['ALL'] + ST:
            rr = [r for r in R if (sc == 'ALL' or r['s'] == sc) and p['d0'] <= r['d'] <= p['d1']]
            for y, key in [(2026, 'p26'), (2025, 'p25')]:
                for k in M:
                    a = sum(r[k] for r in rr if r['y'] == y); cmp(f'KPI {dp}{p["k"]}{sc}{key}{k}', a, X[sc]['kpi'][key][k])
                    if sc != 'ALL': cmp(f'店舗 {dp}{p["k"]}{sc}{key}{k}', a, X['stores'][sc][key][k])
                    for c in X['cats']: cmp(f'カテゴリー {dp}{p["k"]}{sc}{c}{key}{k}', sum(r[k] for r in rr if r['y'] == y and r['c'] == c), X[sc]['cat'][key][c][k])
            for pr in X[sc]['prod']:
                z = [r for r in rr if r['y'] == 2026 and r['n'] == pr['name']]
                for k, kk in [('販売数', 'sold'), ('販売高', 'amt'), ('廃棄数', 'w'), ('荒利益高', 'gp')]: cmp(f'単品 {dp}{p["k"]}{sc}{pr["name"]}{k}', sum(r[k] for r in z), pr[kk])
    for sc in ['ALL'] + ST:
        rr = [r for r in R if sc == 'ALL' or r['s'] == sc]; ns = 5 if sc == 'ALL' else 1
        for y, key in [(2026, 'daily26'), (2025, 'daily25')]:
            for k, arr in D[dp][sc][key].items():
                for i, v in enumerate(arr): cmp(f'日別 {dp}{sc}{y}/{i+1}{k}', sum(r[k] for r in rr if r['y'] == y and r['d'] == i + 1), v)
        for w in D[dp][sc]['wk']['weeks']:
            for part, sel in [('all', lambda d: True), ('wk', lambda d: not off26(d)), ('we', off26)]:
                ds = [d for d in range(w['start'], w['end'] + 1) if sel(d)]
                if not ds: continue
                for k in M: cmp(f'PSA/D {dp}{sc}{w["label"]}{part}{k}', sum(r[k] for r in rr if r['y'] == 2026 and r['d'] in ds) / len(ds) / ns, w[part]['tot'][k], 0.01)
    for p in ['p26', 'p25', 'm25']:
        for k in M: cmp(f'5店合計=全店 {dp}{p}{k}', sum(D[dp][s]['kpi'][p][k] for s in ST), D[dp]['ALL']['kpi'][p][k])
print(f"OK {res['ok']}  NG {res['NG']}")
for b in bad[:20]: print('NG', b)
sys.exit(1 if res['NG'] else 0)
