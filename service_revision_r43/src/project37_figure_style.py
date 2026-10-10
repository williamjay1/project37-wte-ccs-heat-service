"""Portable publication artwork settings and deterministic size/font checks.

SciencePlots style resources are supplied next to this module under
figure_style_r39/, with their original MIT copyright/license. This module has
no dependency on a user's installed skill directory or a TeX installation.
Numerical conclusions are independent of font/rendering variations.
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

NATURE_SINGLE_MM = 89.0
NATURE_DOUBLE_MM = 183.0


def mm(value):
    return value / 25.4


def apply_house_style(fontsize=7.0):
    resource = Path(__file__).resolve().parent / 'figure_style_r39'
    for name in ['science.mplstyle', 'nature.mplstyle', 'scienceplots_LICENSE']:
        if not (resource / name).is_file():
            raise FileNotFoundError(f'Missing licensed artwork resource: {name}')
    plt.style.use([str(resource / 'science.mplstyle'), str(resource / 'nature.mplstyle')])
    plt.rcParams.update({
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
        'font.size': fontsize, 'axes.titlesize': fontsize,
        'axes.labelsize': fontsize, 'xtick.labelsize': fontsize - 1,
        'ytick.labelsize': fontsize - 1, 'legend.fontsize': fontsize - 1,
        'figure.dpi': 150, 'savefig.dpi': 600, 'savefig.bbox': 'tight',
        'axes.grid': False, 'legend.frameon': False, 'text.usetex': False})
    return plt


def panel_label(ax, text, pad=8):
    ax.set_title(text, loc='left', fontweight='bold',
                 fontsize=plt.rcParams['font.size'], pad=pad)


def save(fig, stem, dpi=600):
    paths = {}
    for ext in ['pdf', 'png', 'svg']:
        path = f'{stem}.{ext}'
        fig.savefig(path, dpi=dpi, bbox_inches='tight')
        paths[ext] = path
    return paths


def audit(fig, max_width_mm=NATURE_DOUBLE_MM):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    sizes, titles = [], []
    for idx, ax in enumerate(fig.axes):
        candidates = list(ax.texts) + [ax.title, ax._left_title, ax._right_title]
        if ax.axison:
            # axis('off') suppresses tick/axis labels even if their individual
            # Artist visible flag remains True. Do not count unrendered fonts.
            candidates += [ax.xaxis.label, ax.yaxis.label]
            candidates += list(ax.get_xticklabels()) + list(ax.get_yticklabels())
        if ax.get_legend() is not None:
            candidates += list(ax.get_legend().get_texts())
        for artist in candidates:
            if artist.get_visible() and artist.get_text().strip():
                sizes.append(float(artist.get_fontsize()))
        for loc in ['left', 'center', 'right']:
            title = ax.get_title(loc=loc)
            if title:
                titles.append(dict(axis=idx, loc=loc, text=title))
    tight = fig.get_tightbbox(renderer)
    width, height = fig.get_size_inches() * 25.4
    report = dict(nominal_mm=[round(width, 1), round(height, 1)],
                  tight_mm=[round(tight.width * 25.4, 1), round(tight.height * 25.4, 1)],
                  tight_growth_mm=round(tight.width * 25.4 - width, 1),
                  tight_within_max=tight.width * 25.4 <= max_width_mm + .5,
                  max_width_mm=max_width_mm, panel_titles=titles,
                  left_titles_found=sum(t['loc'] == 'left' for t in titles),
                  min_font_pt=min(sizes) if sizes else None,
                  fonts_under_5pt=sorted({s for s in sizes if s < 5}),
                  pdf_fonttype=int(plt.rcParams['pdf.fonttype']))
    report['ok'] = (report['tight_within_max'] and not report['fonts_under_5pt']
                    and report['pdf_fonttype'] == 42)
    return report
