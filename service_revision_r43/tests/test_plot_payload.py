"""Serialization portability must not conceal a changed scientific payload."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from reproduce_revision_with_artwork_r43 import compare_csv_payload


class TestCSVPayload(unittest.TestCase):
    def test_newlines_only(self):
        a = b'label,value\ncase,1.2\n'
        b = b'label,value\r\ncase,1.2\r\n'
        result = compare_csv_payload(a, b)
        self.assertFalse(result['raw_byte_identical'])
        self.assertTrue(result['payload_identical_after_crlf_normalization'])
        self.assertTrue(result['source_values_match'])

    def test_machine_roundoff_is_recorded(self):
        result = compare_csv_payload(b'label,value\ncase,1.2000000000000002\n',
                                     b'label,value\r\ncase,1.2\r\n')
        self.assertFalse(result['payload_identical_after_crlf_normalization'])
        self.assertTrue(result['source_values_match'])
        self.assertGreater(result['maximum_scaled_numeric_error'], 0)
        self.assertLess(result['maximum_scaled_numeric_error'], 1e-12)

    def test_reject_number_label_and_space_edits(self):
        reference = b'label,value\r\ncase,1.2\r\n'
        for changed in [b'label,value\ncase,1.3\n',
                        b'label,value\nother,1.2\n',
                        b'label,value\ncase, 1.2\n']:
            with self.subTest(changed=changed):
                self.assertFalse(compare_csv_payload(changed, reference)
                                 ['source_values_match'])


if __name__ == '__main__':
    unittest.main()
