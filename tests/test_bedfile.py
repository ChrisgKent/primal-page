from primal_page.schemas import validate_bedfile, BEDFILERESULT

import unittest
import pathlib


class TestBedfile(unittest.TestCase):
    v1bedfile = pathlib.Path("tests/test_input/v1.primer.bed")
    v2bedfile = pathlib.Path("tests/test_input/v2.primer.bed")
    v3bedfile = pathlib.Path("tests/test_input/v3.primer.bed")
    invalidbedfile = pathlib.Path("tests/test_input/invalid.primer.bed")
    invalidstructbedfile = pathlib.Path("tests/test_input/invalid.struct.primer.bed")

    def test_validate_bedfile(self):
        # Test v1
        self.assertEqual(
            validate_bedfile(self.v1bedfile), BEDFILERESULT.INVALID_STRUCTURE
        )
        # Test v2
        self.assertEqual(validate_bedfile(self.v2bedfile), BEDFILERESULT.VALID)
        # Test v3
        self.assertEqual(validate_bedfile(self.v3bedfile), BEDFILERESULT.VALID)
        # Test invalid
        self.assertEqual(
            validate_bedfile(self.invalidbedfile), BEDFILERESULT.INVALID_VERSION
        )
        # Test invalid structure
        self.assertEqual(
            validate_bedfile(self.invalidstructbedfile),
            BEDFILERESULT.INVALID_STRUCTURE,
        )


if __name__ == "__main__":
    unittest.main()
