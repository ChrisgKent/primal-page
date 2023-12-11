import unittest
import pathlib
import shutil
import json

from primal_page.main import create, find_config, find_primerbed, find_ref
from primal_page.schemas import SchemeStatus


class TestCreate(unittest.TestCase):
    def setUp(self) -> None:
        # Required IO params
        self.schemepath = pathlib.Path("tests/test_input/test_covid")
        self.output = pathlib.Path("tests/test_output/test_covid")

        # Required params
        self.ampliconsize = 400
        self.schemeversion = "v1.0.0"
        self.species = ["sars-cov-2"]
        self.schemestatus = SchemeStatus.DRAFT
        self.citations = ["test-citation:124"]
        self.authors = ["artic"]
        self.schemename = "test-data-covid"

        # Parsed / optional params
        self.primerbed = pathlib.Path("tests/test_input/test_covid/primer.bed")
        self.reference = pathlib.Path("tests/test_input/test_covid/reference.fasta")
        self.configpath = pathlib.Path("tests/test_input/test_covid/config.json")
        self.algorithmversion = "primalscheme-test"
        self.description = "test-description"
        self.derivedfrom = "test-derivedfrom"

        # Clean up any previous test runs
        if (self.output / self.schemename).exists():
            shutil.rmtree(self.output / self.schemename)

    def test_create_minimal(self):
        """Test the creation of the scheme, using the config and required params"""

        # Run the create function
        create(
            schemepath=self.schemepath,
            output=self.output,
            ampliconsize=self.ampliconsize,
            schemeversion=self.schemeversion,
            species=self.species,
            schemestatus=self.schemestatus,
            citations=self.citations,
            authors=self.authors,
            schemename=self.schemename,
            reference=None,
        )

        # Check the output files exist
        self.assertTrue(
            (
                self.output
                / self.schemename
                / str(self.ampliconsize)
                / self.schemeversion
            ).exists()
        )

        # Check the info file exists
        self.assertTrue(
            (
                self.output
                / self.schemename
                / str(self.ampliconsize)
                / self.schemeversion
                / "info.json"
            ).exists()
        )

        # Check the details in the info file are correct
        info = json.loads(
            open(
                self.output
                / self.schemename
                / str(self.ampliconsize)
                / self.schemeversion
                / "info.json"
            ).read()
        )
        # Check the main fields are correct
        self.assertEqual(info["schemename"], self.schemename)
        self.assertEqual(info["ampliconsize"], self.ampliconsize)
        self.assertEqual(info["schemeversion"], self.schemeversion)

        # Check the optional fields are correct
        self.assertEqual(info["status"], self.schemestatus.value)
        self.assertEqual(info["authors"], self.authors)
        self.assertEqual(info["citations"], self.citations)
        self.assertEqual(info["species"], self.species)

        # Test the non provided fields are correct
        self.assertEqual(
            info["algorithmversion"], "primalscheme3:1.0.0"
        )  # parsed from config
        self.assertEqual(info["description"], None)
        self.assertEqual(info["derivedfrom"], None)


class Test_Find(unittest.TestCase):
    def setUp(self) -> None:
        self.schemepath = pathlib.Path("tests/test_input/test_covid")
        self.found_files = [x for x in self.schemepath.rglob("*")]

    def test_find_ref(self):
        """
        Test the find_reference function can find a single reference file
        """
        result = find_ref(
            cli_reference=None, found_files=self.found_files, schemepath=self.schemepath
        )
        # See if it can find the reference file
        self.assertEqual(
            result, pathlib.Path("tests/test_input/test_covid/reference.fasta")
        )

        # See if it can find the given reference file
        resultcli = find_ref(
            cli_reference=pathlib.Path(
                "tests/test_input/test_covid/primer.bed"
            ),  # Provide a different file # Might fail in future when ref is validated
            found_files=self.found_files,
            schemepath=self.schemepath,
        )
        self.assertEqual(
            resultcli, pathlib.Path("tests/test_input/test_covid/primer.bed")
        )

        # Test fail when given a file with two refs
        with self.assertRaises(FileNotFoundError):
            new_schemepath = pathlib.Path(
                "tests/test_input"
            )  # This dir contains two schemes dirs
            new_found_files = [x for x in new_schemepath.rglob("*")]
            find_ref(None, new_found_files, new_schemepath)

        # Test fail when given a file that doesn't exist
        with self.assertRaises(FileNotFoundError):
            find_ref(
                cli_reference=pathlib.Path(
                    "tests/test_input/test_covid/missingref.fasta"
                ),
                found_files=self.found_files,
                schemepath=self.schemepath,
            )

    def test_find_primerbed(self):
        """
        Test the find_primerbed function can find a single primerbed file
        """
        result = find_primerbed(
            cli_primerbed=None,
            found_files=self.found_files,
            schemepath=self.schemepath,
        )
        # See if it can find the primerbed file
        self.assertEqual(result, pathlib.Path("tests/test_input/test_covid/primer.bed"))

        # See if it can find the given primerbed file
        resultcli = find_primerbed(
            cli_primerbed=pathlib.Path(
                "tests/test_input/test_covid/primer.bed"
            ),  # Provide a different file # Might fail in future when ref is validated
            found_files=self.found_files,
            schemepath=self.schemepath,
        )
        self.assertEqual(
            resultcli, pathlib.Path("tests/test_input/test_covid/primer.bed")
        )

        # Test fail when given a file with two refs
        with self.assertRaises(FileNotFoundError):
            new_schemepath = pathlib.Path("tests/test_input")
            new_found_files = [x for x in new_schemepath.rglob("*")]
            find_primerbed(None, new_found_files, new_schemepath)

        # Test fail when given a file that doesn't exist
        with self.assertRaises(FileNotFoundError):
            find_primerbed(
                cli_primerbed=pathlib.Path("tests/test_input/test_covid/missing.bed"),
                found_files=self.found_files,
                schemepath=self.schemepath,
            )

    def test_find_config(self):
        """
        Test the find_config function can find a single config file
        """
        result = find_config(
            cli_config=None,
            found_files=self.found_files,
            schemepath=self.schemepath,
        )
        # See if it can find the config file
        self.assertEqual(
            result, pathlib.Path("tests/test_input/test_covid/config.json")
        )

        # See if it can find the given config file
        resultcli = find_config(
            cli_config=pathlib.Path(
                "tests/test_input/test_covid/config.json"
            ),  # Provide a different file # Might fail in future when ref is validated
            found_files=self.found_files,
            schemepath=self.schemepath,
        )
        self.assertEqual(
            resultcli, pathlib.Path("tests/test_input/test_covid/config.json")
        )

        # Test fail when given a file with two refs
        with self.assertRaises(FileNotFoundError):
            new_schemepath = pathlib.Path("tests/test_input")
            new_found_files = [x for x in new_schemepath.rglob("*")]
            find_config(None, new_found_files, new_schemepath)

        # Test fail when given a file that doesn't exist
        with self.assertRaises(FileNotFoundError):
            find_config(
                cli_config=pathlib.Path("tests/test_input/test_covid/missing.json"),
                found_files=self.found_files,
                schemepath=self.schemepath,
            )


if __name__ == "__main__":
    unittest.main()
