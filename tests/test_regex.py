import pathlib
import re
import unittest

from primal_page.bedfiles import (
    V1_PRIMERNAME,
    V2_PRIMERNAME,
    PrimerNameVersion,
    convert_v1_primernames_to_v2,
    determine_bedfile_version,
    determine_primername_version,
    validate_bedfile_line_structure,
)
from primal_page.schemas import (
    BedfileVersion,
    not_empty,
    validate_schemename,
    validate_schemeversion,
)


class TestRegex(unittest.TestCase):
    def test_SchemeNamePattern_valid(self):
        """
        Tests main/SCHEMENAME_PATTERN for valid scheme names
        """
        valid_names = {
            "artic-covid-400": "artic-covid-400",
            "mpx-2022": "mpx-2022",
            "midnight-bccdc-2021": "midnight-bccdc-2021",
            "primerscheme": "primerscheme",
        }

        for name, result in valid_names.items():
            self.assertEqual(validate_schemename(name), result)

    def test_SchemeNamePattern_invalid(self):
        """
        Tests main/SCHEMENAME_PATTERN for invalid scheme names
        """

        invalid_names = [
            "artic-covid-400-",
            "artic/covid-400-1",
            "artic-covid-400-1.0!",
            "*artic-covid-400-1.0",
        ]

        for name in invalid_names:
            with self.assertRaises(ValueError):
                validate_schemename(name)

    def test_VersionPattern_ValidVersions(self):
        """
        Tests main/VERSION_PATTERN for valid scheme names
        """
        valid_versions = [
            "v1.0.0",
            "v2.3.4",
            "v10.20.30",
        ]

        for version in valid_versions:
            self.assertEqual(validate_schemeversion(version), version)

    def test_VersionPattern_InvalidVersions(self):
        """
        Tests main/VERSION_PATTERN for invalid scheme names
        """
        invalid_versions = [
            "v1",
            "v2.3",
            "v10.20",
            "v1.0.0.0",
            "v1.0.0-beta",
            "V1",
            "artic-v1.0.0",
        ]

        for version in invalid_versions:
            with self.assertRaises(ValueError):
                validate_schemeversion(version)

    def test_V1PrimerName_ValidNames(self):
        """
        Tests main/V1_PRIMERNAME for valid primer names
        """
        valid_names = [
            "artic-nCoV_1_LEFT",
            "mpx_1_RIGHT",
            "artic-nCoV_100_LEFT_alt",
            "marv-2023_100_RIGHT_ALT",
            "artic-nCoV_1_LEFT",
        ]

        for name in valid_names:
            self.assertTrue(re.match(V1_PRIMERNAME, name))

    def test_V1PrimerName_InvalidNames(self):
        """
        Tests main/V1_PRIMERNAME for invalid primer names
        """
        invalid_names = [
            "artic-nCoV_1_LEFT_0",  # V2 format should fail
            "artic_nCoV_1_LEFT",  # to many _
            "artic*nCoV_100_LEFT_99",  # invalid character
            "marv-2023_RIGHT_2",  # missing amplicion number
            "artic-nCoV_-1_LEFT_alt",  # Negative amplicon number
        ]

        for name in invalid_names:
            self.assertFalse(re.match(V1_PRIMERNAME, name))

    def test_V2PrimerName_ValidNames(self):
        """
        Tests main/V2_PRIMERNAME for valid primer names
        """
        valid_names = [
            "artic-nCoV_1_LEFT_0",
            "mpx_1_RIGHT_100",
            "artic-nCoV_100_LEFT_99",
            "marv-2023_100_RIGHT_2",
            "artic-nCoV_1_LEFT_1",
        ]

        for name in valid_names:
            self.assertTrue(re.match(V2_PRIMERNAME, name))

    def test_V2PrimerName_InvalidNames(self):
        """
        Tests main/V2_PRIMERNAME for invalid primer names
        """
        invalid_names = [
            "artic-nCoV_1_LEFT",  # V1 format should fail
            "artic_nCoV_1_LEFT_0",  # to many _
            "artic*nCoV_100_LEFT_99",  # invalid character
            "marv-2023_RIGHT_2",  # missing amplicion number
            "artic-nCoV_-1_LEFT_0",  # Negative amplicon number
            "marv-2023_1_RIGHT_2_alt",  # alt should fail
        ]

        for name in invalid_names:
            self.assertFalse(re.match(V2_PRIMERNAME, name))


class TestNotEmpty(unittest.TestCase):
    def test_not_empty_full(self):
        test_cases = [[1], {1}, [1, 2], {10, 11}]
        for test_case in test_cases:
            self.assertEqual(not_empty(test_case), test_case)

    def test_not_empty_empty(self):
        test_cases = [[], {}, set(), ""]
        for test_case in test_cases:
            with self.assertRaises(ValueError):
                not_empty(test_case)


class TestDetermine_primername_version(unittest.TestCase):
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

    def test_convert_v1_primernames_to_v2_valid(self):
        valid_test_cases = {
            # Valid V1 Names
            "artic-nCoV_1_LEFT": "artic-nCoV_1_LEFT_0",
            "artic-nCoV_100_LEFT": "artic-nCoV_100_LEFT_0",
            "marv-2023_100_RIGHT": "marv-2023_100_RIGHT_0",
            "yby17_1_LEFT": "yby17_1_LEFT_0",
        }
        for primername, result in valid_test_cases.items():
            self.assertEqual(convert_v1_primernames_to_v2(primername), result)

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


class TestDeterminePrimerBedVersion(unittest.TestCase):
    v1bedfile = pathlib.Path("tests/test_input/v1.primer.bed")
    v2bedfile = pathlib.Path("tests/test_input/v2.primer.bed")
    v3bedfile = pathlib.Path("tests/test_input/v3.primer.bed")
    invalidbedfile = pathlib.Path("tests/test_input/invalid.primer.bed")

    def test_parse_v1_bedfile(self):
        """
        See if the correct bedfile version is returned
        """
        # Test v1
        self.assertEqual(determine_bedfile_version(self.v1bedfile), BedfileVersion.V1)

    def test_parse_v2_bedfile(self):
        # Test v2
        self.assertEqual(determine_bedfile_version(self.v2bedfile), BedfileVersion.V2)

    def test_parse_v3_bedfile(self):
        # Test v3
        self.assertEqual(determine_bedfile_version(self.v3bedfile), BedfileVersion.V3)

    def test_parse_invalid_bedfile(self):
        # Test invalid
        self.assertEqual(
            determine_bedfile_version(self.invalidbedfile), BedfileVersion.INVALID
        )


class TestValidateBedfileLineStructure(unittest.TestCase):
    v1bedfile = pathlib.Path("tests/test_input/v1.primer.bed")
    v2bedfile = pathlib.Path("tests/test_input/v2.primer.bed")
    v3bedfile = pathlib.Path("tests/test_input/v3.primer.bed")
    invalidbedfile = pathlib.Path("tests/test_input/invalid.struct.primer.bed")

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
        with open(self.invalidbedfile) as bedfile:
            results = [
                validate_bedfile_line_structure(line) for line in bedfile.readlines()
            ]
            self.assertFalse(all(results))


if __name__ == "__main__":
    unittest.main()
