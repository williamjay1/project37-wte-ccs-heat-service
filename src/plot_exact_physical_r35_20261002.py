"""Regenerate the three main service/value figures from IF97 re-runs."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'src/plot_physical_service_r32_20261002.py').read_text(encoding='utf-8')
source=source.replace('import numpy as np','import numpy as np\nfrom functools import lru_cache\nfrom exact_water_comparison_r35_20261002 import water as uncached_water\nwater=lru_cache(maxsize=None)(uncached_water)')
source=source.replace('flow*.00418*(ts-60)','flow*(water(ts)-water(60))')
source=source.replace('a=(t-60)/(ts-60)','a=(water(t)-water(60))/(water(ts)-water(60))')
source=source.replace('m*.00418*(t-60)','m*(water(t)-water(60))')
source=source.replace("ax.plot(ts,36.5/(.00418*(ts-60)),", "ax.plot(ts,[36.5/(water(t)-water(60)) for t in ts],")
source=source.replace('115.9009009','115.660935466').replace('218.3014354','217.525042353').replace('115.90°C','115.66°C').replace('(115.9,410)','(115.66,410)')
source=source.replace('physical_service_annual_matrix_r32_20261002.csv','exact_water_annual_r35_20261002.csv')
source=source.replace('physical_service_followup_smallstore_r32_20261002.csv','exact_water_smallstore_r35_20261002.csv')
source=source.replace("float(r['storage_usable_capacity_MWh'])==(0 if size==0 else 2037.75)","r['tank']==('no_store' if size==0 else '141b Large TTES')")
source=source.replace("ax.set_ylim(0,3.15)","ax.set_ylim(0,3.6)").replace("xytext=(.25,2.96)","xytext=(.25,3.28)")
old="margin=json.loads((OUT/'physical_service_adaptation_boundary_qc_r32_20261002.json').read_text())"
new="all_rows=list(csv.DictReader((OUT/'exact_water_adaptation_r35_20261002.csv').open(encoding='utf-8')))\n    margin={'central_rows':[ {k:float(v) if k in ['extra_capture_t_y','extra_retained_fossil_t_y','marginal_climate_fossil_share_threshold'] else v for k,v in next(r for r in all_rows if r['comparator']==comp and r['hours_SCENARIO']=='8000' and r['electricity_EF_kg_MWh_SCENARIO']=='179' and r['incremental_chain_burden_kg_t_SCENARIO']=='50' and r['incremental_network_pumping_MW_SCENARIO']=='0' and r['fossil_share_SCENARIO']=='0.4' and r['electricity_price_EUR_MWh_SCENARIO']=='70' and r['effective_fossil_value_EUR_t_SCENARIO']=='300').items()} for comp in ['same99_train_bypass','published95_design']]}"
assert old in source
source=source.replace(old,new)
for stem in ['figure_service_domain','figure_annual_service','figure_adaptation_ceiling','figure_physical_service_qc']:
 source=source.replace(stem+'_r32_20261002',stem+'_r35_20261002')
source=source.replace('Figures drawn from actual frozen r32 outputs','Figures drawn from actual IF97 r35 outputs')
exec(compile(source,'r35 exact-property vector plots','exec'),{'__file__':__file__,'__name__':'__main__'})
