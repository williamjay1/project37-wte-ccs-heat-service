"""Origin balances and deliberate comparison-mutation tests."""
from pathlib import Path
import importlib.util
import json
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'src'/filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


balance = module('origin', 'audit_near_neighbor_accounting_r47_20261011.py')
runner = module('r47runner', 'reproduce_fulltext_revision_r47_20261011.py')


class OriginAccounting(unittest.TestCase):
    def test_limits_and_mass_conservation(self):
        for f in [0., .2, .45, 1.]:
            for r in [0., .442, .527, 1.]:
                b = balance.normalized_balance(f, r)
                self.assertAlmostEqual(b['captured_fossil']+b['emitted_fossil'], f)
                self.assertAlmostEqual(b['captured_biogenic']+b['emitted_biogenic'], 1-f)
                self.assertAlmostEqual(b['emitted_fossil']-b['pooled_net_carbon'], b['captured_biogenic'])

    def test_invalid_fractions(self):
        for f, r in [(-.1,.5), (1.1,.5), (.4,-.1), (.4,1.1), (float('nan'),.5)]:
            with self.assertRaises(ValueError):
                balance.normalized_balance(f, r)

    def test_printed_not_private_plant(self):
        b = balance.normalized_balance(.45,.527)
        self.assertAlmostEqual(b['emitted_fossil'], .21285)
        self.assertAlmostEqual(b['pooled_net_carbon'], -.077)

    def test_frozen_numerical_mutation_is_rejected(self):
        ref = ROOT/'reference/near_neighbor_r47'
        with tempfile.TemporaryDirectory(prefix='r47-qa-') as directory:
            fresh = Path(directory)/'copy'
            shutil.copytree(ref, fresh)
            self.assertEqual(runner.compare(ref,fresh)['status'],'PASS')
            p = fresh/'audit.json'
            value = json.loads(p.read_text())
            value['financial_origin_diagnostic']['fossil_only_zero_scope_value_EUR2020_t'] += 1
            p.write_text(json.dumps(value))
            self.assertEqual(runner.compare(ref,fresh)['status'],'FAIL')


if __name__ == '__main__':
    unittest.main()
