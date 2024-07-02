import re
import unittest

from primal_page.bedfiles import (
    V1_PRIMERNAME,
    V2_PRIMERNAME,
)
from primal_page.errors import (
    InvalidSchemeID,
    InvalidSchemeName,
    InvalidSchemeVersion,
)
from primal_page.schemas import (
    not_empty,
    validate_scheme_id,
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
            with self.assertRaises(InvalidSchemeName):
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
            with self.assertRaises(InvalidSchemeVersion):
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


class TestValidateSchemeID(unittest.TestCase):
    def test_valid_scheme_id(self):
        valid_scheme_id = ["test123/400/v1.0.0", "test123/1000/v1.0.0"]

        # Valid scheme ids
        for scheme_id in valid_scheme_id:
            self.assertEqual(tuple(scheme_id.split("/")), validate_scheme_id(scheme_id))

    def test_invalid_scheme_id_schemename(self):
        # Scheme ids with invalid scheme names
        invalid_scheme_id = ["test123-/400/v1.0.0", "test1A23/1000/v1.0.0"]

        # Invalid scheme ids
        for scheme_id in invalid_scheme_id:
            with self.assertRaises(InvalidSchemeID):
                validate_scheme_id(scheme_id)

    def test_invalid_scheme_id_ampliconsize(self):
        # Scheme ids with invalid ampliconsize
        invalid_scheme_id = ["test123/40a0/v1.0.0", "test123/10.00/v1.0.0"]

        # Invalid scheme ids
        for scheme_id in invalid_scheme_id:
            with self.assertRaises(InvalidSchemeID):
                validate_scheme_id(scheme_id)

    def test_invalid_scheme_id_schemeversion(self):
        # Scheme ids with invalid ampliconsize
        invalid_scheme_id = ["test123/400/v1", "test123/1000/1.0"]

        # Invalid scheme ids
        for scheme_id in invalid_scheme_id:
            with self.assertRaises(InvalidSchemeID):
                validate_scheme_id(scheme_id)

    def test_invalid_scheme_id_structure(self):
        # Scheme ids with invalid structure
        invalid_scheme_id = ["test123/400", "test123/1000/1.0/test"]

        # Invalid scheme ids
        for scheme_id in invalid_scheme_id:
            with self.assertRaises(InvalidSchemeID):
                validate_scheme_id(scheme_id)


if __name__ == "__main__":
    unittest.main()
