import pathlib
import unittest

from primal_page.validate import validate_bedfile, validate_hashes, validate_name

# Everything is correct in this
valid_info_path = pathlib.Path(
    "tests/test_input/validate/valid-scheme/400/v5.4.2/info.json"
)
# All hashes are incorrect
invalid_info_path = pathlib.Path(
    "tests/test_input/validate/invalid-scheme/400/v5.4.2/info.json"
)


class TestValidateHashes(unittest.TestCase):
    def test_validate_hashes(self):
        """
        Checks the hashes in the valid info.json
        """
        validate_hashes(valid_info_path)

    def test_validate_hashes_invalid(self):
        """
        Checks the hashes in the invalid info.json
        """
        with self.assertRaises(ValueError):
            validate_hashes(invalid_info_path)


class TestValidateName(unittest.TestCase):
    def test_validate_name(self):
        """
        Checks the name in the valid info.json
        """
        validate_name(valid_info_path)

    def test_validate_name_invalid(self):
        """
        Checks the name in the invalid info.json
        """
        with self.assertRaises((ValueError, FileNotFoundError)):
            validate_hashes(invalid_info_path)


class TestValidateBedFile(unittest.TestCase):
    def test_validate_bedfile(self):
        """
        Checks the bedfile in the valid info.json
        """
        validate_bedfile(valid_info_path.parent / "primer.bed")

    def test_validate_bedfile_invalid(self):
        """
        Checks the bedfile in the invalid info.json
        """
        with self.assertRaises((ValueError, IndexError)):
            validate_bedfile(invalid_info_path.parent / "primer.bed")
