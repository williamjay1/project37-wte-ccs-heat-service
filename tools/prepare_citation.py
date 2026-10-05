"""Create CFF only from genuine, human-reviewed contributor metadata."""
from pathlib import Path
import argparse, datetime, json, re

ROOT = Path(__file__).resolve().parents[1]

def text(value, label):
    if not isinstance(value, str) or not value.strip() or re.search(r'REPLACE|PLACEHOLDER|TBD|TODO|example\.|[<>\[\]]', value, re.I):
        raise ValueError('Supply a genuine value for ' + label)
    return value.strip()

def build(record):
    title = text(record.get('title'), 'title')
    version = text(record.get('version'), 'version')
    url = text(record.get('repository_url'), 'repository URL')
    if not re.fullmatch(r'https://github\.com/[^/]+/[^/]+/?', url):
        raise ValueError('Use an actual GitHub repository URL.')
    if record.get('human_release_review_complete') is not True:
        raise ValueError('Real contributor and license review is required before release metadata.')
    authors = record.get('authors')
    if not isinstance(authors, list) or not authors:
        raise ValueError('Supply real authors; a GitHub login is not inferred to be a researcher author.')
    date = text(record.get('date_released'), 'actual release date')
    datetime.date.fromisoformat(date)
    lines = ['cff-version: 1.2.0', 'type: software',
             'message: "Please cite the tested archived version when a DOI is available."',
             'title: ' + json.dumps(title), 'version: ' + json.dumps(version),
             'date-released: ' + json.dumps(date), 'repository-code: ' + json.dumps(url),
             'license: MIT', 'authors:']
    for author in authors:
        given = text(author.get('given-names'), 'author given-names')
        family = text(author.get('family-names'), 'author family-names')
        lines += ['  - given-names: ' + json.dumps(given), '    family-names: ' + json.dumps(family)]
        if author.get('affiliation'):
            lines.append('    affiliation: ' + json.dumps(text(author['affiliation'], 'affiliation')))
        if author.get('orcid'):
            orcid = text(author['orcid'], 'ORCID')
            if not re.fullmatch(r'https://orcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[\dX]', orcid):
                raise ValueError('Use the real ORCID URL; verify it separately.')
            lines.append('    orcid: ' + json.dumps(orcid))
    if record.get('version_doi'):
        doi = text(record['version_doi'], 'genuine version DOI')
        if not re.fullmatch(r'10\.\d{4,9}/\S+', doi):
            raise ValueError('Invalid DOI syntax; a syntactically valid value still needs actual resolution checking.')
        lines.append('doi: ' + json.dumps(doi))
    lines += ['keywords:', '  - waste-to-energy', '  - carbon capture',
              '  - district heating', '  - thermal service',
              'abstract: "Source-anchored necessary thermal-service screens and scenario calculations. Mixed input licenses are documented separately; this is not measured factory validation."']
    return '\n'.join(lines) + '\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', required=True)
    args = parser.parse_args()
    record = json.loads(Path(args.metadata).read_text(encoding='utf-8'))
    output = ROOT / 'CITATION.cff'
    if output.exists():
        raise FileExistsError('Do not silently overwrite citation metadata; make and review a versioned edit.')
    output.write_text(build(record), encoding='utf-8')
    print('Created CITATION.cff from supplied reviewed metadata; no deposit or DOI request performed.')

if __name__ == '__main__':
    main()
