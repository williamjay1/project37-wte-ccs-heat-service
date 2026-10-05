"""Vector figures drawn from actual r32 outputs, no generated evidence."""
from pathlib import Path
import os,csv,json
ROOT=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(ROOT/'cache/matplotlib_r32')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
OUT=ROOT/'results'
def save(fig,name):
    fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight')
    fig.savefig(OUT/(name+'.png'),dpi=900,bbox_inches='tight')
    plt.close(fig)
def cap(ts,flow,base):
    scale=1 if base==18.5 else (38.0-19.9)/(5.3+1.6+9.8*5.5/4.5)
    ss=[(base,390),(5.3*scale,91),(1.6*scale,158),(9.8*5.5/4.5*scale,77)]
    values=[sum(q for q,t in ss),flow*.00418*(ts-60)]
    for t in {t for q,t in ss if t<ts}:
        a=(t-60)/(ts-60);values.append(sum(q for q,temp in ss if temp>t)/(1-a))
    return min(values)
def main():
    ts=np.linspace(80,140,241);flow=np.linspace(100,500,241)
    cat=np.empty((len(flow),len(ts)))
    for j,m in enumerate(flow):
      for i,t in enumerate(ts):
        agg=37.37777777777778>=36.5 and m*.00418*(t-60)>=36.5
        a=cap(t,m,18.5)>=36.5 and t>=85
        b=cap(t,m,19.9)>=36.5 and t>=85
        cat[j,i]=3 if a else 2 if b else 1 if agg and t>=85 else 0
    from matplotlib.colors import ListedColormap
    fig,ax=plt.subplots(figsize=(6.8,3.6),layout='constrained')
    cm=ListedColormap(['#f3f3f3','#f2c4b5','#c0d5ea','#70b493'])
    # Filled categorical polygons avoid PDF-viewer seams between vector cells.
    ax.contourf(ts,flow,cat,levels=[-.5,.5,1.5,2.5,3.5],colors=cm.colors,antialiased=False)
    ax.plot(ts,36.5/(.00418*(ts-60)),color='#444444',lw=1.1,label='Minimum primary flow')
    ax.axhline(150,color='#555555',ls='--',lw=.9)
    ax.axvline(115.9009009,color='#245a3f',lw=1)
    ax.scatter([100,120],[218.3014354,150],color='black',s=18,zorder=5)
    ax.annotate('99.72% design cut: 115.90°C',(115.9,410),xytext=(83,455),fontsize=9,
                arrowprops=dict(arrowstyle='->',lw=.8))
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=cm(3),label='Both capture designs pass'),
        Patch(facecolor=cm(2),label='95% design only passes'),Patch(facecolor=cm(1),label='Aggregate-only pass'),
        Patch(facecolor=cm(0),label='Service/flow rejection')],loc='upper right',frameon=True,fontsize=9)
    ax.set(xlabel='Primary supply temperature (°C); return 60°C',ylabel='Primary flow limit (kg/s)',ylim=(100,500),xlim=(80,140))
    save(fig,'figure_service_domain_r32_20261002')
    annual=list(csv.DictReader((OUT/'physical_service_annual_matrix_r32_20261002.csv').open(encoding='utf-8')))
    small=list(csv.DictReader((OUT/'physical_service_followup_smallstore_r32_20261002.csv').open(encoding='utf-8')))
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.5),layout='constrained')
    summaries=[]
    for ax,region,title in zip(axes,['Oberland','Porto metropolitan area'],['(a) Oberland proxy','(b) Porto proxy']):
        vals=[]
        for size in [0,5000,50000]:
            data=small if size==5000 else annual
            arr=[]
            for capture,model in [('False','temperature_cascade'),('True','aggregate_heat'),('True','temperature_cascade')]:
                item=next(r for r in data if r['proxy']==region and r['supply_temperature_C']=='120' and r['capture_on']==capture and r['model']==model and (size==5000 or (r['mean_duty_ratio_SCENARIO']=='0.3' and float(r['storage_usable_capacity_MWh'])==(0 if size==0 else 2037.75))))
                arr.append(float(item['unserved_MWh']))
            vals.append(arr)
        a=np.asarray(vals);summaries.append(dict(proxy=region,unserved_matrix_MWh=a.tolist()))
        for k,(label,color) in enumerate(zip(['No CCS, graded','CCS, aggregate','CCS, graded'],['#888888','#6c96be','#c5644e'])):
            ax.bar(np.arange(3)+(k-1)*.23,a[:,k],.22,label=label,color=color)
        ax.set_xticks(np.arange(3),['None','5000 m³','50000 m³']);ax.set_ylabel('Unserved heat (MWh/proxy cycle)')
        ax.set_title(title,loc='left',fontsize=9)
        if region=='Oberland':
            ax.set_ylim(0,3.15);ax.annotate(f'{a[0,2]:.3f}',(.23,a[0,2]),xytext=(.25,2.96),fontsize=8)
        ax.set_xlabel('Finite tank; primary 120/60°C')
    axes[1].legend(fontsize=9,frameon=False,loc='upper right')
    save(fig,'figure_annual_service_r32_20261002')
    margin=json.loads((OUT/'physical_service_adaptation_boundary_qc_r32_20261002.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.7),layout='constrained')
    for label,color,row in zip(['Same 99.72% train, bypass','Published 95% design'],['#207454','#3869a0'],margin['central_rows']):
        dc=row['extra_capture_t_y'];dr=row['extra_retained_fossil_t_y'];pe=70
        dp=(row['marginal_climate_fossil_share_threshold']*1000*(dr/.4)-50*dc)/179
        v=np.linspace(0,600,121)
        axes[0].plot(v,(v*dr-pe*dp-50*dc)/1e6,color=color,label=label)
        axes[0].fill_between(v,(v*dr-pe*(dp+.5*8000)-50*dc)/1e6,(v*dr-pe*dp-50*dc)/1e6,color=color,alpha=.12)
        ef=np.linspace(0,750,101)
        for pump,ls in [(0,'-'),(.5,'--')]:
            axes[1].plot(ef,100*((dp+8000*pump)*ef+dc*50)/(1000*(dr/.4)),color=color,ls=ls)
    axes[0].axhline(0,color='black',lw=.7);axes[0].set(xlabel='Effective fossil carbon value (EUR2020/t)',ylabel='Adaptation-cost ceiling (million EUR2020/y)',title='(a) Conditional operating margin')
    axes[1].axhline(40,color='gray',ls=':',lw=1);axes[1].set(xlabel='Electricity burden (kg CO₂e/MWh)',ylabel='Marginal fossil-share threshold (%)',title='(b) Climate sensitivity')
    axes[0].legend(fontsize=9,frameon=False)
    axes[1].text(.03,.97,'Solid: no extra pump\nDashed: +0.5 MW pump\nDotted: 40% fossil share',transform=axes[1].transAxes,va='top',fontsize=9)
    save(fig,'figure_adaptation_ceiling_r32_20261002')
    record=dict(status='Figures drawn from actual frozen r32 outputs',annual_values=summaries,
        warning='Necessary optimistic domains; no certified attainability or actual investment profit',vector_PDFs=3)
    (OUT/'figure_physical_service_qc_r32_20261002.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()
