"""Portable cleaning of the frozen owner CC0 monthly CSV, not demand inference."""
from pathlib import Path
from datetime import date
import calendar,csv,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'datasets/hagenholz_operator_raw_cc0_20261002.csv'
EXPECTED='fae845b7ecf2a5fd6e78ef9be453e0b99491e73a925c2b036bf1bdaa67546966'

def main():
 assert hashlib.sha256(RAW.read_bytes()).hexdigest()==EXPECTED
 with RAW.open(encoding='utf-8-sig',newline='') as f: raw=list(csv.DictReader(f))
 rows=[];seen=set()
 fields={'Kehrichtdurchsatz':'waste_t','Waermeabsatz':'heat_sales_MWh','Stromproduktion':'gross_electric_MWh','Stromabsatz':'electric_sales_MWh'}
 for r in raw:
  y,m=int(r['Jahr']),int(r['Monat_num']);assert (y,m) not in seen;seen.add((y,m))
  assert r['Monat']==f'{y}-{m:02d}' and r['Monatsende']==date(y,m,calendar.monthrange(y,m)[1]).isoformat()
  z=dict(year=y,month=m,calendar_hours=24*calendar.monthrange(y,m)[1])
  for original,new in fields.items():
   assert r[original].strip();z[new]=float(r[original]);assert z[new]>=0
  assert z['gross_electric_MWh']>=z['electric_sales_MWh']
  z['gross_minus_sales_MWh']=z['gross_electric_MWh']-z['electric_sales_MWh']
  z['heat_sales_monthly_mean_MW']=z['heat_sales_MWh']/z['calendar_hours']
  rows.append(z)
 rows.sort(key=lambda r:(r['year'],r['month']))
 assert len(rows)==80 and (rows[0]['year'],rows[0]['month'])==(2020,1) and (rows[-1]['year'],rows[-1]['month'])==(2026,8)
 for a,b in zip(rows,rows[1:]):assert 12*b['year']+b['month']-12*a['year']-a['month']==1
 out=ROOT/'datasets/hagenholz_monthly_clean_r35_20261002.csv'
 with out.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 sha=hashlib.sha256(out.read_bytes()).hexdigest()
 assert sha=='c483dbfb654537bb4534f540b39f4e2c3e6bdc1a2773f34ed1396c2daafc81ea'
 receipt=dict(status='PASS actual raw-to-clean CSV computation',rows=80,raw_sha256=EXPECTED,clean_sha256=sha,
  license='Owner-published CC0',scope='Monthly exports/generation, Switzerland nonEU. Difference gross-minus-sales is not isolated internal demand. Incomplete2026 excluded from annual cuts.')
 (ROOT/'results/monthly_cc0_clean_reproduction_r35_20261002.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
