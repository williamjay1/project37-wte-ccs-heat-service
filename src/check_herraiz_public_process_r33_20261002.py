"""Independent arithmetic and steam-state checks of a newly acquired table.

Use published inputs; do not calibrate steam pressure/temperature/return or
turbine output to validation targets. Same Su model lineage, not source C.
"""
from pathlib import Path
import sys, json, csv
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'cache/python_packages_r32'))
from iapws import IAPWS97

def main():
    p=json.loads((ROOT/'datasets/herraiz2026_process_table_r33_20261002.json').read_text())
    rows=[]
    def add(name, calculated, reported, unit, status):
        rows.append(dict(quantity=name,calculated=calculated,reported=reported,
                         relative_error_percent=100*(calculated/reported-1),unit=unit,
                         evidence_level=status))
    add('thermal_input',p['waste_t_day']*1000/86400*p['LHV_MJ_kg'],p['thermal_input_MW'],
        'MW','Independent feed/LHV arithmetic; rounded table, not boiler-efficiency validation')
    for key in ('rounded_aux_MW','detailed_aux_MW'):
        add('net_CCS_CHP_'+key,p['gross_CHP_power_MW']-sum(p[key]),p['net_CCS_CHP_power_MW'],
            'MW','Independent auxiliary closure given published gross power; turbine generation is not reproduced')
    add('PCC_heat_from_captured_mass',p['captured_CO2_kg_s']*p['specific_reboiler_MJ_kg_CO2'],
        p['PCC_heat_MW'],'MW','Independent captured-mass duty check, not fitted heat output')
    for i,cap in enumerate(('no_CCS','CCS')):
        add('specific_DH_'+cap,p['DH_heat_MW'][i]*3.6/(p['waste_t_day']/24),
            p['DH_heat_GJ_t_waste'][i],'GJ/t wet waste','Independent MW/throughput unit closure')
    # Cross-source state check: Su main extraction4bar, new table144/136C.
    inlet=IAPWS97(P=.4,T=p['table_PCC_steam_supply_C']+273.15)
    ret=IAPWS97(P=.4,T=p['table_PCC_condensate_return_C']+273.15)
    q=p['PCC_steam_mass_kg_s']*(inlet.h-ret.h)/1000
    add('PCC_heat_4bar_144_to136',q,p['PCC_heat_MW'],'MW',
        'Conditional same-lineage cross-source state check; pressure is Su main, not printed in2026 table')
    diagram_sat=IAPWS97(P=p['diagram_PCC_pressure_bar']/10,x=1)
    diagram_liq=IAPWS97(P=p['diagram_PCC_pressure_bar']/10,x=0)
    qdiagram=p['PCC_steam_mass_kg_s']*(diagram_sat.h-diagram_liq.h)/1000
    add('PCC_heat_diagram_saturated_3p21bar',qdiagram,p['PCC_heat_MW'],'MW',
        'Alternative near-saturated diagram interpretation; not merged with144/136C table')
    # A DH-water return is not its steam-condensate return. No steam enthalpy
    # is inferred by fitting37.3/18.5MW. Report the unresolved distinction.
    with (ROOT/'results/herraiz_public_process_checks_r33_20261002.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    out=dict(created_utc=datetime.now(timezone.utc).isoformat(),source_card=p['locators'],
        checks=len(rows),thermal_input_relative_error_percent=rows[0]['relative_error_percent'],
        net_CCS_aux_closure_range_MW=[min(r['calculated'] for r in rows if r['quantity'].startswith('net_CCS')),max(r['calculated'] for r in rows if r['quantity'].startswith('net_CCS'))],
        PCC_heat_state_range_MW=[min(q,qdiagram),max(q,qdiagram)],
        printed_PCC_heat_MW=p['PCC_heat_MW'],captured_mass_PCC_heat_MW=p['captured_CO2_kg_s']*p['specific_reboiler_MJ_kg_CO2'],
        saturation_3p21bar_C=diagram_sat.T-273.15,
        reboiler125C_10K_plateau_margin_K=diagram_sat.T-273.15-135,
        main_source_saturation4bar_C=IAPWS97(P=.4,x=1).T-273.15,
        DH_water_contract_SOURCE_C=[p['DH_water_supply_C'],p['DH_water_return_C']],
        same_process_lineage_as_Su2023=True,
        unresolved=['DH condensate return is not DH-water return','Complete independently reproduced turbine/net-power state is unavailable',
                    'Diagram3.21bar/136C differs from table144/136C and Su main4bar; no fit or averaging',
                    'New80/60C source contract does not validate100/120C transfer'],
        acceptance='Recorded arithmetic/state checks, including discrepancies; not full process/hardware or LCA reproduction')
    assert abs(rows[0]['relative_error_percent'])<.1
    assert max(abs(r['relative_error_percent']) for r in rows[1:3])<.2
    assert max(abs(r['relative_error_percent']) for r in rows[3:])<3
    (ROOT/'results/herraiz_public_process_qc_r33_20261002.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
