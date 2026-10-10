"""Plot verified audit outputs; Nature-class typography, not a journal claim."""
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
parser.add_argument('--output-dir', type=Path, default=ROOT / 'results/figures/nature_r41_20261011')
args = parser.parse_args()
ROOT = args.data_root.resolve()
plt = apply_house_style(fontsize=10.0)

BLUE, ORANGE, GREY = '#0072B2', '#D55E00', '#6B7280'
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
primary = json.loads((ROOT / 'results/primary_margin_audit_20261011.json').read_text())
steam = json.loads((ROOT / 'results/steam_composite_margin_20261011.json').read_text())
recovery = pd.read_csv(ROOT / 'results/recovery_composite_frontier_20261011.csv')
summary = json.loads((ROOT / 'results/recovery_composite_audit_20261011.json').read_text())

fig, axes = plt.subplots(1, 2, figsize=(mm(170), mm(92)))
fig.subplots_adjust(left=0.09, right=0.99, bottom=0.22, top=0.75, wspace=0.38)
a, b = axes
for ax, lab in zip(axes, ['a', 'b']):
    panel_label(ax, lab, pad=8)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.tick_params(which='both', direction='out', top=False, right=False)

curve = pd.read_csv(ROOT / 'results/primary_flow_curve_20261011.csv')
temps = curve['primary_supply_C'].to_numpy()
flows = curve['required_flow_kg_s'].to_numpy()
ts_upper = primary['primary_supply_max_C']
ts_steam = min(steam['supply_boundary_range_C'])
ts_lower = primary['primary_supply_min_at150_C']
a.plot(temps, flows, color=GREY, lw=1.4, label='Flow required for 36.5 MW')
a.axhline(150, color='black', lw=1.0, ls=':', label='Declared flow limit')
a.axvline(ts_upper, color=BLUE, lw=1.2, ls='--')
a.axvline(ts_steam, color=ORANGE, lw=1.2, ls='-.')
a.axvspan(ts_upper, ts_lower, color=BLUE, alpha=0.14, linewidth=0)
a.plot(ts_upper, primary['minimum_flow_for_necessary_window_kg_s'],
       'o', color=BLUE, ms=4, label='Rectangular recovery frontier')
a.plot(ts_steam, max(steam['minimum_necessary_flow_range_kg_s']),
       's', color=ORANGE, ms=4, label='Cold steam-domain endpoint')
a.set(xlim=(85, 125), ylim=(120, 360), xticks=[85,95,105,115,125],
      yticks=[150,200,250,300,350], xlabel='Primary supply temperature (°C)',
      ylabel='Required primary flow (kg s$^{-1}$)')
a.legend(loc='lower left', bbox_to_anchor=(-0.02, 1.13), fontsize=9.0,
         labelspacing=0.30, handlelength=2.1, borderaxespad=0)

x = np.linspace(0, 1, 41)
families = []
for s in summary['structural_summaries']:
    families.append(s['aggregate_at_fraction0_MW']
                    + x * (s['aggregate_at_fraction1_MW']-s['aggregate_at_fraction0_MW']))
families = np.array(families)
lower, upper = families.min(axis=0), families.max(axis=0)
b.axhspan(35.9, 36.5, color=ORANGE, alpha=0.10, linewidth=0)
b.fill_between(x, lower, upper, color=BLUE, alpha=0.18, linewidth=0,
               label='Declared steam / compression family')
b.plot(x, lower, color=BLUE, lw=1.4, ls='-', label='Lower usable-heat endpoint')
b.plot(x, upper, color=BLUE, lw=1.1, ls='--', label='Upper usable-heat endpoint')
b.axhline(36.5, color='black', lw=1, ls=':', label='Common heat service')
cross = summary['worst_aggregate_partition']['minimum_overhead_plateau_fraction_aggregate']
b.plot(cross, 36.5, 's', color=ORANGE, ms=4)
b.set(xlim=(0,1), ylim=(35.9,37.55), xticks=[0,.25,.5,.75,1],
      yticks=[36,36.5,37,37.5], xlabel='Declared overhead plateau duty fraction',
      ylabel='Heat usable above 60°C (MW)')
b.legend(loc='lower left', bbox_to_anchor=(-0.02, 1.13), fontsize=9.0,
         labelspacing=0.30, handlelength=2.1, borderaxespad=0)

preflight = audit(fig, max_width_mm=183)
assert preflight['ok'], preflight
paths = save(fig, str(OUT / 'Fig2_retrofit_frontier'), dpi=1200)
fig.savefig(OUT / 'Fig2_retrofit_frontier_preview.png', dpi=180, bbox_inches='tight')
# Source-bound export with no interpolation introduced into computed claims.
pd.DataFrame({'primary_supply_C': temps, 'required_flow_kg_s': flows}).to_csv(
    OUT / 'Fig2_panel_a_data.csv', index=False)
pd.DataFrame({'plateau_fraction':x,'usable_heat_lower_MW':lower,
              'usable_heat_upper_MW':upper}).to_csv(OUT / 'Fig2_panel_b_data.csv', index=False)
report = dict(preflight=preflight, exports=paths, raster_dpi=1200,
              inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [ROOT/'results/primary_margin_audit_20261011.json',
                                ROOT/'results/steam_composite_margin_20261011.json',
                                ROOT/'results/recovery_composite_audit_20261011.json']},
              limitations='Necessary / declared structural domains only, not statistical intervals or certified retrofits')
def serializable(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)
(OUT/'figure_audit.json').write_text(json.dumps(report,indent=2,default=serializable),encoding='utf-8')
print(json.dumps(report,indent=2,default=serializable))
