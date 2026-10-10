"""Same-service decision budgets linked to finite thermal constructions.

All money is constant EUR2020. Source duties/COP and output powers are anchors;
the assumed fixed-point power ledger is NOT an off-design turbine reproduction.
The catalogue's generic90%-capture capacity cost is a structural stress, not a
quote or a verified marginal95->99.72% absorber redesign. Price coordinates
carry no automatic EU/UK/Swiss ETS or biogenic-removal eligibility.
"""
from pathlib import Path
from datetime import datetime, timezone
import csv
import json

from construct_finite_heat_path_20261011 import (
    construct, ISENTROPIC, RETURN_COLD, HP99, RECOVERY_SCALE95, h)

ROOT = Path(__file__).resolve().parents[1]
CO2 = 5.168 * 3.6  # t/h at fixed published waste throughput
RETENTION = .99 * .995
CRF = .08 / (1 - (1 + .08) ** -25)
CATALOGUE_FIXED = 5.9e6 * CRF + .18e6  # EUR2020/(tCO2/h)/year


def power_pump(m, dp150, efficiency):
    """MW, prescribed quadratic pressure-loss resistance at rho=1000 kg/m3.

    dp150 is DECLARED pressure loss in MPa at150 kg/s. It is not fitted plant
    pressure loss. A new exchanger's pressure drop is a separate extra-power
    stress and is not inferred from UA. The law is only for a fixed resistance.
    """
    return (m / 1000) * dp150 * (m / 150) ** 2 / efficiency


def main():
    certificates = {}
    for name, ts, q, scale in [('noCCS120', 120., 37.3, 0.),
                               ('95adapted100', 100., 19.9, RECOVERY_SCALE95),
                               ('99adapted100', 100., 18.5, 1.)]:
        s, _ = construct(ts, q, scale, ISENTROPIC.h / 1000, RETURN_COLD, .5, 136., .1)
        assert s['thermal_path_constructed'], (name, s['unmet_MW'])
        certificates[name] = s
    # Source electricity anchors less the full source module's HP power.
    points = {'noCCS120': dict(capture=0., power=8.12),
              '95adapted100': dict(capture=.95, power=6.25 - HP99 * RECOVERY_SCALE95 / 5.5),
              '99adapted100': dict(capture=.9972, power=6.17 - HP99 / 5.5)}
    rows = []
    for baseline in ['noCCS120', '95adapted100']:
        dc = CO2 * (.9972 - points[baseline]['capture'])
        retained = dc * RETENTION
        dp_anchor = points[baseline]['power'] - points['99adapted100']['power']
        extra_fixed = dc * CATALOGUE_FIXED
        for hours in [6000, 8000, 8760]:
            for ef in [50., 179., 429., 700.]:
                for chain_gwp in [0., 50., 100.]:
                    for fossil in [.2, .4, .4679, .6]:
                        for dp150 in [.1, .3, .6]:
                            for pump_eta in [.6, .75, .85]:
                                network_pump = (power_pump(certificates['99adapted100']['primary_water_kg_s'], dp150, pump_eta)
                                                - power_pump(certificates[baseline]['primary_water_kg_s'], dp150, pump_eta))
                                for extra_aux in [0., .1, .5]:
                                    lost_power = dp_anchor + network_pump + extra_aux
                                    gwp = (lost_power * ef + dc * chain_gwp - retained * fossil * 1000) * hours
                                    fossil_threshold = (lost_power * ef + dc * chain_gwp) / (retained * 1000)
                                    for pe in [40., 70., 120.]:
                                        for effective_value in [0., 100., 300., 500.]:
                                            chain_cost = 50.
                                            headroom = (effective_value * retained * fossil
                                                        - pe * lost_power - chain_cost * dc) * hours
                                            budget = headroom - extra_fixed
                                            value_zero = (pe * lost_power + chain_cost * dc
                                                          + extra_fixed / hours) / (retained * fossil)
                                            rows.append(dict(comparator=baseline, hours_SCENARIO=hours,
                                                electricity_EF_kg_MWh_SCENARIO=ef, chain_burden_kg_t_SCENARIO=chain_gwp,
                                                fossil_share_SCENARIO=fossil, pressure_drop_at150_MPa_DECLARED=dp150,
                                                pump_efficiency_DECLARED=pump_eta, extra_aux_MW_DECLARED=extra_aux,
                                                electricity_price_EUR2020_MWh_SCENARIO=pe,
                                                effective_fossil_value_EUR2020_t_SCENARIO=effective_value,
                                                additional_network_pumping_MW=network_pump,
                                                additional_anchor_electricity_loss_MW=dp_anchor,
                                                total_additional_electricity_MW=lost_power,
                                                additional_captured_t_year=dc * hours,
                                                additional_retained_fossil_t_year=retained * fossil * hours,
                                                included_delta_climate_kgCO2e_year=gwp,
                                                fossil_share_break_even_INCLUDED=fossil_threshold,
                                                pre_fixed_headroom_EUR2020_year=headroom,
                                                extra_capture_fixed_cost_STRESS_EUR2020_year=extra_fixed,
                                                maximum_remaining_annual_scope_EUR2020_year=budget,
                                                zero_remaining_budget_value_EUR2020_t=value_zero))
    central = [r for r in rows if r['hours_SCENARIO'] == 8000 and r['electricity_EF_kg_MWh_SCENARIO'] == 179
               and r['chain_burden_kg_t_SCENARIO'] == 50 and r['fossil_share_SCENARIO'] == .4
               and r['pressure_drop_at150_MPa_DECLARED'] == .3 and r['pump_efficiency_DECLARED'] == .75
               and r['extra_aux_MW_DECLARED'] == 0 and r['electricity_price_EUR2020_MWh_SCENARIO'] == 70
               and r['effective_fossil_value_EUR2020_t_SCENARIO'] in [300, 500]]
    for r in central:
        # Algebraic crosscheck: value coordinate producing zero budget.
        residual = r['maximum_remaining_annual_scope_EUR2020_year'] + (
            r['zero_remaining_budget_value_EUR2020_t'] - r['effective_fossil_value_EUR2020_t_SCENARIO']
        ) * r['additional_retained_fossil_t_year']
        assert abs(residual) < 1e-7
    with (ROOT / 'results/finite_path_decision_budget_20261011.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                  status='PASS conditional same-service budget, three thermal paths and algebra checks',
                  certificates=certificates, fixed_point_power_anchors=points,
                  row_count=len(rows), central_rows=central,
                  all_sensitivity_rows_retained=True, monetary_basis='constant EUR2020',
                  capital_source='DEA401a2024: 2025 coordinate 5.9 million EUR2020/(t/h), 0.18 million EUR2020/(t/h)/year; generic90% design; capacity-proportional stress only.',
                  prescribed_pump_envelope='dp150=[0.1,0.3,0.6]MPa; eta=[0.6,0.75,0.85]; extra auxiliary=[0,0.1,0.5]MW. Scenario coordinates, not observed bounds or probability.',
                  same_feed_and_service='500 t/day; 36.5MW secondary80/50C; noCCS primary120/60C versus captured primary100/60C. 95% and99.72% adapted comparators share the same primary flow/interface.',
                  remaining_scope=['Extra branch/interface/pump equipment and installation capital/fixed O&M.',
                                   'Extra coolant/pressure-loss power beyond the prescribed auxiliary scenario.',
                                   'Solvent, construction and full capture/transport/storage inventory differences.',
                                   'Reliability/off-design firm service and availability costs.'],
                  limits=['Finite steady thermal service is constructed, not validated field performance.',
                          'Fixed-point electricity anchors are assumed applicable; no fully reconstructed joint steam/power cycle.',
                          'No empirical probability, present ETS price, legal entitlement or bankable investment ranking.',
                          'Positive remaining budget means maximum affordable omitted scope under assumptions, not observed profit.',
                          'The 95% recovery shape is proportional calibration, not independent source validation.'])
    (ROOT / 'results/finite_path_decision_budget_audit_20261011.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'certificates'}, indent=2))


if __name__ == '__main__':
    main()
