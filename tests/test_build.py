"""build.py の集計を、答えが分かっている小さなテストデータで確かめる。

python3 tests/test_build.py で実行（pytest でも動く）。
本物のCSVは使わない（data/ がなくても動く）。
"""
import csv, json, os, re, subprocess, sys, tempfile, random, base64, hashlib, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORES = ['新御堂筋上新田', '吹田朝日町', '豊中服部元町一丁目', '吹田豊津中学校前', '吹田青山台三丁目']
SHORT = dict(zip(STORES, ['上新田', '朝日町', '元町一', '豊津中', '青山台']))
COLS = ['年月日', '週開始日', '年月', '営業部名', 'MC名', 'MO名', '店舗名', 'DIV名', 'DEPT名', 'CLASS名', 'SUBCLASS名', '商品名',
        '仕入数PSA/D', '販売数PSA/D', '廃棄数PSA/D', '販売数', '販売高', '廃棄数', '廃棄高', '荒利益高']
M = ['販売数', '販売高', '廃棄数', '廃棄高', '荒利益高']
N26 = 11  # 今年は 10/1〜11（木〜日 と 月〜日 の2週）


def row(y, d, store, cls, sub, name, q, w, price):
    amt = q * price; wy = w * price
    return {'年月日': f'{y}/10/{d}', '週開始日': '', '年月': '', '営業部名': '', 'MC名': '', 'MO名': '', '店舗名': store, 'DIV名': '',
            'DEPT名': '', 'CLASS名': cls, 'SUBCLASS名': sub, '商品名': name, '仕入数PSA/D': '', '販売数PSA/D': '', '廃棄数PSA/D': '',
            '販売数': str(q), '販売高': f'{amt:,}', '廃棄数': '*' if w == 0 else str(w), '廃棄高': '*' if wy == 0 else f'{wy:,}',
            '荒利益高': f'{int(amt * 0.4 - wy):,}'}


def make_fixture(tmp):
    rnd = random.Random(7)
    ff, ki = [], []
    for y, days in [(2025, range(1, 32)), (2026, range(1, N26 + 1))]:
        for d in days:
            for st in STORES:
                if y == 2026 and d == 3 and st == '新御堂筋上新田':
                    continue  # 欠損日（データなし）
                zero = (y == 2026 and d == 4 and st == '吹田朝日町')  # データはあるが売れなかった日
                for cls, name, price in [('ホットＦＦ', 'ＨＯＴ テストチキン', 200), ('常温ＦＦ', '常温 テストコロッケ', 120)]:
                    q = 0 if zero else rnd.randint(5, 25); w = 0 if zero else rnd.randint(0, 3)
                    ff.append(row(y, d, st, cls, 'その他', name, q, w, price))
                for sub, name, price in [('弁当', 'Ｍ テスト弁当', 500), ('調理パン', 'Ｍ テストサンド', 300), ('惣菜', 'Ｍ テスト惣菜', 250)]:
                    q = 0 if zero else rnd.randint(2, 12); w = 0 if zero else rnd.randint(0, 2)
                    ki.append(row(y, d, st, 'まちかど厨房（販売）', sub, name, q, w, price))
    # 2日しか売れていない単品 → 判定保留になるはず
    for d in (2, 9):
        ff.append(row(2026, d, '吹田豊津中学校前', 'ホットＦＦ', 'その他', 'ＨＯＴ レア商品', 6, 0, 150))
    # 完全に同じ行（重複）→ 1回だけ数える
    ff.append(dict(ff[0]))
    for sub, rows in [('FF', ff), ('厨房', ki)]:
        os.makedirs(os.path.join(tmp, sub))
        with open(os.path.join(tmp, sub, 'x.csv'), 'w', encoding='cp932', newline='') as f:
            wr = csv.DictWriter(f, COLS); wr.writeheader(); wr.writerows(rows)
    return ff, ki


def expect(rows, pred):
    seen, t = set(), collections.defaultdict(float)
    for r in rows:
        k = tuple(r[c] for c in ['年月日', '店舗名', 'SUBCLASS名', '商品名'] + M)
        if k in seen: continue
        seen.add(k)
        y, _, d = map(int, r['年月日'].split('/'))
        if pred(y, d, r):
            for c in M: t[c] += 0.0 if r[c] == '*' else float(r[c].replace(',', ''))
    return t


def build(tmp, out, pw=None):
    env = dict(os.environ, DATA_DIR=tmp, OUT_FILE=out)
    env.pop('REPORT_PASSWORD', None)
    if pw: env['REPORT_PASSWORD'] = pw
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'build.py')], env=env, check=True, capture_output=True)
    return open(out, encoding='utf-8').read()


def load(html):
    return json.loads(re.search(r'let ALLD=(\{.*?\});\n', html).group(1))


_cache = {}
def data():
    if 'D' not in _cache:
        tmp = tempfile.mkdtemp(); ff, ki = make_fixture(tmp)
        out = os.path.join(tmp, 'out.html')
        _cache.update(D=load(build(tmp, out)), ff=ff, ki=ki, tmp=tmp)
    return _cache


def test_kpi_totals_match_raw():
    c = data(); D = c['D']
    for dept, rows in [('FF', c['ff']), ('厨房', c['ki'])]:
        for sc in ['ALL'] + list(SHORT.values()):
            inS = (lambda r: True) if sc == 'ALL' else (lambda r, sc=sc: SHORT[r['店舗名']] == sc)
            e26 = expect(rows, lambda y, d, r: y == 2026 and inS(r))
            e25 = expect(rows, lambda y, d, r: y == 2025 and d <= N26 and inS(r))
            for k in M:
                assert abs(D[dept][sc]['kpi']['p26'][k] - e26[k]) < 0.5, (dept, sc, k)
                assert abs(D[dept][sc]['kpi']['p25'][k] - e25[k]) < 0.5, (dept, sc, k)


def test_duplicate_row_counted_once():
    c = data()
    raw = sum(float(r['販売数']) for r in c['ff'] if r['年月日'].startswith('2026'))
    dup = float(c['ff'][0]['販売数']) if c['ff'][0]['年月日'].startswith('2026') else 0
    assert abs(c['D']['FF']['ALL']['kpi']['p26']['販売数'] - (raw - dup)) < 0.5


def test_missing_day_is_none_and_zero_day_is_zero():
    D = data()['D']
    assert D['FF']['上新田']['daily26']['販売高'][2] is None      # 10/3 データなし
    assert D['FF']['ALL']['daily26']['販売高'][2] is not None      # 他店はある
    assert D['FF']['朝日町']['daily26']['販売高'][3] == 0           # 10/4 データあり・売上ゼロ
    assert D['FF']['stores']['上新田']['days26'] == N26 - 1
    assert D['FF']['stores']['朝日町']['days26'] == N26


def test_weeks_and_periods():
    c = data(); D = c['D']
    ks = [p['k'] for p in D['meta']['periods']]
    assert ks == ['all', 'w5', 'w1']
    p5 = next(p for p in D['meta']['periods'] if p['k'] == 'w5')
    assert (p5['d0'], p5['d1'], p5['n'], p5['tag']) == (5, 11, 7, '今週')
    e = expect(c['ff'], lambda y, d, r: y == 2026 and 5 <= d <= 11)
    e25 = expect(c['ff'], lambda y, d, r: y == 2025 and 5 <= d <= 11)
    for k in M:
        assert abs(D['P']['w5']['FF']['ALL']['kpi']['p26'][k] - e[k]) < 0.5
        assert abs(D['P']['w5']['FF']['ALL']['kpi']['p25'][k] - e25[k]) < 0.5
    # 週の1店1日あたり（PSA/D）＝ 週合計 ÷ 5店 ÷ 日数
    w = D['FF']['ALL']['wk']['weeks'][1]
    assert abs(w['all']['tot']['販売高'] - e['販売高'] / 5 / 7) < 0.01


def test_thin_sku_is_hold():
    D = data()['D']
    r = next(p for p in D['FF']['豊津中']['prod'] if 'レア商品' in p['name'])
    assert r['v'] == 'hold'


def test_waste_rate_definition():
    D = data()['D']; o = D['FF']['ALL']['nc']['p26']
    wr = o['廃棄数'] / (o['販売数'] + o['廃棄数'])
    assert 0 < wr < 1


def test_no_nan_in_payload():
    html = build(data()['tmp'], os.path.join(data()['tmp'], 'o2.html'))
    payload = re.search(r'let ALLD=(\{.*?\});\n', html).group(1)
    assert 'NaN' not in payload and 'Infinity' not in payload


def test_encrypted_build_decrypts():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    tmp = data()['tmp']; html = build(tmp, os.path.join(tmp, 'enc.html'), pw='test-pass')
    assert 'let ALLD=null' in html
    e = json.loads(re.search(r'(\{"s": ".*?"it": \d+\})', html).group(1)); b = base64.b64decode
    key = hashlib.pbkdf2_hmac('sha256', b'test-pass', b(e['s']), e['it'], 32)
    dec = json.loads(AESGCM(key).decrypt(b(e['i']), b(e['c']), None))
    assert dec == data()['D']


if __name__ == '__main__':
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            try: fn(); print('OK  ', name)
            except Exception as ex: fails += 1; print('FAIL', name, repr(ex))
    sys.exit(1 if fails else 0)
