"""SALES（売上・荒利益）タブの計算を確かめる。python3 tests/test_sales.py で実行（node が必要）。

画面の salesCalc（前年比・月末着地予測）、fcBacktest（誤差の目安）、fcDaytype（参考予測）、catContrib（カテゴリーの寄与）を
template.html からそのまま取り出して動かし、
1. 手で計算できる小さなデータ（欠損日・一部店舗だけの日・未来日・前年ゼロ）
2. 手元に data/ があれば、本物のCSVから別の方法で計算した値
と照合する。
"""
import csv, glob, json, os, re, subprocess, sys, tempfile, collections, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, 'scripts', 'template.html'), encoding='utf-8').read()


def grab(name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', SRC, re.S)
    assert m, name
    return m.group(0)


def js(calls):
    """calls: [(関数名, 引数リスト)] → 結果リスト"""
    code = ''.join(grab(n) for n in ['salesCalc', 'fcBacktest', 'fcDaytype', 'catContrib'])
    f = os.path.join(tempfile.mkdtemp(), 'in.json'); json.dump(calls, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    prog = code + "const C=JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'));const F={salesCalc,fcBacktest,fcDaytype,catContrib};" \
           "console.log(JSON.stringify(C.map(([n,a])=>F[n](...a))));"
    return json.loads(subprocess.run(['node', '-e', prog, f], capture_output=True, text=True, check=True).stdout)


def scope(d26, d25, cov26=None, cov25=None, nst=1, cat=None):
    return {'daily26': {'販売高': d26}, 'daily25': {'販売高': d25}, 'cov26': cov26 or [nst if v is not None else 0 for v in d26],
            'cov25': cov25 or [nst if v is not None else 0 for v in d25], 'nst': nst, 'cat': cat or {}}


def test_yoy_uses_only_matched_days():
    d25 = [100.0] * 31; d26 = [110.0, None, 130.0, 0.0, 120.0]          # 10/2 欠損、10/4 は実績ゼロ
    r = js([('salesCalc', [scope(d26, d25), '販売高', 1, 5, 5])])[0]
    assert r['used'] == [1, 3, 4, 5] and r['skip'] == [2]
    assert r['s26'] == 360 and r['s25'] == 400 and abs(r['yoy'] + 10) < 1e-9   # 欠損日は分子にも分母にも入れない、ゼロは入れる
    assert r['act'] == 360 and r['missAct'] == 1


def test_partial_store_day_is_excluded():
    d25 = [500.0] * 31; d26 = [520.0, 300.0, 510.0]
    r = js([('salesCalc', [scope(d26, d25, cov26=[5, 3, 5], nst=5), '販売高', 1, 3, 3])])[0]
    assert r['used'] == [1, 3] and abs(r['r'] - 1030 / 1000) < 1e-12


def test_future_days_not_in_yoy_and_forecast_formula():
    d25 = [float(100 + d) for d in range(1, 32)]; d26 = [float(120 + d) for d in range(1, 11)]
    r = js([('salesCalc', [scope(d26, d25), '販売高', 1, 31, 10])])[0]
    assert r['used'] == list(range(1, 11))                                 # 11日以降（未来日）は前年比に入らない
    s26 = sum(d26); s25 = sum(d25[:10]); base = sum(d25[10:])
    assert abs(r['r'] - s26 / s25) < 1e-12 and abs(r['base25'] - base) < 1e-9
    assert abs(r['fc'] - (s26 + base * s26 / s25)) < 1e-6                  # 着地＝実績＋残りの前年×前年比
    assert len(r['rest']) == 21 and r['restNg'] == 0


def test_missing_last_year_day_not_forecast():
    d25 = [100.0] * 31; d25[20] = None; d26 = [100.0] * 10
    r = js([('salesCalc', [scope(d26, d25), '販売高', 1, 10, 10])])[0]
    assert r['restNg'] == 1 and abs(r['restFc'] - 2000) < 1e-9


def test_zero_last_year_gives_no_ratio():
    r = js([('salesCalc', [scope([5.0, 5.0], [0.0] * 31), '販売高', 1, 2, 2])])[0]
    assert r['r'] is None and r['yoy'] is None and r['fc'] is None


def test_week_period_ratio():
    d25 = [100.0] * 31; d26 = [100.0] * 7 + [150.0] * 7
    r = js([('salesCalc', [scope(d26, d25), '販売高', 8, 14, 14])])[0]
    assert abs(r['r'] - 1.5) < 1e-12 and abs(r['fc'] - (sum(d26) + 17 * 100 * 1.5)) < 1e-9


def test_backtest_and_daytype_by_hand():
    d25 = [100.0] * 31; d26 = [110.0] * 10
    bt, dt = js([('fcBacktest', [scope(d26, d25), '販売高', 10, None]), ('fcDaytype', [scope(d26, d25), '販売高', 10])])
    assert bt['n'] == 1 and abs(bt['mae']) < 1e-9                          # 一定の伸びなら誤差0（k=7 の1回）
    assert abs(dt - 110 * 31) < 1e-9


def test_category_contribution_adds_up():
    cat = {'p25': {'A': {'販売高': 300.0}, 'B': {'販売高': 700.0}, 'C': {'販売高': 0.0}},
           'p26': {'A': {'販売高': 360.0}, 'B': {'販売高': 650.0}, 'C': {'販売高': 40.0}}}
    X = js([('catContrib', [{'cat': cat}, '販売高', ['A', 'B', 'C']])])[0]
    assert X['t25'] == 1000 and X['t26'] == 1050 and abs(X['yoy'] - 5) < 1e-9
    assert abs(sum(r['contrib'] for r in X['rows']) - X['yoy']) < 1e-9   # 寄与度の合計＝全体の前年比
    assert abs(sum(r['sh26'] for r in X['rows']) - 100) < 1e-9
    c = next(r for r in X['rows'] if r['c'] == 'C'); assert c['yoy'] is None and abs(c['contrib'] - 4) < 1e-9   # 前年0は前年比を出さない


def test_real_data():
    data = os.path.join(ROOT, 'data')
    if not glob.glob(os.path.join(data, 'FF', '*.csv')):
        print('SKIP  本物のCSVがありません'); return
    out = os.path.join(tempfile.mkdtemp(), 'p.html'); env = dict(os.environ, OUT_FILE=out); env.pop('REPORT_PASSWORD', None)
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'build.py')], env=env, check=True, capture_output=True)
    D = json.loads(re.search(r'let ALLD=(\{.*?\});\n', open(out, encoding='utf-8').read()).group(1)); N = D['meta']['N']
    SN = {'新御堂筋上新田': '上新田', '吹田朝日町': '朝日町', '豊中服部元町一丁目': '元町一', '吹田豊津中学校前': '豊津中', '吹田青山台三丁目': '青山台'}
    CM = {'販売）からあげクン他　ホット': 'からあげクン', 'ホットＦＦ': 'ホットFF', '常温ＦＦ': '常温FF', '販売）サーマル　常温': 'サーマル常温', '中華まん　什器販売': '中華まん'}
    M = ['販売数', '販売高', '廃棄数', '廃棄高', '荒利益高']; num = lambda v: 0.0 if v in ('*', '') else float(v.replace(',', ''))
    n = 0
    for dept in ['FF', '厨房']:
        day = collections.defaultdict(float); cat = collections.defaultdict(float); seen = set()
        for f in glob.glob(os.path.join(data, dept, '*.csv')):
            for r in csv.DictReader(open(f, encoding='cp932')):
                c = CM.get(r['CLASS名']) if dept == 'FF' else (r['SUBCLASS名'] if r['SUBCLASS名'] in ('弁当', '調理パン', '惣菜') else None)
                k = tuple(r[x] for x in ['年月日', '店舗名', 'SUBCLASS名', '商品名'] + M)
                if not c or k in seen or all(num(r[x]) == 0 for x in M): continue
                seen.add(k); y, _, d = map(int, r['年月日'].split('/'))
                for met in ['販売高', '荒利益高']:
                    v = num(r[met])
                    for sc in ['ALL', SN[r['店舗名']]]:
                        day[(sc, met, y, d)] += v
                        if d <= N: cat[(sc, met, y, c)] += v
        calls = []; keys = []
        for sc in ['ALL'] + list(SN.values()):
            for met in ['販売高', '荒利益高']:
                calls += [('salesCalc', [D[dept][sc], met, 1, N, N]), ('catContrib', [D[dept][sc], met, D[dept]['cats']]), ('fcBacktest', [D[dept][sc], met, N, None])]
                keys.append((sc, met))
        res = js(calls)
        for i, (sc, met) in enumerate(keys):
            r, X, bt = res[3 * i], res[3 * i + 1], res[3 * i + 2]
            s26 = sum(day[(sc, met, 2026, d)] for d in range(1, N + 1)); s25 = sum(day[(sc, met, 2025, d)] for d in range(1, N + 1))
            rest = sum(day[(sc, met, 2025, d)] for d in range(N + 1, 32))
            assert abs(r['s26'] - s26) < 0.5 and abs(r['s25'] - s25) < 0.5, (dept, sc, met)
            assert abs(r['fc'] - (s26 + rest * s26 / s25)) < 0.5, (dept, sc, met)
            assert abs(r['s26'] - D[dept][sc]['kpi']['p26'][met]) < 0.5          # 日別の合計＝KPIの合計
            assert abs(X['t26'] - s26) < 0.5 and abs(X['t25'] - s25) < 0.5      # カテゴリーの合計＝全体
            for row in X['rows']:
                assert abs(row['b'] - cat[(sc, met, 2026, row['c'])]) < 0.5 and abs(row['a'] - cat[(sc, met, 2025, row['c'])]) < 0.5
            # 誤差の目安を Python でも計算し直す
            errs = []
            for k in range(7, N - 2):
                rr = sum(day[(sc, met, 2026, d)] for d in range(1, k + 1)) / sum(day[(sc, met, 2025, d)] for d in range(1, k + 1))
                p = sum(day[(sc, met, 2025, d)] * rr for d in range(k + 1, N + 1)); q = sum(day[(sc, met, 2026, d)] for d in range(k + 1, N + 1))
                errs.append(abs(p - q) / q * 100)
            assert abs(bt['mae'] - sum(errs) / len(errs)) < 1e-6 and bt['n'] == len(errs)
            n += 1
    print(f'      本物のCSVで {n} 通り（部門×店舗×指標）を照合')


if __name__ == '__main__':
    k = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); k += 1; print('OK  ', name)
    print(f'{k} tests passed')
