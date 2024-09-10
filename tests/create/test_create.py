import json
import pathlib
import shutil
import unittest

from primal_page.main import create
from primal_page.schemas import SchemeStatus


class TestCreate(unittest.TestCase):
    def setUp(self) -> None:
        # Required IO params
        self.schemepath = pathlib.Path("tests/test_input/test_covid")
        self.output = pathlib.Path("tests/test_output/test_covid")

        # Required params
        self.ampliconsize = 400
        self.schemeversion = "v1.0.0"
        self.species = [10]
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
            output=self.output,
            ampliconsize=self.ampliconsize,
            schemeversion=self.schemeversion,
            species=self.species,
            schemestatus=self.schemestatus,
            citations=self.citations,
            authors=self.authors,
            schemename=self.schemename,
            reference=self.reference,
            primerbed=self.primerbed,
            algorithmversion=self.algorithmversion,
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
            info["algorithmversion"], self.algorithmversion
        )  # parsed from config
        self.assertEqual(info["description"], None)
        self.assertEqual(info["derivedfrom"], None)


if __name__ == "__main__":
    unittest.main()
