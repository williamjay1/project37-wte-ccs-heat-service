"""Contract tests, not new process-validation evidence."""
from pathlib import Path
import hashlib, importlib.util, json, unittest

ROOT = Path(__file__).resolve().parents[1]

class RepositoryContract(unittest.TestCase):
    def test_six_frozen_inputs_match_provenance(self):
        sources = json.loads((ROOT / 'docs/DATA_SOURCES.json').read_text(encoding='utf-8'))
        self.assertEqual(len(sources['inputs']), 6)
        for record in sources['inputs']:
            with self.subTest(record=record['path']):
                self.assertEqual(hashlib.sha256((ROOT / record['path']).read_bytes()).hexdigest(), record['sha256'])

    def test_cleaned_csv_not_seeded(self):
        self.assertFalse((ROOT / 'datasets/hagenholz_monthly_clean_r35_20261002.csv').exists())
        self.assertTrue((ROOT / 'reference_results/hagenholz_monthly_clean_r35_20261002.csv').is_file())

    def test_citation_refuses_unreviewed_unknown_authors(self):
        spec = importlib.util.spec_from_file_location('citation', ROOT / 'tools/prepare_citation.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        record = json.loads((ROOT / 'publication_metadata.json').read_text(encoding='utf-8'))
        if record.get('human_release_review_complete') is not True:
            with self.assertRaises(ValueError):
                module.build(record)

    def test_no_bundled_source_documents_or_private_submission(self):
        self.assertFalse((ROOT / 'submission').exists())
        self.assertFalse(list(ROOT.rglob('*.xlsx')))
        self.assertFalse(list(ROOT.rglob('*.docx')))
        self.assertFalse(list(ROOT.rglob('*.tex')))

    def test_mixed_licenses_retained(self):
        self.assertTrue((ROOT / 'src/figure_style_r39/scienceplots_LICENSE').is_file())
        self.assertTrue((ROOT / 'src/figure_style_r39/baker_LICENSE').is_file())
        text = (ROOT / 'DATA_LICENSES.md').read_text(encoding='utf-8')
        self.assertIn('CC0', text)
        self.assertIn('Index C9', text)

if __name__ == '__main__':
    unittest.main()
