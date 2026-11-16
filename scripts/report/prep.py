# レポート用のデータを作る。使い方：
#   OUT_FILE=作業フォルダ/plain.html python3 scripts/build.py      （暗号化なしのページ。GitHubには上げない）
#   python3 scripts/report/prep.py 作業フォルダ/plain.html          → 作業フォルダ/alld.json
#   node scripts/report/deck_store.js 作業フォルダ/alld.json 出力フォルダ [店舗...]
# ダッシュボードのデータ（alld.json）に、
#  1) 月末着地見込み（ダッシュボードの salesCalc をそのまま実行）
#  2) 日別の 販売数・廃棄数（マチカフェ除く。週の平日／土日祝の廃棄率に使う。CSVから集計）
# を足す。足した値はダッシュボードの合計と一致することを確認する。
import sys, json, glob, os
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
import test_sales as T
from test_build import load
P = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), 'alld.json')
D = load(open(sys.argv[1], encoding='utf-8').read()); m = D['meta']; N = m['N']
T.META.update(dict(Y=m['Y'], LY=m['LY'], MO=m['MO'], DIM=m['DIM'], hol26=m['hol26'], hol25=m['hol25'], N=N))
scopes = ['ALL'] + m['stores']
calls = [('salesCalc', [D[dp][sc], met, 1, N, N]) for dp in ['FF', '厨房'] for sc in scopes for met in ['販売高', '荒利益高']]
res = T.js(calls); D['fc'] = {}
i = 0
for dp in ['FF', '厨房']:
    D['fc'][dp] = {}
    for sc in scopes:
        D['fc'][dp][sc] = {}
        for met in ['販売高', '荒利益高']:
            r = res[i]; i += 1; D['fc'][dp][sc][met] = dict(fc=r['fc'], r=r['r'], act=r['act'], base25=r['base25'])
SN = {v: k for k, v in m['sfull'].items()}
CM = {'販売）からあげクン他　ホット', 'ホットＦＦ', '常温ＦＦ', '販売）サーマル　常温', '中華まん　什器販売'}
M = ['販売数', '販売高', '廃棄数', '廃棄高', '荒利益高']
D['ncd'] = {}
for dp in ['FF', '厨房']:
    df = pd.concat([pd.read_csv(f, encoding='cp932', dtype=str) for f in [f for f in glob.glob(os.path.join(ROOT, 'data', dp, '*.csv')) if pd.read_csv(f, encoding='cp932', dtype=str, nrows=1).年月日.iloc[0].startswith(f"{m['Y']}/{m['MO']}/")]]).drop_duplicates()
    for c in M: df[c] = pd.to_numeric(df[c].fillna('0').str.replace(',', '').replace('*', '0'), errors='coerce').fillna(0)
    ok = df.CLASS名.isin(CM) if dp == 'FF' else df.SUBCLASS名.isin(['弁当', '調理パン', '惣菜'])
    df = df[ok & (df[M] != 0).any(axis=1)]
    df['d'] = pd.to_datetime(df.年月日).dt.day; df['s'] = df.店舗名.map(SN)
    D['ncd'][dp] = {}
    for sc in scopes:
        x = df if sc == 'ALL' else df[df.s == sc]
        g = x.groupby('d')[['販売数', '廃棄数']].sum()
        D['ncd'][dp][sc] = {k: [float(g[k].get(d, 0)) for d in range(1, N + 1)] for k in ['販売数', '廃棄数']}
        for k in ['販売数', '廃棄数']:
            assert abs(sum(D['ncd'][dp][sc][k]) - D[dp][sc]['nc']['p26'][k]) < 0.5, (dp, sc, k)
json.dump(D, open(P, 'w'), ensure_ascii=False)
print('ok', {dp: round(D['fc'][dp]['ALL']['販売高']['fc']) for dp in D['fc']})
