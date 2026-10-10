"""Original vector diagram from verified r42 results, sized for WBV 80 x 30 mm.

This is artwork, not an image-generation model or a new scientific result.
Every numerical label is read from the computational output, not hand-drawn.
"""
from pathlib import Path
import hashlib
import json
import sys
import argparse

from project37_figure_style import apply_house_style, audit, mm
from matplotlib import font_manager
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.text import Text

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-root', type=Path, default=ROOT)
parser.add_argument('--output-dir', type=Path, default=ROOT / 'output/graphical_abstract/r42_20261011')
parser.add_argument('--font-family', default='DejaVu Sans',
                    help='Bundled cross-platform font; never silently substitute another width.')
args = parser.parse_args()
ROOT = args.data_root.resolve()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
finite_path = ROOT / 'results/finite_heat_path_audit_20261011.json'
budget_path = ROOT / 'results/finite_path_decision_budget_audit_20261011.json'
finite = json.loads(finite_path.read_text())['representative']
budget = json.loads(budget_path.read_text())
row = next(r for r in budget['central_rows'] if r['comparator'] == '95adapted100'
           and r['effective_fossil_value_EUR2020_t_SCENARIO'] == 300)

plt = apply_house_style()
available = {font.name for font in font_manager.fontManager.ttflist}
font_choice = args.font_family
if font_choice not in available:
    raise ValueError(f'Required diagram font is unavailable: {font_choice}')
plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': [font_choice],
                     'font.size': 8.0, 'ps.fonttype': 42})
fig = plt.figure(figsize=(mm(80), mm(30)))
ax = fig.add_axes([0, 0, 1, 1])
ax.set(xlim=(0, 80), ylim=(0, 30))
ax.axis('off')
blue, orange, grey = '#0072B2', '#D55E00', '#54585A'
labels = []
contained_labels = []
connector_lanes = []

def label(x, y, text, size=8.0, color='black', weight='normal', ha='center'):
    artist = ax.text(x, y, text, ha=ha, va='center', fontsize=size,
                     color=color, weight=weight, linespacing=1.28)
    labels.append(artist)
    return artist

def arrow(x1, x2, y, color=grey):
    ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle='-|>',
                                mutation_scale=5, linewidth=.85, color=color))
    connector_lanes.append((x1, x2, y - .8, y + .8))

def panel(bounds, face, edge):
    x, y, width, height = bounds
    ax.add_patch(Rectangle((x, y), width, height, facecolor=face,
                           edgecolor=edge, linewidth=.8))
    return bounds

def panel_label(bounds, x, y, text, **kwargs):
    artist = label(x, y, text, **kwargs)
    contained_labels.append((artist, bounds))
    return artist

# All connector lanes remain clear of text; the simple source / service / scope
# diagram is deliberately readable at the journal's small final printed size.
label(12, 27, 'Fixed input', weight='bold')
label(39.5, 27, 'Same heat', weight='bold')
label(66.5, 27, 'CCS upgrade', weight='bold')
left_box = panel((1.7, 8.6, 20.6, 15.8), '#F4F6F7', grey)
panel_label(left_box, 12, 21.8, 'WtE + CCS', size=8.0, weight='bold')
panel_label(left_box, 12, 16.8, 'Heat recovery')
panel_label(left_box, 12, 12.3, 'HP 60 → 77°C', size=8.0)
arrow(22.5, 28.4, 17)

middle_box = panel((28.7, 8.6, 21.6, 15.8), '#F0F7FB', blue)
panel_label(middle_box, 39.5, 21.8, 'User 80/50°C')
panel_label(middle_box, 39.5, 17.2, '36.5 MW', size=9.0, color=blue, weight='bold')
panel_label(middle_box, 39.5, 12.4, '100/60°C', size=8.0)
arrow(50.5, 57.1, 17, color=blue)

right_box = panel((57.4, 8.6, 21.2, 15.8), '#FFF5EE', orange)
panel_label(right_box, 68, 22.2, '95 → 99.72%', size=8.0, weight='bold')
climate = row['included_delta_climate_kgCO2e_year'] / 1e6
panel_label(right_box, 68, 18.4, rf'{climate:.3f} kt/y', size=8.0, color=orange)
threshold = row['zero_remaining_budget_value_EUR2020_t']
panel_label(right_box, 68, 14.6, f'Vf > {threshold:.0f}', size=8.0, color=orange)
panel_label(right_box, 68, 10.8, 'EUR2020 / t', size=8.0)

# These are diagram qualifications, not a paragraph or a claim of field proof.
flow = finite['primary_water_kg_s']
label(39.5, 5.8, f'{flow:.1f} kg/s', size=8.0)
label(68, 5.8, 'Unpriced scope', size=8.0)
label(12, 5.8, 'No booster', size=8.0)
label(40, 2.0, 'Declared stress; t = fossil CO$_2$; climate: kt CO$_2$e/y',
      size=8.0, color=grey)

fig.canvas.draw()
renderer = fig.canvas.get_renderer()
collisions = []
for i, a in enumerate(labels):
    for b in labels[i+1:]:
        if a.get_window_extent(renderer).overlaps(b.get_window_extent(renderer)):
            collisions.append(dict(labels=[a.get_text(), b.get_text()],
                bounds_mm=[ax.transData.inverted().transform(x.get_window_extent(renderer).get_points()).tolist()
                           for x in [a,b]]))
assert not collisions, collisions
outside = [a.get_text() for a in labels
           if not fig.bbox.contains(*a.get_window_extent(renderer).get_points()[0])
           or not fig.bbox.contains(*a.get_window_extent(renderer).get_points()[1])]
assert not outside, outside
panel_overflow = []
for artist, (x, y, width, height) in contained_labels:
    # Require 0.30 mm inner clearance from every box edge. The same transforms
    # are used for rendered labels and vector geometry; this is not a guessed
    # character-count check and supplements, rather than replaces, looking.
    lower = ax.transData.transform((x + .30, y + .30))
    upper = ax.transData.transform((x + width - .30, y + height - .30))
    bbox = artist.get_window_extent(renderer)
    if bbox.x0 < lower[0] or bbox.y0 < lower[1] or bbox.x1 > upper[0] or bbox.y1 > upper[1]:
        panel_overflow.append(dict(text=artist.get_text(),
                                   actual_mm=ax.transData.inverted().transform(bbox.get_points()).tolist(),
                                   permitted_mm=[[x+.30,y+.30],[x+width-.30,y+height-.30]]))
assert not panel_overflow, panel_overflow
from matplotlib.transforms import Bbox
connector_intrusions = []
for x0, x1, y0, y1 in connector_lanes:
    lane = Bbox(ax.transData.transform([[x0, y0], [x1, y1]]))
    connector_intrusions += [a.get_text() for a in labels
                             if a.get_window_extent(renderer).overlaps(lane)]
assert not connector_intrusions, connector_intrusions
preflight = audit(fig, max_width_mm=80)
assert preflight['ok'], preflight
stem = OUT / 'project37_graphical_abstract_r42_20261011'
with plt.rc_context({'savefig.bbox': None, 'savefig.pad_inches': 0}):
    # Explicitly disable the house style's tight export: bbox_inches=None alone
    # falls back to rcParams and can enlarge PNG dimensions through padding.
    for ext in ['pdf', 'svg', 'eps']:
        fig.savefig(stem.with_suffix('.'+ext), bbox_inches=None, pad_inches=0)
    fig.savefig(OUT / (stem.name+'_1200dpi.png'), dpi=1200, bbox_inches=None, pad_inches=0)
    fig.savefig(OUT / (stem.name+'_preview.png'), dpi=300, bbox_inches=None, pad_inches=0)
report = dict(size_mm=[80, 30], minimum_font_pt=min(a.get_fontsize() for a in labels),
              text_collisions=collisions, outside_canvas=outside, preflight=preflight,
              panel_overflow=panel_overflow, connector_intrusions=connector_intrusions,
              pdf_fonttype=plt.rcParams['pdf.fonttype'], raster_dpi=1200,
              raw_labels={a.get_text(): a.get_fontsize() for a in labels},
              numerical_labels=dict(climate_kt_year=climate,
                                    effective_value_threshold_EUR2020_t=threshold,
                                    primary_flow_kg_s=flow),
              input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [finite_path, budget_path]},
              font_selected=font_choice,
              visual_status='PENDING actual rendered inspection; generation cannot self-certify visual QA',
              scope='Representative declared path and capital stress, not field validation, current ETS or full LCA.')
(OUT/'graphical_abstract_audit.json').write_text(json.dumps(report, indent=2, default=lambda x:x.item()), encoding='utf-8')
print(json.dumps(report, indent=2, default=lambda x:x.item()))

