"""実施管理の書き出しファイル（JSON）をまとめて、共有版 data/actions.json を作る。

使い方：
  python scripts/merge_actions.py 店長Aの書き出し.json 店長Bの書き出し.json ...
  （今の data/actions.json があれば、それも元にしてまとめる）

決まり：
- 同じ ID の記録は、更新日時（updated_at）が新しい方を残す。
- 同じ ID を、前回の共有版より後に2人以上が直していた場合は「競合」として表示する
  （新しい方を残すが、古い方の内容は失われるので、表示を見て確認する）。
- 形式の違う行は捨てて、件数を表示する。
"""
import json, os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('ACTIONS_FILE', os.path.join(ROOT, 'data', 'actions.json'))
STATUS = ['未着手', '実施中', '完了', '見送り']


def items_of(path):
    raw = json.load(open(path, encoding='utf-8'))
    items = raw.get('items', []) if isinstance(raw, dict) else raw
    return items if isinstance(items, list) else []


def merge(base, files):
    cur = {r['id']: r for r in base}
    base_upd = {r['id']: r.get('updated_at') or '' for r in base}
    touched, conflicts, bad = {}, [], 0
    for path in files:
        for r in items_of(path):
            if not isinstance(r, dict) or not r.get('id') or r.get('dept') not in ('FF', '厨房'):
                bad += 1; continue
            if r.get('status') not in STATUS: r['status'] = '未着手'
            r.pop('_src', None)
            u = r.get('updated_at') or ''
            if u > base_upd.get(r['id'], ''):                       # 前回の共有版より後に直された
                if r['id'] in touched and touched[r['id']][1] != path:
                    conflicts.append((r['id'], touched[r['id']][1], path))
                touched.setdefault(r['id'], (u, path))
            if r['id'] not in cur or u > (cur[r['id']].get('updated_at') or ''):
                cur[r['id']] = r
    return list(cur.values()), conflicts, bad


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    base = items_of(OUT) if os.path.exists(OUT) else []
    items, conflicts, bad = merge(base, sys.argv[1:])
    items.sort(key=lambda r: r.get('created_at') or '')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({'format': 'ff-report-actions', 'version': 1, 'merged_at': datetime.datetime.now().isoformat(timespec='seconds'), 'items': items},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{OUT} に {len(items)} 件を書きました（前回 {len(base)} 件）。形式の違う行：{bad} 件')
    for i, a, b in conflicts:
        print(f'  競合：{i} を {os.path.basename(a)} と {os.path.basename(b)} の両方で変更 → 更新日時が新しい方を残しました。内容を確認してください')
    print('次に：REPORT_PASSWORD=（パスワード） python scripts/build.py でページを作り直します')
