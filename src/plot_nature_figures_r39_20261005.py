"""Nature-inspired, editable artwork from frozen project37 calculations.

SciencePlots styles: John Garrett, MIT, pinned b9b1695 (licence alongside styles).
Baker Laboratory alignment QA: Apache-2.0, pinned ee5aaa4 (licence retained).
No scientific data are generated, filtered for favorable outcomes or overwritten.
Scenario envelopes are not confidence intervals. See the figure contract.
"""
from pathlib import Path
from functools import lru_cache
import csv
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "src/figure_style_r39"
OUT = ROOT / "results/figures/nature_r39_20261005"
OUT.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(ROOT / "cache/matplotlib_nature_r39")
sys.path.insert(0, str(STYLE))
sys.path.insert(0, str(ROOT / "cache/python_packages_r32"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.transforms import ScaledTranslation
from matplotlib.ticker import StrMethodFormatter
from audit_panel_alignment import require_matplotlib_panel_alignment
from iapws import IAPWS97

# Actual GitHub style inheritance, not a merely claimed visual resemblance.
plt.style.use([str(STYLE / p) for p in
               ["science.mplstyle", "no-latex.mplstyle", "nature.mplstyle"]])
plt.rcParams.update({
    "font.family": ["Arial", "DejaVu Sans"],
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "axes.titlesize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "text.usetex": False, "mathtext.fontset": "dejavusans",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": .6, "lines.linewidth": 1., "lines.markersize": 3,
    "xtick.direction": "out", "ytick.direction": "out",
    "xtick.top": False, "ytick.right": False,
    "xtick.minor.visible": False, "ytick.minor.visible": False,
    "axes.grid": False, "legend.frameon": False,
    "savefig.bbox": None, "figure.facecolor": "white", "axes.facecolor": "white",
})
WIDTH_MM = 164
PURPLE, CYAN, ORANGE, GREY = "#4b2e83", "#4196b5", "#b66b38", "#71767c"
INPUTS = [
    "results/exact_water_comparison_qc_r35_20261002.json",
    "results/figure_physical_service_qc_r35_20261002.json",
    "results/exact_water_annual_r35_20261002.csv",
    "results/exact_water_smallstore_r35_20261002.csv",
    "results/exact_water_adaptation_r35_20261002.csv",
    "results/steam_phase_domain_qc_r33_20261002.json",
    "datasets/hagenholz_monthly_clean_r35_20261002.csv",
    "results/swiss_monthly_service_cuts_r35_20261002.csv",
    "results/monthly_service_figure_values_r35_20261002.json",
]
HASHES = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in INPUTS}
LEDGER = {}


def csv_rows(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


@lru_cache(maxsize=None)
def water(temp):
    return IAPWS97(P=1, T=float(temp) + 273.15).h / 1000


def title(ax, letter, text):
    fig = ax.figure
    ax.text(0, 1, letter, transform=ax.transAxes +
            ScaledTranslation(-11 / 72, 11 / 72, fig.dpi_scale_trans),
            ha="left", va="bottom", fontsize=8, fontweight="bold", clip_on=False)
    ax.text(0, 1, text, transform=ax.transAxes +
            ScaledTranslation(0, 11 / 72, fig.dpi_scale_trans),
            ha="left", va="bottom", fontsize=7, clip_on=False)


def two_panels(height_mm=91, top=.72, bottom=.24):
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH_MM / 25.4, height_mm / 25.4))
    fig.subplots_adjust(left=.105, right=.985, bottom=bottom, top=top, wspace=.43)
    return fig, axes


def save(fig, stem, values, *, column_groups=None):
    fig.canvas.draw()
    options = {"column_groups": column_groups} if column_groups else {}
    report = require_matplotlib_panel_alignment(
        fig, json_out=OUT / (stem + ".alignment.json"), tolerance_pt=1.5,
        gutter_tolerance_pt=1.5, require_panel_labels=True, strict=True,
        **options,
    )
    fig.savefig(OUT / (stem + ".pdf"))
    fig.savefig(OUT / (stem + ".svg"))
    fig.savefig(OUT / (stem + ".png"), dpi=1200)
    # Matplotlib also produces the actual-size screen QA and grayscale preview.
    fig.savefig(OUT / (stem + ".preview.png"), dpi=300)
    from PIL import Image
    with Image.open(OUT / (stem + ".preview.png")) as image:
        image.convert("L").save(OUT / (stem + ".grayscale-qa.png"))
    LEDGER[stem] = {"values": values, "width_mm": WIDTH_MM,
                   "height_mm": float(fig.get_size_inches()[1] * 25.4),
                   "raster_dpi": 1200, "alignment_verdict": report["verdict"]}
    plt.close(fig)
    print("Exported " + stem, flush=True)


def capacity(temp, flow, basic):
    scale = 1. if basic == 18.5 else (38. - 19.9) / (5.3 + 1.6 + 9.8 * 5.5 / 4.5)
    streams = [(basic, 390), (5.3 * scale, 91), (1.6 * scale, 158),
               (9.8 * 5.5 / 4.5 * scale, 77)]
    limits = [sum(q for q, _ in streams), flow * (water(temp) - water(60))]
    for grade in {t for _, t in streams if t < temp}:
        fraction = (water(grade) - water(60)) / (water(temp) - water(60))
        limits.append(sum(q for q, t in streams if t > grade) / (1 - fraction))
    return min(limits)


def domain():
    endpoint = json.loads((ROOT / INPUTS[0]).read_text())
    tmax, tmin = endpoint["headline_exact_Tmax_C"], endpoint["headline_exact_Tmin_C"]
    temps, flows = np.linspace(80, 140, 241), np.linspace(100, 500, 241)
    category = np.empty((len(flows), len(temps)))
    for j, flow in enumerate(flows):
        for i, temp in enumerate(temps):
            hydraulic = flow * (water(temp) - water(60)) >= 36.5
            high = capacity(temp, flow, 18.5) >= 36.5 and temp >= 85
            lower = capacity(temp, flow, 19.9) >= 36.5 and temp >= 85
            aggregate = hydraulic and temp >= 85
            category[j, i] = 3 if high else 2 if lower else 1 if aggregate else 0
    colours = ["#f2f3f5", "#f1d6c7", "#bed2e9", "#97c2b0"]
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, 119 / 25.4))
    grid = fig.add_gridspec(2, 1, left=.145, right=.985, bottom=.115,
                           top=.825, height_ratios=[3.4, 1], hspace=.87)
    upper, lower = fig.add_subplot(grid[0]), fig.add_subplot(grid[1])
    upper.contourf(temps, flows, category, levels=[-.5, .5, 1.5, 2.5, 3.5],
                   colors=colours, antialiased=False)
    upper.plot(temps, [36.5 / (water(t) - water(60)) for t in temps],
               color="#30343a", lw=1.)
    upper.axvline(tmax, color=PURPLE, lw=.8)
    upper.axhline(150, color=GREY, lw=.7, ls="--")
    upper.scatter([100, 120], [36.5 / (water(100) - water(60)), 150],
                  s=12, color="#20252a", zorder=5)
    upper.set(xlim=(80, 140), ylim=(100, 500), xticks=np.arange(80, 141, 10),
              xlabel="Primary supply temperature (°C); return 60 °C",
              ylabel="Primary flow limit (kg/s)")
    title(upper, "a", "Temperature-flow screen")
    handles = [Patch(facecolor=c, label=l) for c, l in zip(colours[::-1],
               ["Both screens pass", "95% screen only", "Aggregate-only pass", "Rejected"])]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(.54, .985),
               ncol=4, columnspacing=1.2, handlelength=1.1, handletextpad=.45)
    line_handles = [Line2D([], [], color="#30343a", lw=1, label="Required flow"),
                    Line2D([], [], color=PURPLE, lw=.8, label="99.72% grade limit"),
                    Line2D([], [], color=GREY, ls="--", lw=.7, label="150 kg/s limit")]
    fig.legend(handles=line_handles, loc="upper center", bbox_to_anchor=(.54, .935),
               ncol=3, columnspacing=1.4, handlelength=2.0)
    lower.hlines(1, 110, tmax, color=PURPLE, lw=3)
    lower.hlines(0, tmin, 122, color=GREY, lw=3)
    lower.scatter([tmax, tmin], [1, 0], color=[PURPLE, GREY], s=11, zorder=4)
    lower.set(xlim=(110, 122), ylim=(-.65, 1.65), yticks=[0, 1],
              yticklabels=["Flow limit", "Heat grade"],
              xticks=[110, tmax, tmin, 122],
              xticklabels=["110", f"{tmax:.2f}", f"{tmin:.2f}", "122"],
              xlabel="Primary supply temperature (°C)")
    title(lower, "b", f"Incompatible limits at 150 kg/s: {tmin - tmax:.3f} K gap")
    save(fig, "Fig1_service_domain", dict(Tmax_C=tmax, Tmin_C=tmin,
         gap_K=tmin - tmax, categorical_grid_shape=list(category.shape),
         necessary_screen_only=True), column_groups=[["a", "b"]])


def annual():
    old = json.loads((ROOT / INPUTS[1]).read_text())
    annual_rows, small_rows = csv_rows(INPUTS[2]), csv_rows(INPUTS[3])
    fig, axes = two_panels(85, top=.74, bottom=.23)
    labels = ["No CCS, graded", "CCS, aggregate", "CCS, graded"]
    colours = [GREY, CYAN, PURPLE]
    values = []
    for ax, region, heading in zip(axes, ["Oberland", "Porto metropolitan area"],
                                   ["Oberland modeled load", "Porto modeled load"]):
        matrix = []
        for size in [0, 5000, 50000]:
            data = small_rows if size == 5000 else annual_rows
            row = []
            for capture, model in [("False", "temperature_cascade"),
                                   ("True", "aggregate_heat"), ("True", "temperature_cascade")]:
                item = next(r for r in data if r["proxy"] == region and
                    r["supply_temperature_C"] == "120" and r["capture_on"] == capture and
                    r["model"] == model and (size == 5000 or
                    (r["mean_duty_ratio_SCENARIO"] == "0.3" and
                     r["tank"] == ("no_store" if size == 0 else "141b Large TTES"))))
                row.append(float(item["unserved_MWh"]))
            matrix.append(row)
        prior = next(r for r in old["annual_values"] if r["proxy"] == region)
        assert np.array_equal(matrix, prior["unserved_matrix_MWh"])
        array = np.asarray(matrix)
        for k, colour in enumerate(colours):
            ax.bar(np.arange(3) + (k - 1) * .24, array[:, k], .215,
                   color=colour, edgecolor="none")
        ax.set(xticks=np.arange(3), xticklabels=["No store", "5,000 m³", "50,000 m³"],
               xlabel="Tank volume", ylabel="Unserved heat (MWh/cycle)", xlim=(-.6, 2.6))
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        if region == "Oberland":
            ax.set_ylim(0, 3.7)
            ax.set_yticks([0, 1, 2, 3])
            for i in range(3):
                for k in range(3):
                    x, y = i + (k - 1) * .24, array[i, k]
                    ax.text(x, y + .10, "0" if y == 0 else f"{y:.3f}",
                            ha="center", va="bottom", fontsize=7)
        else:
            ax.set_ylim(0, 10100)
            ax.set_yticks([0, 2500, 5000, 7500, 10000])
        values.append(dict(proxy=region, unserved_matrix_MWh=matrix))
        title(ax, "a" if region == "Oberland" else "b", heading)
    fig.legend(handles=[Patch(facecolor=c, label=l) for c, l in zip(colours, labels)],
               ncol=3, loc="upper center", bbox_to_anchor=(.55, .98),
               handlelength=1.2, columnspacing=2.2)
    fig.text(.55, .04, "Same contract; different vertical scales. Zeros are displayed explicitly.",
             fontsize=7, ha="center")
    save(fig, "Fig2_finite_storage", values)


def adaptation():
    data = csv_rows(INPUTS[4])
    rows = [next(r for r in data if r["comparator"] == comparator and
                 all(r[k] == v for k, v in {
                     "hours_SCENARIO": "8000", "electricity_EF_kg_MWh_SCENARIO": "179",
                     "incremental_chain_burden_kg_t_SCENARIO": "50",
                     "incremental_network_pumping_MW_SCENARIO": "0",
                     "fossil_share_SCENARIO": "0.4", "electricity_price_EUR_MWh_SCENARIO": "70",
                     "effective_fossil_value_EUR_t_SCENARIO": "300"}.items()))
            for comparator in ["same99_train_bypass", "published95_design"]]
    fig, axes = two_panels(94, top=.73, bottom=.25)
    values = []
    for label, colour, row in zip(["Installed train with bypass", "Published 95% design"],
                                  [PURPLE, CYAN], rows):
        capture, fossil = float(row["extra_capture_t_y"]), float(row["extra_retained_fossil_t_y"])
        threshold = float(row["marginal_climate_fossil_share_threshold"])
        electricity = (threshold * 1000 * (fossil / .4) - 50 * capture) / 179
        carbon_value, burden = np.linspace(0, 600, 121), np.linspace(0, 750, 101)
        ceiling_hi = (carbon_value * fossil - 70 * electricity - 50 * capture) / 1e6
        ceiling_lo = ceiling_hi - 70 * .5 * 8000 / 1e6
        axes[0].fill_between(carbon_value, ceiling_lo, ceiling_hi, color=colour, alpha=.13)
        axes[0].plot(carbon_value, ceiling_hi, color=colour, lw=1.)
        axes[0].plot(carbon_value, ceiling_lo, color=colour, lw=.8, ls="--")
        for pump, linestyle in [(0, "-"), (.5, "--")]:
            boundary = 100 * ((electricity + 8000 * pump) * burden + capture * 50) / (1000 * (fossil / .4))
            axes[1].plot(burden, boundary, color=colour, lw=1., ls=linestyle)
        central_margin = (300 * fossil - 70 * electricity - 50 * capture)
        assert np.isclose(central_margin, float(row["maximum_included_annual_adaptation_cost_EUR_y"]), rtol=1e-12)
        values.append(dict(comparator=row["comparator"], extra_capture_t_y=capture,
                           extra_fossil_t_y=fossil, extra_electricity_MWh_y=electricity,
                           central_threshold=threshold, central_headroom_EUR_y=central_margin,
                           value_grid=carbon_value.tolist(), ceiling_hi_million_EUR_y=ceiling_hi.tolist(),
                           ceiling_lo_million_EUR_y=ceiling_lo.tolist()))
    axes[0].axhline(0, color=GREY, lw=.6, ls=":")
    axes[0].set(xlim=(0, 600), xticks=[0, 200, 400, 600],
                xlabel="Effective fossil value (EUR2020/t)",
                ylabel="Adaptation headroom\n(million EUR2020/year)")
    axes[1].axhline(40, color=GREY, lw=.6, ls=":")
    axes[1].set(xlim=(0, 750), xticks=[0, 250, 500, 750],
                xlabel="Electricity burden (kg CO₂e/MWh)",
                ylabel="Fossil-share climate threshold (%)", ylim=(0, 78))
    title(axes[0], "a", "Conditional operating headroom")
    title(axes[1], "b", "Climate sign boundary")
    fig.legend(handles=[Line2D([], [], color=c, lw=1.1, label=l) for c, l in
                        zip([PURPLE, CYAN], ["Installed train with bypass", "Published 95% design"])],
               ncol=2, loc="upper center", bbox_to_anchor=(.55, .98), columnspacing=2)
    fig.text(.55, .075, "Solid: 0 MW pump   Dashed: +0.5 MW pump   Dotted: 40% fossil share",
             ha="center", fontsize=7)
    fig.text(.55, .025, "Shaded bands are pumping scenarios, not confidence intervals.",
             ha="center", fontsize=7)
    save(fig, "Fig3_environmental_headroom", values)


def phase():
    bracket = json.loads((ROOT / INPUTS[5]).read_text())["su_bracket"]
    fig, axes = two_panels(96, top=.68, bottom=.24)
    x, width = np.arange(2), .22
    heat = np.array([37.3, 18.5])
    latent, superheat = heat * bracket["latent_fraction_lower"], heat * bracket["superheat_fraction_upper"]
    for offset, array, colour in [(-1, heat, GREY), (0, latent, CYAN), (1, superheat, ORANGE)]:
        axes[0].bar(x + offset * width, array, width * .93, color=colour, edgecolor="none")
    axes[0].set(xticks=x, xticklabels=["No CCS", "99.72% CCS"], ylim=(0, 44),
                ylabel="Steam-derived duty (MW)")
    from physical_service_caseB_check_r32_20261002 import CASES
    from physical_service_caseB_envelope_r32_20261002 import heat_limit
    approaches, curves = np.linspace(0, 10, 501), []
    sat, inlet, ret = IAPWS97(P=.12, x=1), IAPWS97(P=.12, T=381.15), IAPWS97(P=.1, T=328.15)
    rho, plateau = (inlet.h - sat.h) / (inlet.h - ret.h), sat.T - 273.15
    difference = IAPWS97(P=1, T=373.15).h - IAPWS97(P=1, T=328.15).h
    for hours in (8000, 8760):
        for internal in (0, 3.4):
            duty = heat_limit(CASES[0], hours, 0, internal)
            fraction = np.array([max(0, (IAPWS97(P=1, T=373.15).h -
                IAPWS97(P=1, T=plateau - a + 273.15).h) / difference) for a in approaches])
            curve = np.where(approaches <= plateau - 100, duty,
                             np.minimum(duty, duty * rho / np.maximum(fraction, 1e-12)))
            curves.append(np.where(approaches <= 8, curve, 0))
    lo, hi = np.min(curves, axis=0), np.max(curves, axis=0)
    rect_lo = np.where(approaches <= 8, heat_limit(CASES[0], 8760, 0, 3.4), 0)
    rect_hi = np.where(approaches <= 8, heat_limit(CASES[0], 8000, 0, 0), 0)
    axes[1].fill_between(approaches, rect_lo, rect_hi, color=PURPLE, alpha=.16)
    axes[1].plot(approaches, rect_hi, color=PURPLE, lw=.8, ls="--")
    axes[1].fill_between(approaches, lo, hi, color=CYAN, alpha=.25)
    axes[1].plot(approaches, hi, color=CYAN, lw=1.)
    axes[1].axhline(64.4, color=GREY, ls=":", lw=.8)
    axes[1].set(xlabel="Minimum approach (K)", ylabel="Steam-only service ceiling (MW)",
                xlim=(0, 10), ylim=(0, 110), xticks=[0, 2, 4, 6, 8, 10])
    title(axes[0], "a", "Primary steam-duty bracket")
    title(axes[1], "b", "Swiss route at 100/55 °C")
    handles = [Patch(facecolor=GREY, label="Published basic heat"),
               Patch(facecolor=CYAN, label="Latent lower bound"),
               Patch(facecolor=ORANGE, label="Superheat upper bound"),
               Patch(facecolor=PURPLE, alpha=.16, label="Inlet-grade envelope"),
               Patch(facecolor=CYAN, alpha=.25, label="Condensation envelope"),
               Line2D([], [], color=GREY, ls=":", label="Required DH service")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(.55, .985),
               ncol=3, columnspacing=1.5, handlelength=1.2, labelspacing=.8)
    fig.text(.55, .06, "Brackets are bounds, not heat partitions; ranges are structural, not confidence intervals.",
             ha="center", fontsize=7)
    save(fig, "FigS1_steam_phase", dict(basic_MW=heat.tolist(), latent_lower_MW=latent.tolist(),
         superheat_upper_MW=superheat.tolist(), approaches_K=approaches.tolist(),
         condensing_lo_MW=lo.tolist(), condensing_hi_MW=hi.tolist(),
         rectangular_lo_MW=rect_lo.tolist(), rectangular_hi_MW=rect_hi.tolist()))


def monthly():
    data, cuts = csv_rows(INPUTS[6]), csv_rows(INPUTS[7])
    fig, axes = two_panels(98, top=.73, bottom=.29)
    colours = [GREY, CYAN, PURPLE, ORANGE, "#234969", "#356c56"]
    styles = [":", "--", "-", "-.", "-", "-"]
    markers = [None, None, None, None, "o", "s"]
    lines, normalized = [], []
    for k, year in enumerate(range(2020, 2026)):
        rows = sorted([r for r in data if int(r["year"]) == year], key=lambda r: int(r["month"]))
        assert len(rows) == 12
        mean = sum(float(r["heat_sales_MWh"]) for r in rows) / sum(float(r["calendar_hours"]) for r in rows)
        values = [float(r["heat_sales_MWh"]) / float(r["calendar_hours"]) / mean for r in rows]
        line, = axes[0].plot(np.arange(1, 13), values, color=colours[k], ls=styles[k],
                            marker=markers[k], markersize=2.2, lw=.8, label=str(year))
        lines.append(line)
        normalized.append(dict(year=year, mean_heat_MW=mean, normalized=values))
    axes[0].set(xlabel="Calendar month", ylabel="Monthly export / calendar mean",
                xticks=[1, 3, 5, 7, 9, 11], xlim=(1, 12), ylim=(.25, 1.8))
    axes[0].axhline(1, color=GREY, lw=.6, ls=":")
    groups = [(95, 0, "95 °C\nNo CCS"), (95, .99, "95 °C\n99% CCS"),
              (100, 0, "100 °C\nNo CCS"), (100, .99, "100 °C\n99% CCS")]
    ranges = []
    for x, (temp, capture, _) in enumerate(groups):
        for model, offset, colour, marker in [
            ("rectangular_inlet_grade", -.12, PURPLE, "o"),
            ("condensation_cut", .12, CYAN, "s")]:
            values = [float(r["necessary_mean_service_ceiling_MW"]) for r in cuts if
                int(r["supply_SCENARIO_C"]) == temp and float(r["capture_fraction"]) == capture and
                r["thermal_model"] == model and r["volume_SCENARIO_m3"] == "0" and
                r["feed_timing_SCENARIO"] == "observed_monthly_throughput_shape"]
            assert len(values) == 12, "Six years times two internal-heat stresses"
            lo, hi = min(values), max(values)
            axes[1].plot([x + offset] * 2, [lo, hi], color=colour, lw=1.3)
            axes[1].scatter([x + offset] * 2, [lo, hi], marker=marker, color=colour, s=12, zorder=4)
            ranges.append(dict(supply=temp, capture=capture, model=model, min_MW=lo, max_MW=hi))
    axes[1].set(xticks=np.arange(4), xticklabels=[g[2] for g in groups],
                ylabel="Necessary mean service ceiling (MW)", ylim=(25, 71), xlim=(-.5, 3.5))
    title(axes[0], "a", "Observed monthly exports")
    title(axes[1], "b", "Conditional no-boost ceiling")
    fig.legend(handles=lines, ncol=6, loc="upper center", bbox_to_anchor=(.55, .98),
               handlelength=1.7, columnspacing=1.2)
    fig.legend(handles=[Line2D([], [], color=PURPLE, marker="o", label="Inlet-grade screen"),
                        Line2D([], [], color=CYAN, marker="s", label="Condensation cut")],
               ncol=2, loc="lower center", bbox_to_anchor=(.55, .07), columnspacing=2)
    fig.text(.55, .025, "Ranges: six observed years × 0/3.4 MW internal heat; not confidence intervals.",
             fontsize=7, ha="center")
    prior = json.loads((ROOT / INPUTS[8]).read_text())
    assert ranges == prior
    save(fig, "FigS2_monthly_service", dict(years=normalized, ranges=ranges))


def main():
    domain()
    annual()
    adaptation()
    phase()
    monthly()
    assert {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in INPUTS} == HASHES
    report = dict(status="Figures rendered; PDF collision and visual QA pending",
                  scientific_inputs_unchanged=True, source_hashes=HASHES, figures=LEDGER,
                  reuse="MIT SciencePlots style-only inheritance; Apache-2.0 Baker QA",
                  final_canvas_note="164 mm manuscript width, not a Nature submission contract")
    (OUT / "figure_data_and_export_manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: {a: v[a] for a in ["width_mm", "height_mm", "raster_dpi", "alignment_verdict"]}
                      for k, v in LEDGER.items()}, indent=2))


if __name__ == "__main__":
    main()
