import json, os, random, re, socket, sys, time, yaml, requests
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
sys.path.insert(0,'.')
from scraper import uri_to_clash
from geoip_rename import clean_org, is_routable_ip, FIELDS
LIMIT=int(os.environ.get('LIMIT','400'))
HERE=os.path.dirname(os.path.abspath(__file__))
MIHOMO=os.environ.get('MIHOMO',os.path.join(HERE,'mihomo'))
OUT=os.environ.get('OUT',os.path.join(HERE,'dist','.clash.new.yaml'))
random.seed(int(time.time()))
raw='output/raw'
uris=[l.strip() for l in open(f'{raw}/nodes.txt',encoding='utf-8') if l.strip()]
pairs=[p for p in (uri_to_clash(u) for u in uris) if p]
try: pairs+=[dict(p) for p in json.load(open(f'{raw}/_yaml_proxies.json')) if isinstance(p,dict) and p.get('server')]
except FileNotFoundError: pass
print('raw',len(pairs))
def bad(p):
    r=p.get('reality-opts')
    if isinstance(r,dict):
        if not r.get('public-key'): return True
        sid=r.get('short-id','')
        if sid is None: sid=''
        if not isinstance(sid,str): sid=str(sid); r['short-id']=sid
        if len(sid)>16 or len(sid)%2 or not re.fullmatch(r'[0-9a-fA-F]*',sid): return True
    return '¬' in str(p)
def cred(p): return p.get('uuid') or p.get('password') or ''
def front(p):
    w=(p.get('ws-opts') or {})
    host=((w.get('headers') or {}).get('Host') or p.get('servername') or p.get('sni') or '').lower().rstrip('.')
    return host, w.get('path','')
# 去重1：完整配置（忽略名字）
seen,ded=set(),[]
for p in pairs:
    p.pop('_source',None)
    if bad(p): continue
    k=json.dumps({x:y for x,y in p.items() if x!='name'},sort_keys=True,ensure_ascii=False)
    if k in seen: continue
    seen.add(k); ded.append(p)
print('dedup-config',len(ded))
# 去重2：server+port+type
seen,d2=set(),[]
for p in ded:
    k=(str(p.get('server')).lower(),p.get('port'),p.get('type'))
    if k in seen: continue
    seen.add(k); d2.append(p)
print('dedup-server-port',len(d2))
# 去重3：同一后端（凭据+伪装域名+路径）走不同CDN IP只留一个
seen,d3=set(),[]
for p in d2:
    h,path=front(p); c=cred(p)
    if h and c:
        k=(p.get('type'),c,h,path)
        if k in seen: continue
        seen.add(k)
    d3.append(p)
print('dedup-backend',len(d3))
random.shuffle(d3)
socket.setdefaulttimeout(4)
def res(h):
    if re.fullmatch(r'[\d.]+',h or ''): return h
    try: return socket.gethostbyname(h)
    except Exception: return None
# 先挑 LIMIT 个（多线程DNS；去重4：同IP+端口+协议只留一个）
chosen=[]; usedk=set(); i=0
with ThreadPoolExecutor(64) as ex:
    while len(chosen)<LIMIT*1.6 and i<len(d3):
        batch=d3[i:i+300]; i+=300
        for p,ip in zip(batch,ex.map(lambda p:res(p['server']),batch)):
            if not ip or not is_routable_ip(ip): continue
            k=(ip,p.get('port'),p.get('type'))
            if k in usedk: continue
            usedk.add(k); chosen.append((p,ip))
print('candidates',len(chosen))
import subprocess, tempfile, os
def valid(item):
    p=item[0]
    d=tempfile.mkdtemp(dir='/tmp/mt')
    f=os.path.join(d,'c.yaml')
    yaml.safe_dump({'proxies':[p],'rules':['MATCH,DIRECT']},open(f,'w',encoding='utf-8'),allow_unicode=True)
    r=subprocess.run([MIHOMO,'-t','-d',d,'-f',f],capture_output=True,text=True,timeout=30)
    ok='successful' in (r.stdout+r.stderr)
    subprocess.run(['rm','-rf',d])
    return ok
os.makedirs('/tmp/mt',exist_ok=True)
with ThreadPoolExecutor(16) as ex: oks=list(ex.map(valid,chosen))
print('mihomo invalid',oks.count(False))
chosen=[c for c,o in zip(chosen,oks) if o][:LIMIT]
print('chosen',len(chosen))
# 多线程重命名：ip-api batch 并发
S=requests.Session(); S.trust_env=False
ipl=sorted({ip for _,ip in chosen})
def look(chunk):
    for a in range(5):
        try:
            r=S.post('http://ip-api.com/batch',json=[{'query':x,'fields':FIELDS} for x in chunk],timeout=30)
            return r.json()
        except Exception: time.sleep(4)
    return []
geo={}
with ThreadPoolExecutor(4) as ex:
    for data in ex.map(look,[ipl[j:j+100] for j in range(0,len(ipl),100)]):
        for it in data:
            if it.get('status')=='success':
                geo[it['query']]=(it.get('countryCode') or 'XX',clean_org(it.get('org') or it.get('isp')) or '未知')
print('geo',len(geo),'/',len(ipl))
used=set(); proxies=[]
for p,ip in chosen:
    cc,org=geo.get(ip,('XX','未知'))
    base=f'{cc}+{org}'; n,k=base,2
    while n in used: n=f'{base} {k}'; k+=1
    used.add(n); p['name']=n; proxies.append(p)
proxies.sort(key=lambda p:p['name'])
tpl=yaml.safe_load(open(os.path.join(HERE,'tpl.yaml'),encoding='utf-8'))
tpl['proxies']=proxies
yaml.safe_dump(tpl,open(OUT,'w',encoding='utf-8'),allow_unicode=True,sort_keys=False)
print(Counter(p['name'][:2] for p in proxies).most_common(10))
