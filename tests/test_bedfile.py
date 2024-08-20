import pathlib
import unittest

from primal_page.bedfiles import (
    BEDFileResult,
    BedfileVersion,
    PrimerNameVersion,
    convert_v1_primernames_to_v2,
    determine_bedfile_version,
    determine_primername_version,
    validate_bedfile,
    validate_bedfile_line_structure,
)
from primal_page.errors import InvalidBedFileLine, PrimerNameError, PrimerVersionError


class TestBedfile(unittest.TestCase):
    v1bedfile = pathlib.Path("tests/test_input/v1.primer.bed")
    v2bedfile = pathlib.Path("tests/test_input/v2.primer.bed")
    v3bedfile = pathlib.Path("tests/test_input/v3.primer.bed")
    invalid_bedfile = pathlib.Path("tests/test_input/invalid.primer.bed")
    invalid_struct_bedfile = pathlib.Path("tests/test_input/invalid.struct.primer.bed")

    def test_validate_bedfile(self):
        # Test v1
        with self.assertRaises(InvalidBedFileLine):
            validate_bedfile(self.v1bedfile)
        # Test v2
        self.assertEqual(validate_bedfile(self.v2bedfile), BEDFileResult.VALID)
        # Test v3
        self.assertEqual(validate_bedfile(self.v3bedfile), BEDFileResult.VALID)
        # Test invalid raises
        with self.assertRaises(PrimerVersionError):
            validate_bedfile(self.invalid_bedfile)

        # Test invalid structure
        with self.assertRaises(InvalidBedFileLine):
            validate_bedfile(self.invalid_struct_bedfile)


class TestDeterminePrimernameVersion(unittest.TestCase):
    def test_determine_primername_version(self):
        test_cases = {
            # VALID V2 Names
            "artic-nCoV_1_LEFT_0": PrimerNameVersion.V2,
            "artic-nCoV_100_LEFT_99": PrimerNameVersion.V2,
            "marv-2023_1_LEFT_1": PrimerNameVersion.V2,
            "78h13h_0_RIGHT_0": PrimerNameVersion.V2,
            "artic-nCoV_100_RIGHT_99": PrimerNameVersion.V2,
            "artic-nCoV_1_LEFT_1": PrimerNameVersion.V2,
            # Valid V1 Names
            "artic-nCoV_1_LEFT": PrimerNameVersion.V1,
            "artic-nCoV_1_LEFT_alt": PrimerNameVersion.V1,
            "artic-nCoV_100_LEFT_ALT": PrimerNameVersion.V1,
            "marv-2023_100_RIGHT_ALT": PrimerNameVersion.V1,
            "yby17_1_LEFT": PrimerNameVersion.V1,
            "yby17_1_LEFT_alt": PrimerNameVersion.V1,
            "yby17_1_LEFT_ALT": PrimerNameVersion.V1,
            # Invalid Names
            "easyfail": PrimerNameVersion.INVALID,
            "marv-2023_1_RIGHT_2_alt": PrimerNameVersion.INVALID,
            "artic*nCoV_100_LEFT_99": PrimerNameVersion.INVALID,
            "": PrimerNameVersion.INVALID,
        }

        for primername, result in test_cases.items():
            self.assertEqual(determine_primername_version(primername), result)


class TestDeterminBedfileVersion(unittest.TestCase):
    v1line = ["test", "0", "10", "test_5_LEFT", "0", "+"]
    v2line = ["test", "0", "10", "test_5_LEFT", "0", "+", "ATCG"]
    v3line = ["test", "0", "10", "test_5_LEFT_1", "0", "+", "ATCG"]
    invalidbedline = ["test", "0", "10", "test-5-LEFT", "0", "+", "ATCG"]

    def test_determine_bedfile_version(self):
        # Test v1
        self.assertEqual(determine_bedfile_version([self.v1line]), BedfileVersion.V1)
        # Test v2
        self.assertEqual(determine_bedfile_version([self.v2line]), BedfileVersion.V2)
        # Test v3
        self.assertEqual(determine_bedfile_version([self.v3line]), BedfileVersion.V3)
        # Test invalid primername raises
        with self.assertRaises(PrimerNameError):
            determine_bedfile_version([self.invalidbedline])
        # Test mixed raises
        with self.assertRaises(PrimerVersionError):
            determine_bedfile_version([self.v2line, self.v3line])


class TestConvertV1PrimernamesToV2(unittest.TestCase):
    def test_convert_v1_primernames_to_v2_valid(self):
        valid_test_cases = {
            # Valid V1 Names
            "artic-nCoV_1_LEFT": "artic-nCoV_1_LEFT_0",
            "artic-nCoV_100_LEFT": "artic-nCoV_100_LEFT_0",
            "marv-2023_100_RIGHT": "marv-2023_100_RIGHT_0",
            "yby17_1_LEFT": "yby17_1_LEFT_0",
        }
        for primername, result in valid_test_cases.items():
            self.assertEqual(convert_v1_primernames_to_v2(primername, 0), result)

    def test_convert_v1_primernames_to_v2_invalid(self):
        invalid_test_cases: set = {
            # Valid V1 Names
            "artic-nCoV_1_LEFT_alt",
            "artic-nCoV_100_LEFT_ALT",
            "marv-2023_100_RIGHT_ALT",
            "yby17_1_LEFT_alt",
            "yby17_1_LEFT_ALT",
            "easyfail",
            "marv-2023_1_RIGHT_2_alt",
            "artic*nCoV_100_LEFT_99",
            "",
        }
        for primername in invalid_test_cases:
            with self.assertRaises(ValueError):
                convert_v1_primernames_to_v2(primername)


class TestValidateBedfileLineStructure(unittest.TestCase):
    v1bedfile = pathlib.Path("tests/test_input/v1.primer.bed")
    v2bedfile = pathlib.Path("tests/test_input/v2.primer.bed")
    v3bedfile = pathlib.Path("tests/test_input/v3.primer.bed")
    invalid_bedfile = pathlib.Path("tests/test_input/invalid.struct.primer.bed")

    def test_bed_file_structure_v3(self):
        """
        Test that the bed file structure is correct
        """
        with open(self.v3bedfile) as bedfile:
            for line in bedfile.readlines():
                self.assertTrue(validate_bedfile_line_structure(line))

    def test_bed_file_structure_v2(self):
        """
        Test that the bed file structure is correct
        """
        with open(self.v2bedfile) as bedfile:
            for line in bedfile.readlines():
                self.assertTrue(validate_bedfile_line_structure(line))

    def test_bed_file_structure_v1(self):
        """
        V1 Bedfiles are not supported in this index
        """
        with open(self.v1bedfile) as bedfile:
            results = [
                validate_bedfile_line_structure(line) for line in bedfile.readlines()
            ]
            self.assertFalse(all(results))

    def test_bed_file_structure_invalid(self):
        """
        Test that the bed file structure is correct
        """
        with open(self.invalid_bedfile) as bedfile:
            results = [
                validate_bedfile_line_structure(line) for line in bedfile.readlines()
            ]
            self.assertFalse(all(results))


if __name__ == "__main__":
    unittest.main()
