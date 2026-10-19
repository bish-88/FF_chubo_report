"""改善候補の自動抽出。

実績データ（CSVを集計した DataFrame）だけから、店舗×単品・店舗×カテゴリーの改善候補を作る。
試算は、下の式で誰でも同じ数字を再現できるようにしている。実績値（CSVから計算した値）と
仮定値（こちらで置いた前提）は、出力の中で必ず分けて持つ。

■ CSVから分かる単価（実績値）
  原価/個   = (販売高 − 荒利益高) ÷ (販売数 + 廃棄数)
              荒利益高は「販売高 − 作った分すべての原価」になっている（売れなかった日の荒利益高が
              −廃棄数×原価 になることで確認）。同じ単品なら日によるばらつきは 0.1% 程度。
  売価/個   = 販売高 ÷ 販売数（値引き後の平均）
  廃棄高/個 = 廃棄高 ÷ 廃棄数（廃棄高は定価ベース。荒利益高への影響は原価分だけ）

■ 廃棄削減（減産）の試算 ― 過去の日別実績に「毎日 r 個少なく作る」を当てはめる
  廃棄が出た日（廃棄 w 個）：その日の需要は販売数どおり。r ≤ w なら販売は減らない。
                              r > w なら (r − w) 個の販売を失う。
  廃棄ゼロの日：作った分は全部売れていたので、r 個少なく作ると r 個の販売を失う。
  荒利益高の変化（1日）= r × 原価 − max(0, r − w) × 売価
  これを期間の全記録日で合計し、7日分に換算する（×7÷記録日数）。
  r が 0.5（2日に1回 1個）のときは、1個減らす日と減らさない日が半々として 0.5 倍する。

■ 増産の試算 ― 毎日 1 個多く作る
  廃棄が出た日：追加の1個は売れ残る → −原価
  廃棄ゼロの日：需要が分からない（売り切れた時刻のデータがない）。
     売れた場合 +（売価 − 原価）／売れ残った場合 −原価 の両方を出す。
  損益分岐：追加分のうち 原価÷売価 以上が売れれば荒利益高はプラス。

■ 急変（先週比・前年比）
  日別の値（1日あたり）で比べ、ばらつきを考えた t 値で確度を決める。
  先週比：ウェルチの t 値（今週の日別 vs 先週の日別）
  前年比：同じ日付どうしの差の t 値（対応のある比較）
"""
import datetime, math
import numpy as np, pandas as pd

M = ['販売数', '販売高', '廃棄数', '廃棄高', '荒利益高']
CUT_RATE = 0.8          # 仮定：廃棄の約8割まで減らす（全部減らすと廃棄ゼロの日に売り切れが出るため）
CONF_ORDER = {'高': 0, '中': 1, '低': 2}


def cut_per_day(w):
    """1日に減らす数（画面の cutN と同じ決まり）。0 は「様子見」。"""
    if w >= 1.25: return max(1, math.floor(w * CUT_RATE))
    if w >= 0.75: return 1
    if w >= 0.3: return 0.5
    return 0


def unit_values(s):
    """合計値 s（Series/dict）から単価を出す。計算できないものは None。"""
    q, w = s['販売数'], s['廃棄数']
    cost = (s['販売高'] - s['荒利益高']) / (q + w) if q + w > 0 else None
    price = s['販売高'] / q if q > 0 else None
    wunit = s['廃棄高'] / w if w > 0 else None
    return cost, price, wunit


def sim_reduce(daily_w, r, cost, price):
    """日別の廃棄数 daily_w に「毎日 r 個減らす」を当てはめた荒利益高の変化（合計）と、販売を失う数。"""
    step = 1 if r == 0.5 else r
    k = 0.5 if r == 0.5 else 1.0
    gp = 0.0; lost = 0.0; wcut = 0.0
    for w in daily_w:
        l = max(0.0, step - w)
        gp += k * (step * cost - l * price); lost += k * l; wcut += k * min(step, w)
    return gp, lost, wcut


def _t_welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2: return None
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = math.sqrt(va + vb)
    return None if se == 0 else (a.mean() - b.mean()) / se


def _t_paired(d):
    d = np.asarray(d, float)
    if len(d) < 3: return None
    sd = d.std(ddof=1)
    return None if sd == 0 else d.mean() / (sd / math.sqrt(len(d)))


def _conf_t(t):
    if t is None: return None
    a = abs(t)
    return '高' if a >= 3 else '中' if a >= 2 else '低' if a >= 1.5 else None


def _down(c):
    return {'高': '中', '中': '低', '低': '低'}[c]


def _rng(d0, d1, wd):
    return f'10/{d0}（{wd(d0)}）〜10/{d1}（{wd(d1)}）'


def build(df, dept, ff, d0, d1, weeks, is_off, clean, year=2026, reclass=None):
    """df: その部門の全データ（year, d, store, cat, 商品名, M）。d0〜d1 が対象期間。
    weeks: 今年の週 [(start,end), ...]（古い順）。is_off(d): 土日祝なら True。
    reclass: {カテゴリー: 説明}。前年から分類が変わったカテゴリーは、前年比の確度を「低」にする。"""
    reclass = reclass or {}
    wd = lambda d: '月火水木金土日'[datetime.date(year, 10, d).weekday()]
    out = []
    y = df[(df.year == year)]
    p = y[y.d.between(d0, d1)]
    nd_period = d1 - d0 + 1
    per = _rng(d0, d1, wd) + f'・{nd_period}日間'

    # ---- 店舗×単品の日別 ----
    g = p.groupby(['store', 'cat', '商品名', 'd'])[M].sum()
    nrows = p.groupby(['store', 'cat', '商品名']).size()
    for (st, cat, name), x in g.groupby(level=[0, 1, 2]):
        x = x.droplevel([0, 1, 2]).sort_index()
        x = x[(x.販売数 + x.廃棄数) > 0]
        n = len(x)
        if n == 0: continue
        s = x.sum(); cost, price, wunit = unit_values(s)
        wdays = int((x.廃棄数 > 0).sum()); zdays = n - wdays
        wr = s.廃棄数 / (s.販売数 + s.廃棄数)
        wpd = s.廃棄数 / n
        wk = x[[not is_off(int(d)) for d in x.index]]; we = x[[is_off(int(d)) for d in x.index]]
        base = dict(dept=dept, store=st, cat=cat, name=clean(name), period=per, d0=d0, d1=d1,
                    n_days=int(n), n_rows=int(nrows.loc[(st, cat, name)]))
        actual = [['記録のある日数', n, '日'], ['販売数', s.販売数, '個'], ['廃棄数', s.廃棄数, '個'],
                  ['廃棄率（廃棄数÷(販売数＋廃棄数)）', wr * 100, '%'], ['廃棄が出た日', wdays, '日'], ['廃棄ゼロの日', zdays, '日'],
                  ['販売高', s.販売高, '円'], ['荒利益高', s.荒利益高, '円'], ['廃棄高（定価ベース）', s.廃棄高, '円']]
        units = []
        if cost is not None: units.append(['原価/個 ＝(販売高−荒利益高)÷(販売数＋廃棄数)', cost, '円'])
        if price is not None: units.append(['売価/個 ＝販売高÷販売数（値引き後の平均）', price, '円'])

        # 廃棄削減
        r = cut_per_day(wpd)
        if n >= 3 and s.廃棄数 >= 3 and wr >= 0.15 and r > 0 and cost and price:
            gp, lost, wcut = sim_reduce(x.廃棄数.values, r, cost, price)
            r0 = r
            if gp <= 0 and r > 0.5:   # 決まりどおりの数では荒利益高が下がる → 2日に1回 1個 でも試す
                g2 = sim_reduce(x.廃棄数.values, 0.5, cost, price)
                if g2[0] > 0: r = 0.5; gp, lost, wcut = g2
            k7 = 7 / n
            share = wdays / n
            conf = '高' if n >= 10 and share >= 0.5 else '中' if n >= 5 and share >= 0.3 else '低'
            why = f'記録{n}日・廃棄が出た日{wdays}日（{share*100:.0f}%）'
            wwk = wk.廃棄数.mean() if len(wk) else None; wwe = we.廃棄数.mean() if len(we) else None
            rtxt = '2日に1回 1個' if r == 0.5 else f'{r}個'
            plan = f'毎日 {rtxt} 少なく作る'
            if r != r0: plan += f'（{_cut_txt(r0)}減らすと荒利益高が下がる試算のため）'
            neg = gp <= 0
            if neg:
                plan = '作る数は減らさない（減らすと、失う販売の荒利が廃棄の原価を上回る試算）。廃棄が出る時間帯の陳列・値引きを確認する'
            elif r == r0 and wwk is not None and wwe is not None and abs(wwe - wwk) >= 1:
                plan = f'平日 {_cut_txt(cut_per_day(wwk))}・土日祝 {_cut_txt(cut_per_day(wwe))} 少なく作る（試算は毎日{rtxt}で計算）'
            out.append(dict(base, type='廃棄削減', neg=neg, conf=conf, conf_why=why,
                actual=actual + units + [['1日平均の廃棄数', wpd, '個'], ['平日の平均廃棄数', wwk, '個'], ['土日祝の平均廃棄数', wwe, '個']],
                assume=[f'1日に減らす数 r＝{rtxt}（廃棄の約{int(CUT_RATE*100)}%まで。1日平均の廃棄 {wpd:.2f}個 から決める。荒利益高が下がる場合は 2日に1回 1個 でも試す）',
                        '来週も、この期間と同じ日別の売れ方・廃棄の出方になる',
                        '廃棄ゼロの日は作った分が全部売れていた＝減らした分だけ販売を失う',
                        '原価・売価は期間の平均で一定'],
                formula=[f'1日の荒利益高の変化 ＝ r×原価 − max(0, r−その日の廃棄数)×売価',
                         f'期間合計 ＝ {gp:+,.0f}円（{n}日分）→ 7日換算 ＝ {gp:+,.0f} × 7 ÷ {n} ＝ {gp*k7:+,.0f}円/週',
                         f'うち販売を失う数 ＝ {lost:.1f}個（{n}日分）、減る廃棄数 ＝ {wcut:.1f}個（{n}日分）',
                         f'廃棄高（定価ベース）の減少 ＝ 減る廃棄数 × 廃棄高/個 {wunit:,.0f}円 ＝ {wcut*wunit*k7:,.0f}円/週'],
                est=[['荒利益高の変化', gp * k7, '円/週'], ['廃棄高の変化（定価ベース）', -wcut * wunit * k7, '円/週'],
                     ['販売数の変化', -lost * k7, '個/週']],
                score=gp * k7 if not neg else 0.0, action=plan,
                check=f'減らした後、売り切れ・欠品が増えていないか（この期間の廃棄ゼロの日：{zdays}日）'))

        # 増産
        thr = 4 if ff else 2
        if n >= 5 and zdays / n >= 0.8 and s.販売数 / n >= thr and cost and price:
            k7 = 7 / n; margin = price - cost
            up = (zdays * margin - wdays * cost) * k7      # 廃棄ゼロの日は全部売れた場合
            dn = -(n * cost) * k7                           # 全部売れ残った場合
            be = cost / price
            conf = '中' if n >= 10 and zdays == n else '低'
            if up <= 0: continue   # 全部売れても荒利益高が増えない
            out.append(dict(base, type='増産', conf=conf,
                conf_why=f'記録{n}日・廃棄ゼロ{zdays}日。売り切れた時刻のデータがないため、需要がどこまであるかは分からない（確度は最高でも「中」）',
                actual=actual + units + [['1日平均の販売数', s.販売数 / n, '個']],
                assume=['毎日 1個 多く作る', '廃棄が出た日は、追加の1個は売れ残る',
                        '廃棄ゼロの日に追加の1個が売れるかは分からない → 売れた場合と売れ残った場合の両方を出す',
                        '原価・売価は期間の平均で一定'],
                formula=[f'売れた場合：廃棄ゼロの日 {zdays}日 × (売価−原価) {margin:,.0f}円 − 廃棄が出た日 {wdays}日 × 原価 {cost:,.0f}円 → 7日換算 {up:+,.0f}円/週',
                         f'売れ残った場合：{n}日 × 原価 {cost:,.0f}円 → 7日換算 {dn:+,.0f}円/週',
                         f'損益分岐：追加分のうち 原価÷売価 ＝ {cost:,.0f}÷{price:,.0f} ＝ {be*100:.0f}% 以上が売れればプラス'],
                est=[['荒利益高の変化（追加分が全部売れた場合）', up, '円/週'], ['荒利益高の変化（全部売れ残った場合）', dn, '円/週'],
                     ['損益分岐の販売率', be * 100, '%']],
                score=up * 0.5, action='売り切れが早い日だけ 1個多く作り、売り切れ時刻を記録する',
                check='追加した分が何時ごろ売れたか・売れ残ったか（売れ残りが続けば元に戻す）'))

    # ---- 急変：先週比（店舗×カテゴリー、店舗×単品） ----
    if len(weeks) >= 2:
        (ps, pe), (cs, ce) = weeks[-2], weeks[-1]
        pdays = list(range(ps, pe + 1)); cdays = list(range(cs, ce + 1))
        offp = sum(is_off(d) for d in pdays); offc = sum(is_off(d) for d in cdays)
        rng = f'今週 {_rng(cs, ce, wd)}（{len(cdays)}日・土日祝{offc}日） vs 先週 {_rng(ps, pe, wd)}（{len(pdays)}日・土日祝{offp}日）'
        yy = y[y.d.between(ps, ce)]
        for level in ['cat', 'sku']:
            keys = ['store', 'cat'] if level == 'cat' else ['store', 'cat', '商品名']
            gg = yy.groupby(keys + ['d'])[M].sum()
            nr = yy.groupby(keys).size()
            for key, x in gg.groupby(level=list(range(len(keys)))):
                x = x.droplevel(list(range(len(keys))))
                if level == 'sku':
                    rec = x[(x.販売数 + x.廃棄数) > 0]
                    if len(rec) < 6: continue   # 少なすぎる単品は扱わない
                    # 単品は「記録がない日」を欠損として扱い、記録のある日だけで比べる
                    a = rec.reindex([d for d in cdays if d in rec.index]); b = rec.reindex([d for d in pdays if d in rec.index])
                    if len(a) < 3 or len(b) < 3: continue
                else:
                    a = x.reindex(cdays, fill_value=0); b = x.reindex(pdays, fill_value=0)
                for met, lab, thr, bad_up in [('販売高', '販売高（売上）', 5000 if level == 'cat' else 3000, False),
                                              ('荒利益高', '荒利益高', 3000 if level == 'cat' else 2000, False),
                                              ('廃棄高', '廃棄高（定価ベース）', 3000 if level == 'cat' else 2000, True)]:
                    am, bm = a[met].mean(), b[met].mean(); dw = (am - bm) * 7
                    if abs(dw) < thr: continue
                    t = _t_welch(a[met].values, b[met].values); conf = _conf_t(t)
                    if conf is None: continue
                    why = f't値 {t:+.1f}（日別のばらつきに対する差の大きさ）・今週{len(a)}日 vs 先週{len(b)}日'
                    if offp != offc: conf = _down(conf); why += '・週の土日祝の日数が違うため1段階下げ'
                    up = dw > 0; worse = up if bad_up else not up
                    st = key[0]; cat = key[1]; name = clean(key[2]) if level == 'sku' else f'{cat}（カテゴリー計）'
                    pct = (am / bm - 1) * 100 if bm else None
                    out.append(dict(dept=dept, store=st, cat=cat, name=name, type='急変', sub='先週比', metric=lab, dir='増' if up else '減',
                        period=rng, d0=cs, d1=ce, n_days=int(len(a) + len(b)), n_rows=int(nr.loc[key]), conf=conf, conf_why=why,
                        actual=[[f'今週 {lab} 1日平均', am, '円'], [f'先週 {lab} 1日平均', bm, '円'], ['差（1日あたり）', am - bm, '円'],
                                ['増減率（1日あたり）', pct, '%'], ['今週の日数', len(a), '日'], ['先週の日数', len(b), '日']],
                        assume=['差を7日分に直して表示（1日あたりの差×7）', '原因（天気・販促・欠品など）はこのデータからは分からない'],
                        formula=[f'差（週換算）＝（今週の1日平均 {am:,.0f} − 先週の1日平均 {bm:,.0f}）× 7 ＝ {dw:+,.0f}円',
                                 f't値 ＝ 差 ÷ √(今週の分散/日数 ＋ 先週の分散/日数) ＝ {t:+.2f}（|t|≥3 高・≥2 中・≥1.5 低、1.5未満は出さない）'],
                        est=[[f'{lab}の差（週換算）', dw, '円/週']],
                        score=abs(dw) * (1.2 if worse else 0.8), worse=worse,
                        action=_change_action(met, up, level),
                        check='来週も同じ方向に続くか（1週だけの動きなら様子を見る）'))

    # ---- 急変：前年比（店舗×カテゴリー、同じ日付どうし） ----
    ly = df[(df.year == year - 1) & df.d.between(d0, d1)]
    a_ = p.groupby(['store', 'cat', 'd'])[M].sum(); b_ = ly.groupby(['store', 'cat', 'd'])[M].sum()
    nr_a = p.groupby(['store', 'cat']).size(); nr_b = ly.groupby(['store', 'cat']).size()
    days = list(range(d0, d1 + 1))
    for key in sorted(set(a_.index.droplevel(2)) | set(b_.index.droplevel(2))):
        A = a_.loc[key].reindex(days, fill_value=0) if key in a_.index.droplevel(2) else None
        B = b_.loc[key].reindex(days, fill_value=0) if key in b_.index.droplevel(2) else None
        if A is None or B is None or len(days) < 5: continue
        for met, lab, bad_up in [('販売高', '販売高（売上）', False), ('荒利益高', '荒利益高', False), ('廃棄高', '廃棄高（定価ベース）', True)]:
            sa, sb = A[met].sum(), B[met].sum()
            if sb <= 0: continue
            diff = sa - sb; pct = (sa / sb - 1) * 100
            if abs(pct) < 15 or abs(diff) < 10000: continue
            t = _t_paired((A[met] - B[met]).values); conf = _conf_t(t)
            if conf is None: continue
            up = diff > 0; worse = up if bad_up else not up
            why = f'同じ日付どうしの差の t値 {t:+.1f}・{len(days)}日分の組'
            if key[1] in reclass: conf = '低'; why += f'。ただし{reclass[key[1]]}ため「低」'
            out.append(dict(dept=dept, store=key[0], cat=key[1], name=f'{key[1]}（カテゴリー計）', type='急変', sub='前年比', metric=lab, dir='増' if up else '減',
                period=f'{per}（前年も同じ日付）', d0=d0, d1=d1, n_days=len(days) * 2, n_rows=int(nr_a.get(key, 0) + nr_b.get(key, 0)),
                conf=conf, conf_why=why,
                actual=[[f'今年 {lab}', sa, '円'], [f'前年 {lab}（同じ日付）', sb, '円'], ['差', diff, '円'], ['増減率', pct, '%'], ['比べた日数', len(days), '日']],
                assume=['前年と今年で曜日の並びが違う（同じ日付どうしで比較）', '商品の入れ替え・分類の変更も差に含まれる'],
                formula=[f'差 ＝ 今年 {sa:,.0f} − 前年 {sb:,.0f} ＝ {diff:+,.0f}円（{pct:+.1f}%）',
                         f't値 ＝ 日別の差の平均 ÷（日別の差の標準偏差÷√日数）＝ {t:+.2f}'],
                est=[[f'{lab}の前年差（期間合計）', diff, '円']],
                score=abs(diff) / max(1, len(days)) * 7 * (1.2 if worse else 0.8), worse=worse,
                action=_change_action(met, up, 'cat', yoy=True),
                check='分類の変更や新商品の影響がないか（集計方法を参照）'))

    out.sort(key=lambda c: (_group(c), CONF_ORDER[c['conf']], -abs(c['score'])))
    for i, c in enumerate(out): c['id'] = f'{dept}-{d0}-{d1}-{i}'
    return _py(out)


def _py(o):
    """numpy の型を JSON にできる Python の型へ。NaN は None（欠損）にする。"""
    if isinstance(o, dict): return {k: _py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_py(v) for v in o]
    if isinstance(o, (np.bool_, bool)): return bool(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating, float)): return None if math.isnan(o) else float(o)
    return o


def _group(c):
    """並び順：すぐ手を打てるものを先に。0 廃棄削減 → 1 悪い方向の急変 → 2 増産 → 3 良い方向の急変 → 4 減らさない方がよい単品"""
    if c['type'] == '廃棄削減': return 4 if c.get('neg') else 0
    if c['type'] == '急変': return 1 if c.get('worse') else 3
    return 2


def _cut_txt(r):
    return '様子見' if r == 0 else '2日に1回 1個' if r == 0.5 else f'{r}個'


def _change_action(met, up, level, yoy=False):
    if met == '廃棄高':
        return '仕込み数と追加調理の時間帯を見直す（廃棄が増えた日と時間帯を確認）' if up else '廃棄が減った週の仕込み方を記録し、続ける'
    if up:
        return '伸びた理由（販促・天気・新商品・陳列）を確認し、欠品しないよう仕込み数を確認する'
    return ('売上が落ちた理由を確認する：欠品・陳列・発注数・商品の入れ替え（原因はこのデータからは特定できない）'
            if not yoy else '前年から落ちた理由を確認する：商品の入れ替え・分類の変更・陳列（原因はこのデータからは特定できない）')
