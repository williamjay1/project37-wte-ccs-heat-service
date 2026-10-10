"""Vector thermal-construction and budget figure from computed ledgers only."""
from pathlib import Path
import json
import sys
import hashlib
import argparse

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
from project37_figure_style import apply_house_style, save, panel_label, audit, mm
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-root', type=Path, default=ROOT)
parser.add_argument('--output-dir', type=Path, default=ROOT / 'results/figures/nature_r42_20261011')
args = parser.parse_args()
ROOT = args.data_root.resolve()
plt = apply_house_style(fontsize=10.)
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
thermal = json.loads((ROOT / 'results/finite_heat_path_audit_20261011.json').read_text())['representative']
decisions = json.loads((ROOT / 'results/finite_path_decision_budget_audit_20261011.json').read_text())
data = pd.read_csv(ROOT / 'results/finite_path_decision_budget_20261011.csv')

fig, axes = plt.subplots(1, 2, figsize=(mm(174), mm(90)), gridspec_kw={'width_ratios':[1.,1.05]})
fig.subplots_adjust(left=.19, right=.99, bottom=.23, top=.78, wspace=.38)
for ax, lab in zip(axes, ['a', 'b']):
    ax.text(-.12, 1.04, lab, transform=ax.transAxes, fontsize=10.,
            weight='bold', va='bottom', ha='left')
    ax.spines[['top','right']].set_visible(False)
    ax.tick_params(which='both', direction='out', top=False, right=False)
a,b = axes
names = ['Heat pump', 'Steam: latent', 'Steam: liquid', 'Overhead: plateau', 'Overhead: sensible', 'Compression']
q = [thermal['heat_pump_delivered_MW']] + [thermal['delivered_by_branch_MW'][k] for k in
     ['steam_latent','steam_liquid','overhead_plateau','overhead_sensible','compressor_sensible']]
colors = ['#0072B2','#555555','#999999','#E69F00','#F0C66D','#009E73']
y = np.arange(len(names))
a.barh(y, q, color=colors, height=.58, edgecolor='none')
for pos,val in enumerate(q):
    a.text(val+.35,pos,f'{val:.3f}',va='center',ha='left',fontsize=9.)
a.set(yticks=y,yticklabels=names,xlim=(0,22),xticks=[0,5,10,15,20],
      xlabel='Delivered branch heat (MW)',ylim=(5.8,-.8))
a.text(0,1.15,'Declared 36.5 MW path',transform=a.transAxes,fontsize=10.,weight='bold')
a.text(0,1.02,'Primary 100/60°C; customer 80/50°C',transform=a.transAxes,fontsize=9.)
a.text(0,-.25,'217.5 kg s$^{-1}$; no booster\nDeclared profiles, not hardware',
       transform=a.transAxes,fontsize=9.,va='top',linespacing=1.5)

value = np.linspace(200,600,81)
subset = data[(data.hours_SCENARIO==8000) & (data.electricity_EF_kg_MWh_SCENARIO==179)
              & (data.chain_burden_kg_t_SCENARIO==50) & (data.fossil_share_SCENARIO==.4)
              & (data.electricity_price_EUR2020_MWh_SCENARIO==70)]
plot_rows=[]
for baseline,color,ls,marker,label in [('noCCS120','#0072B2','-','o','No CCS, primary 120°C'),
                                      ('95adapted100','#D55E00','--','s','95% capture, primary 100°C')]:
    central=next(r for r in decisions['central_rows'] if r['comparator']==baseline
                 and r['effective_fossil_value_EUR2020_t_SCENARIO']==300)
    zeros=subset[subset.comparator==baseline].zero_remaining_budget_value_EUR2020_t
    lower=value-zeros.max();upper=value-zeros.min()
    line=value-central['zero_remaining_budget_value_EUR2020_t']
    b.fill_between(value,lower,upper,color=color,alpha=.14,lw=0)
    b.plot(value,line,color=color,ls=ls,lw=1.4,marker=marker,markevery=16,ms=3.4,label=label)
    plot_rows.extend(dict(comparator=baseline,effective_value_EUR2020_t=float(x),
                         central_remaining_per_retained_t=float(z),
                         prescribed_lower=float(lo),prescribed_upper=float(hi))
                     for x,z,lo,hi in zip(value,line,lower,upper))
b.axhline(0,color='black',lw=.8,ls=':')
b.set(xlim=(200,600),xticks=[200,300,400,500,600],ylim=(-310,220),yticks=[-300,-200,-100,0,100,200],
      xlabel='Effective fossil value (EUR2020 t$^{-1}$)',
      ylabel='Budget / retained fossil CO$_2$\n(EUR2020 t$^{-1}$)')
b.legend(loc='lower left',bbox_to_anchor=(-.02,1.12),fontsize=9.,frameon=False,
         borderaxespad=0,handlelength=2.3,labelspacing=.5)
b.text(0,-.25,'Capture fixed-cost stress deducted\nShading: pump / auxiliary scenarios',
       transform=b.transAxes,fontsize=9.,va='top',linespacing=1.5)
preflight=audit(fig,max_width_mm=183)
assert preflight['ok'],preflight
exports=save(fig,str(OUT/'Fig3_finite_path_decision'),dpi=1200)
fig.savefig(OUT/'Fig3_finite_path_decision_preview.png',dpi=180,bbox_inches='tight')
pd.DataFrame({'branch':names,'delivered_MW':q}).to_csv(OUT/'Fig3_panel_a_data.csv',index=False)
pd.DataFrame(plot_rows).to_csv(OUT/'Fig3_panel_b_data.csv',index=False)
report=dict(preflight=preflight,exports=exports,raster_dpi=1200,
            inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                [ROOT/'results/finite_heat_path_audit_20261011.json',ROOT/'results/finite_path_decision_budget_audit_20261011.json']},
            interpretation='Conditional construction and non-cancelling cost stress; shading is not probability/confidence or a complete cost interval.')
(OUT/'figure_audit.json').write_text(json.dumps(report,indent=2,default=lambda x:x.item()),encoding='utf-8')
print(json.dumps(report,indent=2,default=lambda x:x.item()))
