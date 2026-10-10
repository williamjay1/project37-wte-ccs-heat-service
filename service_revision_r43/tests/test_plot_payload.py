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

    def test_reject_number_label_and_space_edits(self):
        reference = b'label,value\r\ncase,1.2\r\n'
        for changed in [b'label,value\ncase,1.3\n',
                        b'label,value\nother,1.2\n',
                        b'label,value\ncase, 1.2\n']:
            with self.subTest(changed=changed):
                self.assertFalse(compare_csv_payload(changed, reference)
                                 ['payload_identical_after_crlf_normalization'])


if __name__ == '__main__':
    unittest.main()
