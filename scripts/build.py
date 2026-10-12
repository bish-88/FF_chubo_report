import pandas as pd, numpy as np, glob, json, datetime, os, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m=['販売数','販売高','廃棄数','廃棄高','荒利益高']
SN={'新御堂筋上新田':'上新田','吹田朝日町':'朝日町','豊中服部元町一丁目':'元町一','吹田豊津中学校前':'豊津中','吹田青山台三丁目':'青山台'}
STORES=list(SN.values())
def read(files,catfn):
    dfs=[]
    for f in files:
        d=pd.read_csv(f,encoding='cp932',dtype=str)[['年月日','店舗名','CLASS名','SUBCLASS名','商品名']+m]
        dfs.append(d)
    df=pd.concat(dfs)
    for c in m: df[c]=pd.to_numeric(df[c].str.replace(',',''),errors='coerce').fillna(0)
    df['date']=pd.to_datetime(df['年月日']); df['year']=df.date.dt.year; df['d']=df.date.dt.day
    df['cat']=catfn(df); df['store']=df.店舗名.map(SN)
    df=df[(df[m]!=0).any(axis=1)&df.cat.notna()]
    return df.drop_duplicates(['年月日','店舗名','SUBCLASS名','商品名']+m)
catmap={'販売）からあげクン他　ホット':'からあげクン','ホットＦＦ':'ホットFF','常温ＦＦ':'常温FF','販売）サーマル　常温':'サーマル常温','販売）マチカフェ':'マチカフェ','中華まん　什器販売':'中華まん'}
FF=read(sorted(glob.glob(os.path.join(ROOT,'data','FF','*.csv'))),lambda d:d.CLASS名.map(catmap))
KI=read(sorted(glob.glob(os.path.join(ROOT,'data','厨房','*.csv'))),lambda d:d.SUBCLASS名.where(d.SUBCLASS名.isin(['弁当','惣菜','調理パン'])))
F=float
# 今年のデータが何日まであるか（FF・厨房で共通の日数）
N=int(min(FF[FF.year==2026].d.max(),KI[KI.year==2026].d.max()))
def is_we(y,d): return datetime.date(y,10,d).weekday()>=5
def tot(x): s=x[m].sum(); return {k:F(s[k]) for k in m}
def clean(n): return ' '.join(n.replace('●','').replace('　',' ').split())
AL={'常温　カリパン　ＫＹ':'常温　カリパン　Ｙ','常温　ジャイアントポークフランク　１本':'ＨＯＴ　ジャイアントポークフランク','常温　なんこつ入りつくね棒　１本':'ＨＯＴ　なんこつ入りつくね棒　１本'}
# weather
rain=[0,0,2.5,13,2.5,0,0,0,0,0,0,5.5,0,0,2,1,0,6.5,11.5,4.5,0,2.5,0,0,12.5,1,0,0,0,0,36]
tmax=[28.5,28,25.8,22.4,25.1,29.7,31.2,31.8,28.2,25.9,28.5,25.7,29,29.8,27.6,26.4,28.9,26.3,23.1,24,19.5,15.9,23.6,22.7,22.2,21.3,22.5,19.3,19.5,22.3,17.1]
W=pd.DataFrame({'d':range(1,32),'rain':rain,'tmax':tmax})
W['wd']=[datetime.date(2025,10,d).weekday() for d in W.d]
W['type']=np.where((W.wd==6)|(W.d==13),'日祝',np.where(W.wd==5,'土','平日')); W['wet']=W.rain>=2
# 今年の天気実績（気象庁 大阪 日別値）。日付を追加したら同じ形で足していく
RAIN26={1:0,2:0,3:0,4:14.0,5:10.0,6:0,7:0,8:0,9:0,10:0,11:0}
TMAX26={1:29.6,2:27.3,3:26.9,4:21.4,5:22.0,6:26.1,7:25.8,8:26.8,9:29.0,10:28.8,11:29.8}
# 天気予報（吹田市、tenki.jp）。新しい予報に更新するときはここを書き換える
FC_ISSUED='10/12 21時発表'
FC=[(12,'晴',28,0),(13,'晴時々曇',28,30),(14,'雨のち晴',25,90),(15,'晴時々曇',25,20),(16,'曇時々晴',25,20),(17,'晴時々曇',27,20),(18,'晴',27,20),(19,'曇のち雨',26,80),(20,'雨のち晴',26,80),(21,'晴時々曇',24,40),(22,'曇時々晴',22,20),(23,'曇のち雨',22,70),(24,'曇時々雨',23,70),(25,'雨のち曇',22,60)]
fc={r[0]:r for r in FC}; HOL={12:'スポーツの日'}; EV={31:'ハロウィン'}
def fx(series):
    X=pd.DataFrame({'c':1,'sat':(W.type=='土')*1,'sun':(W.type=='日祝')*1,'wet':W.wet*1,'t':W.tmax-25})
    b,*_=np.linalg.lstsq(X.values.astype(float),np.log(np.clip(series.values,0,None)+1),rcond=None)
    return dict(sat=F(np.exp(b[1])-1),sun=F(np.exp(b[2])-1),wet=F(np.exp(b[3])-1),t=F(np.exp(b[4])-1))

HOL26={12}
def is_off26(d): return datetime.date(2026,10,d).weekday()>=5 or d in HOL26
def weekly(x,ns,cats):
    # 今年のデータを月曜始まりの週に分け、1店1日あたり（PSA/D）で比べる
    y=x[x.year==2026]
    days=sorted(int(v) for v in y.d.unique())
    wkof=lambda d:datetime.date(2026,10,d).isocalendar()[1]
    weeks=[]
    for w in sorted({wkof(d) for d in days}):
        ds=[d for d in days if wkof(d)==w]
        mon=datetime.date.fromisocalendar(2026,w,1)
        def block(sel):
            sd=[d for d in ds if sel(d)]
            z=y[y.d.isin(sd)]
            def psa(zz,n):
                t=zz[m].sum(); dd=max(1,n)*ns
                o={k:F(t[k]/dd) for k in m}; o['wr']=F(t['廃棄数']/max(1,t['販売数']+t['廃棄数'])); return o
            out={'n':len(sd),'tot':psa(z,len(sd))}
            out['cat']={c:psa(z[z.cat==c],len(sd)) for c in cats}
            return out
        weeks.append(dict(label=f"{mon.month}/{mon.day}週",start=ds[0],end=ds[-1],
            first='月火水木金土日'[datetime.date(2026,10,ds[0]).weekday()],last='月火水木金土日'[datetime.date(2026,10,ds[-1]).weekday()],
            all=block(lambda d:True),wk=block(lambda d:not is_off26(d)),we=block(is_off26)))
    # 曜日別 PSA/D（販売高・荒利益高・廃棄高）
    byd={}
    for d in days:
        t=y[y.d==d][m].sum(); byd[d]={k:F(t[k]/ns) for k in m}
    return dict(weeks=weeks,byday=byd)

def dept(df,cats,excl,colors,ff):
    wdf=df[~df.cat.isin(excl)]
    def bycat(x):
        g=x.groupby('cat')[m].sum().reindex(cats).fillna(0); return {c:{k:F(g.loc[c,k]) for k in m} for c in cats}
    def scope(x,single):
        y25=x[x.year==2025]; y26=x[x.year==2026]; sp25=y25[y25.d<=N]
        o={'kpi':{'p25':tot(sp25),'p26':tot(y26),'m25':tot(y25)}}
        o['daily25']={k:[F(v) for v in y25.groupby('d')[k].sum().reindex(range(1,32),fill_value=0)] for k in ['荒利益高','廃棄高','販売数','販売高']}
        o['daily26']={k:[F(v) for v in y26.groupby('d')[k].sum().reindex(range(1,N+1),fill_value=0)] for k in ['荒利益高','廃棄高','販売数','販売高']}
        o['cat']={'p25':bycat(sp25),'p26':bycat(y26),'m25':bycat(y25)}
        nc=x[~x.cat.isin(excl)]
        a=nc[nc.year==2026]; b=nc[(nc.year==2025)&(nc.d<=N)]; mm=nc[nc.year==2025]
        p=a.groupby(['cat','商品名'])[m].sum()
        sd=a.groupby(['cat','商品名','store','d'])[['販売数','廃棄数']].sum(); sd=sd[sd.販売数+sd.廃棄数>0]
        p['sd']=sd.groupby(['cat','商品名']).size(); p['wsd']=sd.assign(z=sd.廃棄数>0).groupby(['cat','商品名']).z.sum()
        sdr=sd.reset_index(); sdr['we']=[is_we(2026,int(v)) for v in sdr.d]
        p['wwk']=sdr[~sdr.we].groupby(['cat','商品名']).廃棄数.mean(); p['wwe']=sdr[sdr.we].groupby(['cat','商品名']).廃棄数.mean()
        pb=b.groupby('商品名')[m].sum(); pm=mm.groupby('商品名')[m].sum()
        rows=[]; minsold=3 if single else 10
        for (c,n),r in p.iterrows():
            if r.販売数+r.廃棄数<minsold: continue
            nl=AL.get(n,n) if ff else n
            wr=r.廃棄数/(r.販売数+r.廃棄数); so=1-r.wsd/r.sd; per=r.販売数/r.sd; wpd=r.廃棄数/r.sd
            if (wr>=0.15 and r.廃棄高>=(500 if single else 1000)) or (r.廃棄高>r.荒利益高*0.6 and r.廃棄高>=500): v='reduce'
            elif wr<=0.05 and so>=0.8 and per>=(4 if single else 2.5) and r.販売数>=(12 if single else 20): v='increase'
            elif wr>=0.10: v='watch'
            else: v='keep'
            lw=None
            if nl in pm.index and pm.loc[nl,'販売数']+pm.loc[nl,'廃棄数']>0: lw=F(pm.loc[nl,'廃棄数']/(pm.loc[nl,'販売数']+pm.loc[nl,'廃棄数']))
            rows.append(dict(cat=c,name=clean(n),amt=F(r.販売高),amt_ly=(F(pb.loc[nl,'販売高']) if nl in pb.index else None),sold=F(r.販売数),w=F(r.廃棄数),wy=F(r.廃棄高),gp=F(r.荒利益高),wr=F(wr),so=F(so),per=F(per),wpd=F(wpd),
                sd=int(r.sd),wsd=int(r.wsd),wwk=F(r.wwk) if r.wwk==r.wwk else 0.0,wwe=F(r.wwe) if r.wwe==r.wwe else 0.0,sold_ly=(F(pb.loc[nl,'販売数']) if nl in pb.index else None),alias=(nl!=n),ly_wr=lw,v=v))
        o['prod']=sorted(rows,key=lambda r:-r['gp'])
        l=mm.groupby(['cat','商品名'])[m].sum(); l=l[l.販売数+l.廃棄数>0]; l['wr']=l.廃棄数/(l.販売数+l.廃棄数)
        o['lesson']=[dict(cat=c,name=clean(n),wy=F(r.廃棄高),gp=F(r.荒利益高),wr=F(r.wr)) for (c,n),r in l.sort_values('廃棄高',ascending=False).head(10 if single else 12).iterrows()]
        sp=a.groupby(['store','cat','商品名'])[['販売数','廃棄数','廃棄高','荒利益高']].sum()
        dd=a.groupby(['store','cat','商品名','d'])[['販売数','廃棄数']].sum(); dd=dd[dd.販売数+dd.廃棄数>0]
        sp['days']=dd.groupby(['store','cat','商品名']).size()
        ddr=dd.reset_index(); ddr['we']=[is_we(2026,int(v)) for v in ddr.d]
        sp['wwk']=ddr[~ddr.we].groupby(['store','cat','商品名']).廃棄数.mean(); sp['wwe']=ddr[ddr.we].groupby(['store','cat','商品名']).廃棄数.mean()
        sp['wmin']=ddr.groupby(['store','cat','商品名']).廃棄数.min(); sp['zd']=ddr.assign(z=ddr.廃棄数==0).groupby(['store','cat','商品名']).z.sum()
        inc=sp[(sp.廃棄数==0)&(sp.days>=max(4,round(N*0.8)))&(sp.販売数/sp.days>=(4 if ff else 2))]
        dec=sp[(sp.廃棄数/(sp.販売数+sp.廃棄数)>=0.2)&(sp.廃棄高>=(500 if single else 1000))]
        o['inc']=[dict(store=i[0],cat=i[1],name=clean(i[2]),per=F(r.販売数/r.days),gp=F(r.荒利益高)) for i,r in inc.sort_values('荒利益高',ascending=False).head(10).iterrows()]
        o['dec']=[dict(store=i[0],cat=i[1],name=clean(i[2]),per=F(r.販売数/r.days),wpd=F(r.廃棄数/r.days),wy=F(r.廃棄高),wr=F(r.廃棄数/(r.販売数+r.廃棄数)),wwk=F(r.wwk) if r.wwk==r.wwk else 0.0,wwe=F(r.wwe) if r.wwe==r.wwe else 0.0,zd=int(r.zd)) for i,r in dec.sort_values('廃棄高',ascending=False).head(10).iterrows()]
        o['wcat']={k:{c:F(v) for c,v in z.groupby('cat').廃棄高.sum().items()} for k,z in [('p26',a),('p25',b),('m25',mm)]}
        o['nc']={'p26':tot(a),'p25':tot(b),'m25':tot(mm)}
        # weather / daytype
        yy=x[x.year==2025]; dd2=yy.groupby('d')[m].sum().reindex(range(1,32),fill_value=0)
        ncd=nc[nc.year==2025].groupby('d')[['販売数','廃棄数']].sum().reindex(range(1,32),fill_value=0)
        dd2['type']=W.type.values; dd2['wet']=W.wet.values
        g=dd2.groupby('type')[['荒利益高','廃棄高','販売高']].mean(); gw=dd2.groupby('wet')[['荒利益高','廃棄高','販売高']].mean()
        ng=ncd.assign(type=W.type.values).groupby('type').sum()
        ST={t:dict(amt=F(g.loc[t,'販売高']),gp=F(g.loc[t,'荒利益高']),idx=F(g.loc[t,'荒利益高']/g.loc['平日','荒利益高']),wy=F(g.loc[t,'廃棄高']),wr=F(ng.loc[t,'廃棄数']/max(1,ng.loc[t,'販売数']+ng.loc[t,'廃棄数']))) for t in ['平日','土','日祝']}
        ST['wet']=dict(amt=F(gw.loc[True,'販売高']/gw.loc[False,'販売高']-1),gp=F(gw.loc[True,'荒利益高']/gw.loc[False,'荒利益高']-1),wy=F(gw.loc[True,'廃棄高']/max(1,gw.loc[False,'廃棄高'])-1))
        o['st']=ST
        yoy=o['kpi']['p26']['荒利益高']/o['kpi']['p25']['荒利益高']; yoys=o['kpi']['p26']['販売高']/o['kpi']['p25']['販売高']
        cal=[]
        for d in range(N+1,32):
            dt=datetime.date(2026,10,d); wd='月火水木金土日'[dt.weekday()]
            typ='日祝' if dt.weekday()==6 or d in HOL else '土' if dt.weekday()==5 else '平日'
            f=fc.get(d); wet=bool(f and f[3]>=50)
            idx=ST[typ]['idx']*(1+ST['wet']['gp'] if wet else 1)
            sig='risk' if wet or idx<=0.88 else 'chance' if idx>=1.08 else 'normal'
            cal.append(dict(d=d,wd=wd,typ=typ,hol=HOL.get(d) or EV.get(d),wx=f[1] if f else None,tmax=f[2] if f else None,pop=f[3] if f else None,wet=wet,idx=F(idx),exp=F(ST[typ]['gp']*(1+ST['wet']['gp'] if wet else 1)*yoy),exps=F(ST[typ]['amt']*(1+ST['wet']['amt'] if wet else 1)*yoys),sig=sig))
        o['cal']=cal
        o['wk']=weekly(x,1 if single else len(STORES),cats)
        return o
    out={'cats':cats,'excl':excl,'colors':colors,'ff':ff,'ALL':scope(df,False)}
    for s in STORES: out[s]=scope(df[df.store==s],True)
    out['stores']={s:{'p26':tot(df[(df.store==s)&(df.year==2026)]),'p25':tot(df[(df.store==s)&(df.year==2025)&(df.d<=N)]),
        'nc26':tot(wdf[(wdf.store==s)&(wdf.year==2026)]),'nc25':tot(wdf[(wdf.store==s)&(wdf.year==2025)&(wdf.d<=N)])} for s in STORES}
    y=df[df.year==2025]
    res={}
    for c in ['ALL']+cats:
        x=y if c=='ALL' else y[y.cat==c]
        dd=x.groupby('d')[['販売数','荒利益高']].sum().reindex(range(1,32),fill_value=0)
        res[c]={'qty':fx(dd.販売数),'gp':fx(dd.荒利益高)}
    tq=y.groupby('d').販売数.sum().reindex(range(1,32),fill_value=0)
    wx=dict(W=dict(d=list(W.d),tmax=tmax,rain=rain,wet=[bool(v) for v in W.wet],type=list(W.type),tq=[F(v) for v in tq]),res=res)
    if ff and 'マチカフェ' in cats:
        yy=y[y.cat=='マチカフェ'].copy(); yy['ice']=yy.商品名.str.contains('アイス')
        mc=yy.groupby(['d','ice']).販売数.sum().unstack().fillna(0).reindex(range(1,32),fill_value=0)
        wx['W']['ice']=[F(v) for v in mc[True]/(mc[True]+mc[False])]
        wx['corr']=F(np.corrcoef(tmax,wx['W']['ice'])[0,1])
    if ff and '中華まん' in cats:
        ch=y[y.cat=='中華まん'].groupby('d').販売数.sum().reindex(range(1,32),fill_value=0)
        wx['W']['chuka']=[F(v) for v in ch]
        wx['chukaCorr']=F(np.corrcoef(tmax,ch)[0,1])
        bands=[(0,22),(22,26),(26,40)]
        wx['chukaBand']=[dict(lo=lo,hi=hi,n=int(((W.tmax>=lo)&(W.tmax<hi)).sum()),avg=F(ch[((W.tmax>=lo)&(W.tmax<hi)).values].mean())) for lo,hi in bands]
    if not ff:
        wx['corr']=F(np.corrcoef(tmax,tq)[0,1])
        # by category corr with tmax
        wx['catcorr']={c:F(np.corrcoef(tmax,y[y.cat==c].groupby('d').販売数.sum().reindex(range(1,32),fill_value=0))[0,1]) for c in cats}
    out['wx']=wx
    return out
def present(df,order):
    have=lambda y:set(df[df.year==y].cat.unique())
    return [c for c in order if c in have(2025) and c in have(2026)]
FFC=present(FF,['からあげクン','マチカフェ','ホットFF','常温FF','サーマル常温','中華まん'])
D={'FF':dept(FF,FFC,[c for c in ['マチカフェ'] if c in FFC],[],True),
   '厨房':dept(KI,['弁当','調理パン','惣菜'],[],['--c2','--c1','--c4'],False)}
WD='月火水木金土日'
def wcount(y): 
    ds=[datetime.date(y,10,d) for d in range(1,N+1)]
    return dict(we=sum(d.weekday()>=5 for d in ds),first=WD[ds[0].weekday()],last=WD[ds[-1].weekday()])
D['meta']=dict(N=N,w26=wcount(2026),w25=wcount(2025),fc=FC_ISSUED,
  wx26=[dict(d=d,rain=RAIN26.get(d),tmax=TMAX26.get(d)) for d in range(1,N+1)],
  dropped=[c for c in ['マチカフェ','中華まん'] if c not in FFC])
tpl=open(os.path.join(ROOT,'scripts','template.html'),encoding='utf-8').read()
PW=os.environ.get('REPORT_PASSWORD','')
payload=json.dumps(D,ensure_ascii=False)
if PW:
    import base64, secrets, hashlib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    it=1000000; salt=secrets.token_bytes(16); iv=secrets.token_bytes(12)
    key=hashlib.pbkdf2_hmac('sha256',PW.encode(),salt,it,32)
    ct=AESGCM(key).encrypt(iv,payload.encode('utf-8'),None)
    e=lambda b:base64.b64encode(b).decode()
    tpl=tpl.replace('__ENC__',json.dumps({'s':e(salt),'i':e(iv),'c':e(ct),'it':it})); payload='null'
    print('データをパスワードで暗号化しました')
else:
    tpl=tpl.replace('__ENC__','null')
    print('注意：REPORT_PASSWORD が未設定のため、暗号化していません（GitHubに上げないでください）')
head='<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
open(os.path.join(ROOT,'index.html'),'w',encoding='utf-8').write(head+tpl.replace('__DATA__',payload).replace('<header class="band">','</head>\n<body>\n<header class="band">',1)+'\n</body>\n</html>\n')
print('index.html を更新しました')

