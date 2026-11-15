"""Bounded retrieval of observed ADI links; no URL guessing or third-party model."""
from pathlib import Path
import urllib.request, urllib.error, json, hashlib, datetime, re, html
ROOT=Path(__file__).resolve().parents[1]
records=[]
class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        chain.append(dict(status=code,source=req.full_url,target=newurl))
        return super().redirect_request(req,fp,code,msg,headers,newurl)
opener=urllib.request.build_opener(Redirects)
def get(url,name):
    global chain
    chain=[]
    rec=dict(url=url,date='2026-11-15',time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        response=opener.open(url,timeout=35)
    except urllib.error.HTTPError as e:response=e
    except Exception as e:
        rec.update(error=str(e),status=None,content_type=None,bytes=0,redirects=chain)
        records.append(rec);return ''
    with response:
        data=response.read();typ=response.headers.get('Content-Type','')
        rec.update(status=response.code,final_url=response.geturl(),content_type=typ,bytes=len(data),redirects=chain,
                   sha256=hashlib.sha256(data).hexdigest())
    # Save failed response bodies as evidence, never with a .cir extension.
    model=bool(re.search(rb'(?im)^\s*\.subckt\s+\S+',data)) and 'html' not in typ.lower() and rec['status']==200
    rec['valid_model_candidate']=model
    dest=ROOT/'sources'/('AD835_OFFICIAL_ORIGINAL.cir' if model else name)
    dest.write_bytes(data);rec['saved_as']=dest.name;records.append(rec)
    print(json.dumps(rec),flush=True)
    return data.decode('utf8',errors='replace')
product=get('https://www.analog.com/en/products/ad835.html','product.html')
license_url='https://www.analog.com/en/license/spice-models.html?mediaPath=/media/en/simulation-models/spice-models/ad835.cir&modelType=spice-models'
license_text=get(license_url,'license.html')
text=html.unescape(license_text)
match=re.search(r"location.href\s*=\s*'([^']*ad835\.cir[^']*)'",text,re.I)
get('https://www.analog.com/media/en/simulation-models/spice-models/ad835.cir','model_entry_response.bin')
if match:
    target=urllib.parse.urljoin(license_url,match[1]);get(target,'accept_download_response.bin')
get('https://ez.analog.com/other-products/a/documents/c/questions/DO22920/ad835-related','official_support_related.html')
get('https://ez.analog.com/other-products/a/documents/c/questions/DO22950/ad835-spice-model','official_support_model.html')
(ROOT/'sources/http_records.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print('STOP: bounded official-link inspection complete. Model obtained:',any(x.get('valid_model_candidate') for x in records))
