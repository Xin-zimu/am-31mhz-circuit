from pathlib import Path
import requests,json,concurrent.futures,re
ROOT=Path(__file__).resolve().parent/'evidence'
URLS=['https://e.tb.cn/h.jmaEgGlFwt4RKjR?tk=ZdCI6VupCiM','https://e.tb.cn/h.j9tnacrWSiFsHFK?tk=YigD6VupUVS','https://e.tb.cn/h.j9tnWMoiVozjd0M?tk=9v606Vupx4E','https://e.tb.cn/h.jlh3IcQiUBAW6mp?tk=3HcM6VuKwII']
def get(pair):
 i,u=pair
 try:
  r=requests.get(u,timeout=20)
  (ROOT/f'taobao_{i}.html').write_bytes(r.content)
  return dict(index=i,url=u,final_url=r.url,status=r.status_code,title=re.findall(r'<title>(.*?)</title>',r.text,re.S),bytes=len(r.content))
 except Exception as e:return dict(index=i,url=u,error=str(e))
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(get,enumerate(URLS,1)))
 (ROOT/'taobao_access.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(rows,ensure_ascii=False,indent=2))
