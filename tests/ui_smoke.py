"""ブラウザで全タブ・全切り替えを開き、エラー・表示崩れ・未展開の文字がないか確かめる。

python3 tests/ui_smoke.py index.html [chart.umd.js]
暗号化なしで作ったページを渡す。Chart.js をネットから読めない環境では、2つめの引数に chart.umd.js を渡すと埋め込んで確認する。
要 playwright（pip install playwright && playwright install chromium）。
"""
import asyncio, json, os, re, sys, tempfile
from playwright.async_api import async_playwright
src = open(sys.argv[1], encoding='utf-8').read()
if len(sys.argv) > 2:
    js = open(sys.argv[2], encoding='utf-8').read()
    src = re.sub(r'<script src="https://cdnjs[^>]*></script>', lambda m: '<script>' + js + '</script>', src)
page = os.path.join(tempfile.mkdtemp(), 'p.html'); open(page, 'w', encoding='utf-8').write(src)
TABS = ['overview', 'sales', 'waste', 'sku', 'store', 'demand', 'action']
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); problems = []; checked = 0
        for w in [1300, 768, 390]:
            pg = await b.new_page(viewport={'width': w, 'height': 900}); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto('file://' + page); await pg.wait_for_timeout(1000)
            if await pg.evaluate('ALLD===null'): print('暗号化されたページです。暗号化なしで作ったページを渡してください。'); sys.exit(2)
            pers = await pg.evaluate("ALLD.meta.periods.map(p=>p.k)")
            for dept in ['FF', '厨房']:
                await pg.click(f'#dept button[data-d="{dept}"]')
                for per in pers:
                    await pg.click(f'.pb[data-k="{per}"]')
                    for s in ['ALL', '上新田', '朝日町', '元町一', '豊津中', '青山台']:
                        await pg.click(f'.sw[data-s="{s}"]')
                        for t in TABS:
                            await pg.click(f'.tab[data-t="{t}"]'); checked += 1
                            r = await pg.evaluate(r"""()=>{const t=document.body.innerText,bad=[];
                              for(const pat of ['{{','NaN','undefined','Infinity','[object','=>']){const i=t.indexOf(pat);if(i>=0)bad.push(pat+': '+t.slice(Math.max(0,i-40),i+30).replace(/\n/g,' '))}
                              if(/\bnull\b/.test(t))bad.push('null');
                              return {bad,ov:document.documentElement.scrollWidth>innerWidth+1,vis:[...document.querySelectorAll('section[data-tab]')].filter(e=>!e.hidden).length}}""")
                            if r['bad'] or r['ov'] or not r['vis']: problems.append((w, dept, per, s, t, r))
            problems += [(w, 'JS error', e) for e in errs]
        await b.close()
        print(f'{checked} 画面を確認、問題 {len(problems)} 件')
        for x in problems[:20]: print(x)
        sys.exit(1 if problems else 0)
asyncio.run(main())
