"""Final-export QA; imported third-party auditors retain their licences."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/figures/nature_r39_20261005'
STYLE = ROOT / 'src/figure_style_r39'

def run(script, args):
    p = subprocess.run([sys.executable, str(STYLE / script), *map(str, args)],
                       capture_output=True, text=True, encoding='utf-8')
    return dict(exit_code=p.returncode, report=json.loads(p.stdout))

def main():
    summary = {}
    for path in sorted(OUT.glob('Fig*.pdf')):
        if '.collision-overlay.' in path.name:
            continue
        stem = path.stem
        text = run('audit_pdf_text.py', [path, '--min-pt', '5', '--json'])
        collisions = run('audit_figure_collisions.py', [path, '--json',
            '--json-out', OUT / (stem + '.collisions.json'),
            '--overlay-pdf', OUT / (stem + '.collision-overlay.pdf')])
        with fitz.open(path) as doc:
            page = doc[0]
            images = len(page.get_images())
            text_chars = len(page.get_text().strip())
            fonts = page.get_fonts()
            width_mm, height_mm = page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72
        with Image.open(OUT / (stem + '.png')) as image:
            pixels, dpi = image.size, image.info.get('dpi')
        svg = ET.parse(OUT / (stem + '.svg')).getroot()
        texts = len(svg.findall('.//{http://www.w3.org/2000/svg}text'))
        vector_ok = images == 0 and text_chars > 100 and texts > 10
        raster_ok = all(abs(p / (m / 25.4) - 1200) < 1 for p, m in
                        zip(pixels, [width_mm, height_mm]))
        summary[stem] = dict(text=text, collisions=collisions,
            embedded_raster_images=images, extractable_text_chars=text_chars,
            editable_svg_text_nodes=texts, fonts=fonts,
            width_mm=width_mm, height_mm=height_mm, png_pixels=pixels, png_dpi=dpi,
            vector_ok=vector_ok, native_1200dpi_ok=raster_ok,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        print(stem, 'font:', text['exit_code'], 'collision:', collisions['exit_code'],
              'vector:', vector_ok, '1200dpi:', raster_ok, flush=True)
    source = run('validate_figure.py', [ROOT / 'src/plot_nature_figures_r39_20261005.py',
                                      '--profile', 'ipd-baker', '--json'])
    report = dict(source_validator=source, figures=summary,
                  visual_review='Separate actual rendered-page review is required')
    (OUT / 'final_artwork_technical_audit.json').write_text(
        json.dumps(report, indent=2), encoding='utf-8')
    if source['exit_code'] or any(r['text']['exit_code'] or r['collisions']['exit_code']
            or not r['vector_ok'] or not r['native_1200dpi_ok'] for r in summary.values()):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
