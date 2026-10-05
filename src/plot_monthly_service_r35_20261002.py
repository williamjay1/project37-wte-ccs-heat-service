"""Vector figure: observed normalized export shapes, scenario upper cuts."""
from pathlib import Path
import os,csv,json
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'cache/matplotlib_r35'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42,'ps.fonttype':42})

def main():
 with (ROOT/'datasets/hagenholz_monthly_clean_r35_20261002.csv').open(encoding='utf-8') as f:data=list(csv.DictReader(f))
 with (ROOT/'results/swiss_monthly_service_cuts_r35_20261002.csv').open(encoding='utf-8') as f:cuts=list(csv.DictReader(f))
 fig,axes=plt.subplots(1,2,figsize=(7.0,3.05),gridspec_kw={'width_ratios':[1.05,1]})
 colors=plt.get_cmap('viridis')
 for k,year in enumerate(range(2020,2026)):
  rows=[r for r in data if int(r['year'])==year]
  mean=sum(float(r['heat_sales_MWh']) for r in rows)/sum(float(r['calendar_hours']) for r in rows)
  axes[0].plot(range(1,13),[float(r['heat_sales_MWh'])/float(r['calendar_hours'])/mean for r in rows],label=str(year),color=colors(k/5),linewidth=1.25)
 axes[0].set(xlabel='Calendar month',ylabel='Monthly sales / calendar-year mean',xticks=[1,3,5,7,9,11],ylim=(.25,1.8))
 axes[0].axhline(1,color='gray',lw=.6,ls=':')
 axes[0].legend(ncol=3,fontsize=7,frameon=False,loc='lower left',columnspacing=.6)
 groups=[(95,0,'95°C\nno CCS'),(95,.99,'95°C\n99% CCS'),(100,0,'100°C\nno CCS'),(100,.99,'100°C\n99% CCS')]
 ledger=[]
 for x,(ts,cap,label) in enumerate(groups):
  for model,offset,color,marker in [('rectangular_inlet_grade',-.12,'#b66b38','o'),('condensation_cut',.12,'#235c82','s')]:
   z=[float(r['necessary_mean_service_ceiling_MW']) for r in cuts if int(r['supply_SCENARIO_C'])==ts and float(r['capture_fraction'])==cap and r['thermal_model']==model and r['volume_SCENARIO_m3']=='0' and r['feed_timing_SCENARIO']=='observed_monthly_throughput_shape']
   lo,hi=min(z),max(z)
   axes[1].plot([x+offset,x+offset],[lo,hi],color=color,lw=3)
   axes[1].scatter([x+offset]*2,[lo,hi],marker=marker,color=color,s=18,zorder=4)
   ledger.append(dict(supply=ts,capture=cap,model=model,min_MW=lo,max_MW=hi))
 axes[1].plot([],[],color='#b66b38',lw=3,label='Inlet-grade screen')
 axes[1].plot([],[],color='#235c82',lw=3,label='Condensation cut')
 axes[1].set(xticks=range(4),xticklabels=[g[2] for g in groups],ylabel='Necessary annual-mean ceiling (MW)',ylim=(25,71))
 axes[1].legend(fontsize=7,frameon=False,loc='upper right')
 for ax in axes:
  ax.spines[['top','right']].set_visible(False)
  ax.tick_params(labelsize=8)
 axes[0].set_title('(a) Observed export shapes',loc='left',fontsize=10)
 axes[1].set_title('(b) Specified no-boost route',loc='left',fontsize=10)
 fig.tight_layout(pad=.7,w_pad=1.2)
 folder=ROOT/'results/figures';folder.mkdir(exist_ok=True)
 fig.savefig(folder/'monthly_service_r35.pdf');fig.savefig(folder/'monthly_service_r35.png',dpi=300);plt.close(fig)
 (ROOT/'results/monthly_service_figure_values_r35_20261002.json').write_text(json.dumps(ledger,indent=2),encoding='utf-8')
 print(json.dumps(ledger,indent=2))
if __name__=='__main__':main()
