import re,subprocess,sys,collections
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"
def get(u):
    try: return subprocess.run(["curl","-sSL","--max-time","25","-A",UA,u],capture_output=True,text=True,timeout=35).stdout
    except: return ""
for host in sys.argv[1:]:
    urls=set()
    for path in ["/sitemap.xml","/sitemap_index.xml","/wp-sitemap.xml","/sitemap-1.xml"]:
        x=get(host+path)
        if "<loc>" not in x: continue
        locs=re.findall(r"<loc>(.*?)</loc>",x)
        subs=[l for l in locs if l.endswith(".xml")]
        if subs:
            for s in subs[:6]:
                urls |= set(l for l in re.findall(r"<loc>(.*?)</loc>",get(s)) if not l.endswith(".xml"))
        else:
            urls |= set(locs)
        if urls: break
    if not urls:
        print(f"{host:<34} sitemap 없음/차단"); continue
    # 카테고리 폭 추정: URL slug 토큰 빈도
    toks=collections.Counter()
    for u in urls:
        for t in re.findall(r"[a-z]{4,}", u.split("//")[-1].split("/",1)[-1].lower()):
            if t not in ("html","index","page","post","entry","category","tag","www"): toks[t]+=1
    print(f"{host:<34} URL {len(urls):>5}개 | 상위토큰 {[t for t,_ in toks.most_common(8)]}")
