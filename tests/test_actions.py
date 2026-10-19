"""実施管理（共有版の読み込み・日別データ・実施前後の比較）を確かめる。

python3 tests/test_actions.py で実行（node が必要）。
- 共有版 data/actions.json：形式の違う行は捨て、状況の値を正規化する
- 実施前後の比較（画面の actEval）：テスト用データで、手で計算した平均と一致するか
- 欠損日（データなし）は平均に入れない／データ不足・範囲外は数字を出さない
- 手元に data/ があれば、本物のCSVから計算し直した値とも照合する
"""
import csv, glob, json, os, re, subprocess, sys, tempfile, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
from test_build import make_fixture, build, load, M, SHORT

SRC = open(os.path.join(ROOT, 'scripts', 'template.html'), encoding='utf-8').read()


def js_eval(records, daily, N):
    """template.html の dKey と actEval をそのまま取り出して node で動かす。"""
    grab = lambda pat: re.search(pat, SRC, re.S).group(0)
    code = grab(r"const dKey=r=>[^\n]*\n") + grab(r"function actEval\(r,daily,N\)\{.*?\n\}\n")
    tmp = tempfile.mkdtemp(); f = os.path.join(tmp, 'in.json')
    json.dump({'records': records, 'daily': daily, 'N': N}, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    js = code + "const I=JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'));" \
         "console.log(JSON.stringify(I.records.map(r=>actEval(r,I.daily,I.N))));"
    out = subprocess.run(['node', '-e', js, f], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


_c = {}
def fixture():
    if not _c:
        tmp = tempfile.mkdtemp(); ff, ki = make_fixture(tmp)
        items = [
            dict(id='A1', dept='FF', store='上新田', cat='ホットFF', name='ＨＯＴ テストチキン', type='廃棄削減', rec='毎日1個少なく作る',
                 status='実施中', done_date='2026-10-05', updated_at='2026-10-05T00:00:00Z'),
            dict(id='A2', dept='厨房', store='朝日町', cat='弁当', name='弁当（カテゴリー計）', type='急変', rec='確認', status='ふめい'),
            dict(id='', dept='FF', store='上新田', name='x'),          # id なし → 捨てる
            dict(id='A9', dept='ほか', store='上新田', name='x'),      # 部門が違う → 捨てる
            'ゴミ',
        ]
        json.dump({'items': items}, open(os.path.join(tmp, 'actions.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        _c.update(D=load(build(tmp, os.path.join(tmp, 'o.html'))), ff=ff, ki=ki)
    return _c


def test_shared_actions_are_validated():
    sh = fixture()['D']['actions_shared']
    assert [r['id'] for r in sh['items']] == ['A1', 'A2']
    assert sh['items'][1]['status'] == '未着手'          # 知らない状況は「未着手」に
    assert set(sh['items'][0]) >= {'owner', 'plan_date', 'result_note'}   # 欠けた項目は空で持つ


def test_no_shared_file_means_none():
    tmp = tempfile.mkdtemp(); make_fixture(tmp)
    assert load(build(tmp, os.path.join(tmp, 'o.html')))['actions_shared'] is None


def test_daily_series_for_shared_action():
    c = fixture(); D = c['D']
    s = D['daily']['FF']['上新田|ＨＯＴ テストチキン']
    days = [r[0] for r in s]
    assert 3 not in days and days == sorted(days)       # 10/3 は欠損（データなし）
    want = collections.defaultdict(float)
    for r in c['ff']:
        if r['年月日'] == '2026/10/2' and r['店舗名'] == '新御堂筋上新田' and r['商品名'] == 'ＨＯＴ テストチキン':
            want['q'] += float(r['販売数']); want['w'] += 0 if r['廃棄数'] == '*' else float(r['廃棄数'])
    row = next(r for r in s if r[0] == 2)
    assert (row[1], row[2]) == (want['q'], want['w'])
    assert '朝日町|cat:弁当' in D['daily']['厨房']        # カテゴリー計の記録はカテゴリーの日別


def test_act_eval_matches_hand_calc():
    D = fixture()['D']; N = D['meta']['N']; s = D['daily']['FF']['上新田|ＨＯＴ テストチキン']
    rec = dict(store='上新田', cat='ホットFF', name='ＨＯＴ テストチキン', dept='FF')
    r = js_eval([dict(rec, done_date='2026-10-05')], D['daily']['FF'], N)[0]
    # 実施日 10/5 → 前は 10/1〜10/4（4日。10/3 欠損で記録3日）、後は 10/5〜10/8（4日）
    assert (r['len'], r['b']['n'], r['a']['n']) == (4, 3, 4)
    avg = lambda ds, k: sum(x[k] for x in s if x[0] in ds) / len([x for x in s if x[0] in ds])
    assert abs(r['b']['q'] - avg({1, 2, 4}, 1)) < 1e-9 and abs(r['a']['w'] - avg({5, 6, 7, 8}, 2)) < 1e-9
    assert abs(r['a']['gp'] - avg({5, 6, 7, 8}, 4)) < 1e-9


def test_act_eval_edge_cases():
    D = fixture()['D']; N = D['meta']['N']; base = dict(store='上新田', cat='ホットFF', name='ＨＯＴ テストチキン', dept='FF')
    out = js_eval([dict(base), dict(base, done_date='2026-11-02'), dict(base, done_date=f'2026-10-{N+1:02d}'),
                   dict(base, done_date='2026-10-01'), dict(base, done_date='2026-10-05', name='ない商品')], D['daily']['FF'], N)
    assert '実施日を入れる' in out[0]['msg']
    assert '範囲外' in out[1]['msg']
    assert 'まだありません' in out[2]['msg']
    assert '実施前のデータがありません' in out[3]['msg']
    assert '日別データがありません' in out[4]['msg']
    # 実施後が2日しかない → 計算はするが、画面は「データ不足」（各3日未満）にする
    r = js_eval([dict(base, done_date=f'2026-10-{N-1:02d}')], D['daily']['FF'], N)[0]
    assert r['len'] == 2 and r['a']['n'] == 2


def test_real_data_eval():
    data = os.path.join(ROOT, 'data')
    if not glob.glob(os.path.join(data, 'FF', '*.csv')):
        print('SKIP  本物のCSVがありません'); return
    out = os.path.join(tempfile.mkdtemp(), 'p.html'); env = dict(os.environ, OUT_FILE=out); env.pop('REPORT_PASSWORD', None)
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'build.py')], env=env, check=True, capture_output=True)
    D = load(open(out, encoding='utf-8').read()); N = D['meta']['N']
    SN = {v: k for k, v in SHORT.items()}
    cl = lambda n: ' '.join(n.replace('●', '').replace('　', ' ').split())
    num = lambda v: 0.0 if v in ('*', '') else float(v.replace(',', ''))
    CM = {'販売）からあげクン他　ホット': 1, 'ホットＦＦ': 1, '常温ＦＦ': 1, '販売）サーマル　常温': 1, '中華まん　什器販売': 1}
    n = 0
    for dept in ['FF', '厨房']:
        recs = [dict(store=c['store'], cat=c['cat'], name=c['name'], dept=dept, done_date='2026-10-12')
                for c in D['cand']['all'][dept] if c['type'] in ('廃棄削減', '増産')][:25]
        res = js_eval(recs, D['daily'][dept], N)
        day = collections.defaultdict(lambda: collections.defaultdict(float)); seen = set()
        for f in glob.glob(os.path.join(data, dept, '*2026*.csv')):
            for r in csv.DictReader(open(f, encoding='cp932')):
                ok = r['CLASS名'] in CM if dept == 'FF' else r['SUBCLASS名'] in ('弁当', '調理パン', '惣菜')
                k = tuple(r[c] for c in ['年月日', '店舗名', 'SUBCLASS名', '商品名'] + M)
                if not ok or k in seen or all(num(r[c]) == 0 for c in M): continue
                seen.add(k); d = int(r['年月日'].split('/')[2])
                day[(r['店舗名'], cl(r['商品名']), d)]['q'] += num(r['販売数']); day[(r['店舗名'], cl(r['商品名']), d)]['gp'] += num(r['荒利益高'])
        for rec, e in zip(recs, res):
            L = e['len']; aft = range(12, 12 + L); bef = range(12 - L, 12)
            for ds, side in [(aft, 'a'), (bef, 'b')]:
                v = [day[(SN[rec['store']], rec['name'], d)] for d in ds if (SN[rec['store']], rec['name'], d) in day]
                assert e[side]['n'] == len(v), (rec['name'], side)
                if v:
                    assert abs(e[side]['q'] - sum(x['q'] for x in v) / len(v)) < 1e-6
                    assert abs(e[side]['gp'] - sum(x['gp'] for x in v) / len(v)) < 1e-6
            n += 1
    print(f'      本物のCSVで {n} 件の実施前後比較を照合')


def test_merge_actions_script():
    sys.path.insert(0, os.path.join(ROOT, 'scripts')); import merge_actions as MA
    tmp = tempfile.mkdtemp(); w = lambda n, items: (json.dump({'items': items}, open(os.path.join(tmp, n), 'w', encoding='utf-8')), os.path.join(tmp, n))[1]
    base = [dict(id='A1', dept='FF', status='未着手', owner='', updated_at='2026-10-10T00:00:00Z')]
    a = w('a.json', [dict(id='A1', dept='FF', status='実施中', owner='店長', updated_at='2026-10-12T00:00:00Z'),
                     dict(id='A2', dept='厨房', status='?', updated_at='2026-10-12T00:00:00Z'), dict(id='', dept='FF')])
    b = w('b.json', [dict(id='A1', dept='FF', status='完了', owner='副店長', updated_at='2026-10-13T00:00:00Z', _src='changed')])
    items, conflicts, bad = MA.merge(base, [a, b])
    d = {r['id']: r for r in items}
    assert d['A1']['status'] == '完了' and '_src' not in d['A1']     # 新しい方が残る
    assert d['A2']['status'] == '未着手' and bad == 1
    assert len(conflicts) == 1 and conflicts[0][0] == 'A1'          # 2人が同じ記録を直した


if __name__ == '__main__':
    k = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); k += 1; print('OK  ', name)
    print(f'{k} tests passed')
