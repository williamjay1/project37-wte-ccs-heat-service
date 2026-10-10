"""Original vector service-certificate summary at WBV's 80 x 30 mm size.

Capacity brackets are recomputed by the scientific pipeline before drawing.
This diagram is not a new experiment, an exclusive priority claim, or a
jointly validated factory rating. The old central budget diagram is separate.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re

from project37_figure_style import apply_house_style, audit, mm
from matplotlib import font_manager
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.transforms import Bbox


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=root)
    parser.add_argument('--brackets-csv', type=Path, default=None)
    parser.add_argument('--output-dir', type=Path,
                        default=root/'output/graphical_abstract/r46_service_certificate_20261011')
    parser.add_argument('--font-family', default='DejaVu Sans')
    args = parser.parse_args()
    root = args.data_root.resolve()
    brackets_path = (args.brackets_csv or root/'results/continuum_outer_r46/continuum_inner_outer_brackets_r46_20261011.csv').resolve()
    finite_path = root/'results/finite_heat_path_audit_20261011.json'
    rows = list(csv.DictReader(brackets_path.open(newline='', encoding='utf-8')))
    nominal = [r for r in rows if float(r['retained_duty_DECLARED']) == 1.0
               and float(r['common_grid_step_K']) == .05]
    assert len(nominal) == 2
    cases = {float(r['capture_percent']): r for r in nominal}
    assert set(cases) == {95.0, 99.72}
    finite_document = json.loads(finite_path.read_text(encoding='utf-8'))
    finite = finite_document['representative']
    # Numerical service attributes are taken from the constructed-path record.
    service_definition = finite_document['fixed_secondary_service']
    service_match = re.search(r'([\d.]+) MW at\s*([\d.]+)/([\d.]+) C', service_definition)
    assert service_match, service_definition
    contract, user_supply, user_return = map(float, service_match.groups())
    hp_match = re.match(r'([\d.]+) -> ([\d.]+) C water', finite['heat_pump_anchor'])
    assert hp_match, finite['heat_pump_anchor']
    hp_inlet, hp_outlet = map(float, hp_match.groups())
    loop_supply = float(finite['primary_supply_C'])
    loop_return = float(finite['primary_return_C'])
    inputs = [brackets_path, finite_path]
    numbers = {}
    for capture, r in cases.items():
        lower = float(r['finite_constructed_lower_MW'])
        upper = float(r['continuum_necessary_upper_MW'])
        cut = float(r['continuum_witness_grade_C'])
        assert lower <= upper
        assert abs(float(r['target_retained_fraction_sufficient'])*lower - contract) < 1e-9
        numbers[str(capture)] = dict(capture_percent=capture,
                                    constructed_lower_MW=lower,
                                    necessary_outer_MW=upper,
                                    witness_grade_C=cut)
    assert numbers['95.0']['constructed_lower_MW'] > contract
    assert numbers['99.72']['necessary_outer_MW'] < contract
    assert numbers['99.72']['witness_grade_C'] == 77.0

    plt = apply_house_style(fontsize=7.5)
    assert args.font_family in {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams.update({'font.family': 'sans-serif',
                         'font.sans-serif': [args.font_family],
                         'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig = plt.figure(figsize=(mm(80), mm(30)))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, 80), ylim=(0, 30))
    ax.axis('off')
    blue, orange, grey = '#0072B2', '#D55E00', '#54585A'
    texts, contained, lanes = [], [], []

    def label(x, y, text, size=7.5, color='black', weight='normal', ha='center', box=None):
        artist = ax.text(x, y, text, ha=ha, va='center', fontsize=size,
                         color=color, weight=weight)
        texts.append(artist)
        if box is not None:
            contained.append((artist, box))
        return artist

    def panel(bounds, color, face):
        x, y, w, h = bounds
        ax.add_patch(Rectangle((x, y), w, h, linewidth=.7,
                               edgecolor=color, facecolor=face))
        return bounds

    def connector(p, q, arrow=False):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>' if arrow else '-',
                                    mutation_scale=5, linewidth=.75, color=grey,
                                    shrinkA=0, shrinkB=0))
        x0, x1 = sorted([p[0], q[0]])
        y0, y1 = sorted([p[1], q[1]])
        lanes.append((x0-.3, x1+.3, y0-.6, y1+.6))

    label(40, 27.4, f'{contract:.1f} MW service: inner–outer bounds', size=8.0, weight='bold')
    left = panel((1.5, 4.0, 21, 20.7), grey, '#F4F6F7')
    label(12, 21.8, 'WtE + CCS', weight='bold', box=left)
    label(12, 17.6, f'User {user_supply:.0f}/{user_return:.0f}°C', size=7.5, box=left)
    label(12, 13.4, f'Loop {loop_supply:.0f}/{loop_return:.0f}°C', size=7.2, box=left)
    label(12, 8.4, f'HP {hp_inlet:.0f} → {hp_outlet:.0f}°C', size=7.2, box=left)
    connector((22.6, 14.1), (25, 14.1))
    connector((25, 9.0), (25, 19.3))
    connector((25, 19.3), (29.8, 19.3), arrow=True)
    connector((25, 9.0), (29.8, 9.0), arrow=True)

    good = panel((30.5, 14.2, 48, 10.5), blue, '#F0F7FB')
    bad = panel((30.5, 3.5, 48, 10.1), orange, '#FFF5EE')
    for capture, box, y, color, qualifier in [
            (95.0, good, 22.4, blue, '95% capture (calibrated)'),
            (99.72, bad, 11.5, orange, '99.72% capture')]:
        n = numbers[str(capture)]
        label(32, y, qualifier, size=7.3, weight='bold', ha='left', box=box)
        label(32, y-3.15,
              f"≈{n['constructed_lower_MW']:.3f}–{n['necessary_outer_MW']:.3f} MW",
              size=8.0, weight='bold', color=color, ha='left', box=box)
        decision = 'Contract constructed' if capture == 95 else f"{n['witness_grade_C']:.0f}°C cut: worst-profile exclusion"
        label(32, y-6.3, decision, size=7.0, color=color, ha='left', box=box)
    label(40, 1.25, 'Declared family; adaptive routes; not plant validation',
          size=6.7, color=grey)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    collisions = [[a.get_text(), b.get_text()] for i, a in enumerate(texts)
                  for b in texts[i+1:]
                  if a.get_window_extent(renderer).overlaps(b.get_window_extent(renderer))]
    outside = [a.get_text() for a in texts
               if not fig.bbox.contains(*a.get_window_extent(renderer).get_points()[0])
               or not fig.bbox.contains(*a.get_window_extent(renderer).get_points()[1])]
    overflow = []
    for a, (x, y, w, h) in contained:
        low = ax.transData.transform((x+.30, y+.30))
        high = ax.transData.transform((x+w-.30, y+h-.30))
        b = a.get_window_extent(renderer)
        if b.x0 < low[0] or b.y0 < low[1] or b.x1 > high[0] or b.y1 > high[1]:
            overflow.append(a.get_text())
    intrusions = [a.get_text() for x0, x1, y0, y1 in lanes for a in texts
                  if a.get_window_extent(renderer).overlaps(
                      Bbox(ax.transData.transform([[x0, y0], [x1, y1]])))]
    assert not collisions, collisions
    assert not outside, outside
    assert not overflow, overflow
    assert not intrusions, intrusions
    preflight = audit(fig, max_width_mm=80)
    assert preflight['ok'] and preflight['min_font_pt'] >= 6.7
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    stem = out/'project37_graphical_abstract_r46_service_certificate_20261011'
    with plt.rc_context({'savefig.bbox': None, 'savefig.pad_inches': 0}):
        for ext in ['pdf', 'svg', 'eps']:
            fig.savefig(stem.with_suffix('.'+ext), bbox_inches=None, pad_inches=0)
        for suffix, dpi in [('1200dpi', 1200), ('preview', 300)]:
            fig.savefig(out/f'{stem.name}_{suffix}.png', dpi=dpi,
                        bbox_inches=None, pad_inches=0)
    report = dict(status='PASS deterministic layout and numerical source binding',
                  size_mm=[80, 30], preflight=preflight,
                  minimum_font_pt=min(a.get_fontsize() for a in texts),
                  text_collisions=collisions, outside_canvas=outside,
                  panel_overflow=overflow, connector_intrusions=intrusions,
                  numerical_labels=dict(contract_MW=contract, cases=numbers,
                      customer_supply_C=user_supply, customer_return_C=user_return,
                      loop_supply_C=loop_supply, loop_return_C=loop_return,
                      hp_carrier_inlet_C=hp_inlet, hp_carrier_outlet_C=hp_outlet),
                  raw_labels={a.get_text(): a.get_fontsize() for a in texts},
                  font_selected=args.font_family, pdf_fonttype=42, raster_dpi=1200,
                  input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                  source_csv_fields=['capture_percent', 'retained_duty_DECLARED',
                      'common_grid_step_K', 'finite_constructed_lower_MW',
                      'continuum_necessary_upper_MW', 'continuum_witness_grade_C'],
                  scope='Declared worst source profile, fixed direct HP route and adaptive steady thermal construction. Not one installed HEN, joint plant validation, annual firm service or a confidence interval.',
                  visual_status='PENDING actual rendered inspection; generation cannot self-certify visual QA')
    payload = json.dumps(report, indent=2, default=lambda x: x.item())
    (out/'graphical_abstract_audit.json').write_text(payload, encoding='utf-8')
    print(payload)
    plt.close(fig)


if __name__ == '__main__':
    main()
