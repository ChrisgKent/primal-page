import unittest

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


class TestValidateSchemeVersion(unittest.TestCase):
    def test_validate_schemeversion_valid(self):
        """
        Tests main/VERSION_PATTERN for valid scheme names
        """
        valid_versions = [
            "v1.0.0",
            "v2.3.4",
            "v10.20.30",
            "v1.0.0-beta",
            "v1.0.0-alpha",
            "v1.0.0-alpha1",
        ]

        for version in valid_versions:
            self.assertEqual(validate_schemeversion(version), version)

    def test_validate_schemeversion_invalid(self):
        """
        Tests main/VERSION_PATTERN for invalid scheme names
        """
        invalid_versions = [
            "v1",
            "v2.3",
            "v10.20",
            "v1.0.0.0",
            "V1",
            "artic-v1.0.0",
            "v1.0.0-",
            "v1.0.0-!",
            "v1.0.0-alpha!",
            "v1.0.0-A",
            "v1.0.0_alpha",
            "v1.0.0.alpha",
        ]

        for version in invalid_versions:
            with self.assertRaises(InvalidSchemeVersion):
                validate_schemeversion(version)


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
