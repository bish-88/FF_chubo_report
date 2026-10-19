"""改善候補（scripts/candidates.py）の計算式を、答えが手で計算できる小さなデータで確かめる。

python3 tests/test_candidates.py で実行（pytest でも動く）。
最後に、手元に data/ があれば、本物のCSVから別の方法で計算し直して全候補の実績値と試算を照合する。
"""
import csv, datetime, glob, math, os, sys, collections
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import candidates as C

M = C.M
off = lambda d: datetime.date(2026, 10, d).weekday() >= 5
clean = lambda n: n


def frame(rows):
    """rows: (year, d, store, cat, name, 販売数, 廃棄数, 売価, 原価, 定価)"""
    out = []
    for y, d, st, cat, name, q, w, price, cost, list_price in rows:
        out.append(dict(year=y, d=d, store=st, cat=cat, 商品名=name, 販売数=q, 販売高=q * price, 廃棄数=w,
                        廃棄高=w * list_price, 荒利益高=q * price - (q + w) * cost))
    return pd.DataFrame(out)


def test_unit_cost_identity():
    # 荒利益高＝販売高−(販売数＋廃棄数)×原価 なら、原価/個 が正確に戻る
    s = {'販売数': 30, '販売高': 30 * 250, '廃棄数': 6, '廃棄高': 6 * 270, '荒利益高': 30 * 250 - 36 * 120}
    cost, price, wunit = C.unit_values(s)
    assert abs(cost - 120) < 1e-9 and abs(price - 250) < 1e-9 and abs(wunit - 270) < 1e-9
    # 販売0・廃棄0 は計算しない（0除算しない）
    assert C.unit_values({'販売数': 0, '販売高': 0, '廃棄数': 0, '廃棄高': 0, '荒利益高': 0}) == (None, None, None)


def test_cut_per_day_boundaries():
    assert C.cut_per_day(0.29) == 0 and C.cut_per_day(0.3) == 0.5 and C.cut_per_day(0.74) == 0.5
    assert C.cut_per_day(0.75) == 1 and C.cut_per_day(1.24) == 1 and C.cut_per_day(1.25) == 1
    assert C.cut_per_day(2.5) == 2 and C.cut_per_day(5) == 4


def test_sim_reduce_by_hand():
    # 廃棄 [2,0,1,3]、毎日1個減らす、原価100・売価250
    # 日1: 1×100 − 0 = 100 / 日2: 100 − 1×250 = −150 / 日3: 100 / 日4: 100 → 合計 150、失う販売 1個、減る廃棄 3個
    gp, lost, wcut = C.sim_reduce([2, 0, 1, 3], 1, 100, 250)
    assert (gp, lost, wcut) == (150, 1, 3)
    # 2個減らす：日1 200 / 日2 200−500=−300 / 日3 200−250=−50 / 日4 200 → 50、失う 2+1=3、減る廃棄 2+0+1+2=5
    assert C.sim_reduce([2, 0, 1, 3], 2, 100, 250) == (50, 3, 5)
    # 2日に1回1個：1個減らす計算の半分
    assert C.sim_reduce([2, 0, 1, 3], 0.5, 100, 250) == (75, 0.5, 1.5)


def _reduce_fixture(waste, q=10, price=250, cost=100, lp=270):
    return frame([(2026, d + 1, '朝日町', 'ホットFF', 'テストチキン', q, w, price, cost, lp) for d, w in enumerate(waste)])


def test_reduce_candidate_matches_formula():
    waste = [2, 2, 0, 2, 1, 2, 2, 3, 2, 2]          # 10日・平均1.8個 → r=1
    df = _reduce_fixture(waste)
    L = [c for c in C.build(df, 'FF', True, 1, 10, [], off, clean) if c['type'] == '廃棄削減']
    assert len(L) == 1; c = L[0]
    gp, lost, wcut = C.sim_reduce(waste, 1, 100, 250)
    est = dict((l, v) for l, v, u in c['est'])
    assert abs(est['荒利益高の変化'] - gp * 7 / 10) < 1e-6
    assert abs(est['廃棄高の変化（定価ベース）'] + wcut * 270 * 7 / 10) < 1e-6
    assert abs(est['販売数の変化'] + lost * 7 / 10) < 1e-6
    assert c['n_days'] == 10 and c['n_rows'] == 10 and c['conf'] == '高' and not c['neg']
    # 実績値と仮定値は別々に持っている
    assert any('原価/個' in a[0] for a in c['actual']) and all(isinstance(a, str) for a in c['assume'])


def test_reduce_that_lowers_gp_is_flagged():
    # 廃棄はあるが廃棄ゼロの日が多く、売価が高い → 減らすと荒利益高が下がる
    waste = [0, 0, 0, 4, 0, 0, 4, 0, 0, 4]
    df = _reduce_fixture(waste, q=5, price=500, cost=100, lp=520)
    c = [c for c in C.build(df, 'FF', True, 1, 10, [], off, clean) if c['type'] == '廃棄削減'][0]
    assert c['neg'] and '減らさない' in c['action'] and c['score'] == 0


def test_increase_candidate_formula():
    df = frame([(2026, d, '上新田', '弁当', 'テスト弁当', 5, 0, 500, 350, 700) for d in range(1, 11)])
    c = [c for c in C.build(df, '厨房', False, 1, 10, [], off, clean) if c['type'] == '増産'][0]
    est = dict((l, v) for l, v, u in c['est'])
    assert abs(est['荒利益高の変化（追加分が全部売れた場合）'] - 10 * 150 * 7 / 10) < 1e-6
    assert abs(est['荒利益高の変化（全部売れ残った場合）'] + 10 * 350 * 7 / 10) < 1e-6
    assert abs(est['損益分岐の販売率'] - 70) < 1e-6
    assert c['conf'] == '中'   # 売り切れ時刻が分からないので最高でも「中」


def test_thin_data_is_not_judged():
    # 記録2日だけ → 廃棄削減・増産とも出さない
    df = frame([(2026, d, '元町一', 'ホットFF', 'レア', 6, 3, 200, 90, 220) for d in (2, 9)])
    assert [c for c in C.build(df, 'FF', True, 1, 10, [], off, clean) if c['type'] != '急変'] == []


def test_week_change_detection():
    rows = []
    for d in range(5, 19):
        q = 20 if d <= 11 else 8           # 今週（12〜18）に大きく落ちた
        rows.append((2026, d, '豊津中', 'ホットFF', 'A', q + (d % 2), 0, 300, 120, 320))
    df = frame(rows)
    L = [c for c in C.build(df, 'FF', True, 1, 18, [(5, 11), (12, 18)], off, clean) if c['type'] == '急変' and c['sub'] == '先週比']
    sales = [c for c in L if c['metric'].startswith('販売高') and c['name'].endswith('（カテゴリー計）')]
    assert sales and sales[0]['dir'] == '減' and sales[0]['worse']
    # 小さな揺れは出さない
    rows = [(2026, d, '豊津中', 'ホットFF', 'A', 20 + (d % 3), 0, 300, 120, 320) for d in range(5, 19)]
    assert [c for c in C.build(frame(rows), 'FF', True, 1, 18, [(5, 11), (12, 18)], off, clean) if c['type'] == '急変'] == []


def test_sku_missing_days_are_not_zero():
    # 単品の記録がない日は「売れなかった」ではなく欠損として扱う（0で埋めない）
    rows = [(2026, d, '青山台', '惣菜', 'B', 10, 0, 300, 150, 320) for d in list(range(5, 12)) + [12, 13, 14]]
    L = [c for c in C.build(frame(rows), '厨房', False, 1, 18, [(5, 11), (12, 18)], off, clean) if c['type'] == '急変' and c['name'] == 'B']
    assert L == []


def test_reclass_lowers_confidence():
    rows = []
    for y in (2025, 2026):
        for d in range(1, 11):
            rows.append((y, d, '元町一', '常温FF', 'X', 5 if y == 2025 else 40 + d % 3, 0, 150, 70, 160))
    L = C.build(frame(rows), 'FF', True, 1, 10, [], off, clean, reclass={'常温FF': '分類変更'})
    yoy = [c for c in L if c['type'] == '急変' and c['sub'] == '前年比']
    assert yoy and all(c['conf'] == '低' and '分類変更' in c['conf_why'] for c in yoy)


def test_real_data_reproduces():
    """本物のCSVから、candidates.py を使わずに計算し直して、全候補の実績値・試算と照合する。"""
    data = os.path.join(ROOT, 'data')
    if not glob.glob(os.path.join(data, 'FF', '*.csv')):
        print('SKIP  本物のCSVがありません'); return
    import json, re, subprocess, tempfile
    out = os.path.join(tempfile.mkdtemp(), 'p.html'); env = dict(os.environ, OUT_FILE=out); env.pop('REPORT_PASSWORD', None)
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'build.py')], env=env, check=True, capture_output=True)
    D = json.loads(re.search(r'let ALLD=(\{.*?\});\n', open(out, encoding='utf-8').read()).group(1))
    SN = {'新御堂筋上新田': '上新田', '吹田朝日町': '朝日町', '豊中服部元町一丁目': '元町一', '吹田豊津中学校前': '豊津中', '吹田青山台三丁目': '青山台'}
    CM = {'販売）からあげクン他　ホット': 'からあげクン', 'ホットＦＦ': 'ホットFF', '常温ＦＦ': '常温FF', '販売）サーマル　常温': 'サーマル常温', '中華まん　什器販売': '中華まん'}
    num = lambda v: 0.0 if v in ('*', '') else float(v.replace(',', ''))
    cl = lambda n: ' '.join(n.replace('●', '').replace('　', ' ').split())
    checked = 0
    for dept in ['FF', '厨房']:
        seen = set(); day = collections.defaultdict(lambda: collections.defaultdict(float))
        for f in glob.glob(os.path.join(data, dept, '*.csv')):
            for r in csv.DictReader(open(f, encoding='cp932')):
                cat = CM.get(r['CLASS名']) if dept == 'FF' else (r['SUBCLASS名'] if r['SUBCLASS名'] in ('弁当', '調理パン', '惣菜') else None)
                if not cat: continue
                k = tuple(r[c] for c in ['年月日', '店舗名', 'SUBCLASS名', '商品名'] + M)
                if k in seen or all(num(r[c]) == 0 for c in M): continue
                seen.add(k); y, _, d = map(int, r['年月日'].split('/'))
                if y != 2026: continue
                for c in M: day[(SN[r['店舗名']], cl(r['商品名']), d)][c] += num(r[c])
        for pk, per in D['cand'].items():
            for c in per[dept]:
                if c['type'] not in ('廃棄削減', '増産'): continue
                days = sorted(dd for (st, nm, dd), v in day.items() if st == c['store'] and nm == c['name'] and c['d0'] <= dd <= c['d1'] and v['販売数'] + v['廃棄数'] > 0)
                tot = {m: sum(day[(c['store'], c['name'], dd)][m] for dd in days) for m in M}
                act = {a[0]: a[1] for a in c['actual']}
                assert len(days) == c['n_days'] == act['記録のある日数'], (c['name'], len(days), c['n_days'])
                for m in ['販売数', '廃棄数', '販売高', '荒利益高']: assert abs(tot[m] - act[m]) < 0.5, (c['name'], m)
                cost = (tot['販売高'] - tot['荒利益高']) / (tot['販売数'] + tot['廃棄数']); price = tot['販売高'] / tot['販売数']
                est = {e[0]: e[1] for e in c['est']}
                if c['type'] == '廃棄削減':
                    ws = [day[(c['store'], c['name'], dd)]['廃棄数'] for dd in days]
                    r = 0.5 if '2日に1回' in c['assume'][0].split('（')[0] else int(c['assume'][0].split('＝')[1].split('個')[0])
                    gp = 0.0
                    for w in ws:
                        st = 1 if r == 0.5 else r; k = 0.5 if r == 0.5 else 1
                        gp += k * (st * cost - max(0, st - w) * price)
                    assert abs(gp * 7 / len(days) - est['荒利益高の変化']) < 0.01, (c['name'], gp)
                else:
                    z = sum(1 for dd in days if day[(c['store'], c['name'], dd)]['廃棄数'] == 0)
                    up = (z * (price - cost) - (len(days) - z) * cost) * 7 / len(days)
                    assert abs(up - est['荒利益高の変化（追加分が全部売れた場合）']) < 0.01
                checked += 1
    print(f'      本物のCSVで {checked} 件の候補を照合')


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_') and callable(f):
            f(); n += 1; print('OK  ', k)
    print(f'{n} tests passed')
