"""Vector plots from actual phase calculations, not invented empirical data."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.8,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
obj=json.loads((ROOT/'results/steam_phase_domain_qc_r33_20261002.json').read_text())
b=obj['su_bracket'];fig,ax=plt.subplots(1,2,figsize=(6.9,3.0),layout='constrained')
x=np.arange(2);H=np.array([37.3,18.5]);width=.23
ax[0].bar(x-width,H,width,label='Published basic heat',color='#9da4ad')
ax[0].bar(x,H*b['latent_fraction_lower'],width,label='Conditional latent lower bound',color='#286a8e')
ax[0].bar(x+width,H*b['superheat_fraction_upper'],width,label='Superheat upper bound',color='#c96c45')
ax[0].set_xticks(x,['No CCS','99.72% CCS']);ax[0].set_ylabel('Steam-derived duty (MW)')
ax[0].set_ylim(0,44);ax[0].set_title('(a) Su steam-route bracket',loc='left',fontsize=10)
ax[0].legend(frameon=False,fontsize=8.8,loc='upper right')

from physical_service_caseB_check_r32_20261002 import CASES
from physical_service_caseB_envelope_r32_20261002 import heat_limit
approaches=np.linspace(0,10,501);curves=[];c=CASES[0]
import sys
sys.path.insert(0,str(ROOT/'cache/python_packages_r32'))
from iapws import IAPWS97
sat=IAPWS97(P=.12,x=1);hin=IAPWS97(P=.12,T=381.15);ret=IAPWS97(P=.1,T=328.15)
rho=(hin.h-sat.h)/(hin.h-ret.h);Tsat=sat.T-273.15
for hour in (8000,8760):
 for qi in (0,3.4):
  H=heat_limit(c,hour,0,qi)
  dh=IAPWS97(P=1,T=373.15).h-IAPWS97(P=1,T=328.15).h
  frac=np.array([max(0,(IAPWS97(P=1,T=373.15).h-IAPWS97(P=1,T=Tsat-a+273.15).h)/dh) for a in approaches])
  v=np.where(approaches<=Tsat-100,H,np.minimum(H,H*rho/np.maximum(frac,1e-12)))
  v=np.where(approaches<=8,v,0)
  curves.append(v)
ax[1].fill_between(approaches,np.min(curves,axis=0),np.max(curves,axis=0),color='#286a8e',alpha=.22,label='Condensation-curve envelope')
ax[1].plot(approaches,np.max(curves,axis=0),color='#286a8e',lw=1.2)
Hlo=heat_limit(c,8760,0,3.4);Hhi=heat_limit(c,8000,0,0)
ax[1].fill_between(approaches,np.where(approaches<=8,Hlo,0),np.where(approaches<=8,Hhi,0),color='#c96c45',alpha=.17,label='Inlet-temperature rectangle')
ax[1].axhline(64.4,color='#333333',ls='--',lw=1,label='Required source DH service')
ax[1].set(xlabel='Minimum approach (K)',ylabel='Necessary steam-only ceiling (MW)',xlim=(0,10),ylim=(0,110))
ax[1].set_title('(b) Hagenholz: 100/55°C service',loc='left',fontsize=10)
ax[1].text(5.7,101,'Inlet rectangle',color='#a95536',fontsize=8.8)
ax[1].text(5.8,37,'Condensing bound',color='#286a8e',fontsize=8.8)
ax[1].text(7.0,67,'DH demand',color='#333333',fontsize=8.8)
ax[1].text(5.3,73,'Only 3.216 K\nof superheat',fontsize=8.8)
folder=ROOT/'results/figures';folder.mkdir(exist_ok=True)
fig.savefig(folder/'physical_steam_phase_r33.pdf',bbox_inches='tight')
fig.savefig(folder/'physical_steam_phase_r33.png',dpi=450,bbox_inches='tight')
plt.close(fig)
print('Generated vector steam-phase figure from executed model outputs.')
