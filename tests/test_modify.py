import unittest
from copy import deepcopy

from primal_page.schemas import (
    BedfileVersion,
    Collection,
    Info,
    PrimerClass,
    SchemeStatus,
)

base_info = Info(
    ampliconsize=400,
    schemeversion="v1.0.0",
    schemename="test",
    primer_bed_md5="hello",
    reference_fasta_md5="world",
    status=SchemeStatus.DRAFT,
    citations=set("nobel-prize"),
    authors=["artic", "developer"],
    algorithmversion="test",
    species=set("sars-cov-2"),
    articbedversion=BedfileVersion.V3,
    collections=set([Collection.WHOLE_GENOME]),
    primerclass=PrimerClass.PRIMERSCHEMES,
)


class TestAddAuthor(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_author_add_append(self):
        """Test adding an author to the Info object"""

        local_info = deepcopy(self.info)
        new_author = "test-author"

        # Check the author is not present
        self.assertNotIn(new_author, local_info.authors)

        # Append the author
        local_info.author_add(new_author, None)

        # Check the author is present at the end
        self.assertEqual(local_info.authors[-1], new_author)

    def test_author_add_insert(self):
        """Test adding an author to the Info object"""

        local_info = deepcopy(self.info)
        new_author = "test-author"
        new_index = 1

        # Check the author is not present
        self.assertNotIn(new_author, local_info.authors)

        # Insert the author
        local_info.author_add(new_author, new_index)

        # Check the author is present at the index
        self.assertEqual(local_info.authors[new_index], new_author)

    def test_author_add_invalid_index(self):
        """Test adding an author to the Info object with an invalid index"""

        local_info = deepcopy(self.info)
        new_author = "test-author"
        new_index = len(local_info.authors) + 1

        # Check the author is not present
        self.assertNotIn(new_author, local_info.authors)

        # Insert the author
        local_info.author_add(new_author, new_index)

        # Check the author is present at the end
        self.assertEqual(local_info.authors[-1], new_author)


class TestRemoveAuthor(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_author_remove_valid(self):
        """Test removing an author from the Info object"""

        local_info = deepcopy(self.info)
        author_to_remove = local_info.authors[0]

        # Check the author is present
        self.assertIn(author_to_remove, local_info.authors)

        # Remove the author
        local_info.author_remove(author_to_remove)

        # Check the author is not present
        self.assertNotIn(author_to_remove, local_info.authors)

    def test_author_remove_invalid(self):
        """Test removing an author from the Info object"""

        local_info = deepcopy(self.info)
        author_to_remove = "invalid-author"

        # Check the author is not present
        self.assertNotIn(author_to_remove, local_info.authors)

        # Remove the author
        with self.assertRaises(ValueError):
            local_info.author_remove(author_to_remove)


class TestReorderAuthors(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_author_reorders_valid(self):
        """Test reordering authors in the Info object"""

        local_info = deepcopy(self.info)
        new_order = [1, 0]

        # Check the authors are in the correct order
        self.assertEqual(local_info.authors, ["artic", "developer"])

        # Reorder the authors
        local_info.author_reorders(new_order)

        # Check the authors are in the correct order
        self.assertEqual(local_info.authors, ["developer", "artic"])

    def test_author_reorders_invalid_index(self):
        """Test reordering authors in the Info object with an invalid index"""

        local_info = deepcopy(self.info)
        new_order = [1, 2]

        # Check the authors are in the correct order
        self.assertEqual(local_info.authors, ["artic", "developer"])

        # Reorder the authors
        with self.assertRaises(IndexError):
            local_info.author_reorders(new_order)

    def test_author_reorders_duplicate_index(self):
        """Test reordering authors in the Info object with a duplicate index"""

        local_info = deepcopy(self.info)
        new_order = [1, 1]

        # Check the authors are in the correct order
        self.assertEqual(local_info.authors, ["artic", "developer"])

        # Reorder the authors
        with self.assertRaises(ValueError):
            local_info.author_reorders(new_order)

    def test_no_authors_lost(self):
        """Test reordering authors in the Info object with a duplicate index"""

        local_info = deepcopy(self.info)
        new_order = [1]

        # Check the authors are in the correct order
        self.assertEqual(local_info.authors, ["artic", "developer"])

        # Reorder the authors
        local_info.author_reorders(new_order)

        # Check the authors are in the correct order
        self.assertEqual(local_info.authors, ["developer", "artic"])


class TestAddCitation(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_citation_add(self):
        """Test adding a citation to the Info object"""

        local_info = deepcopy(self.info)
        new_citation = "test-citation"

        # Check the citation is not present
        self.assertNotIn(new_citation, local_info.citations)

        # Append the citation
        local_info.citation_add(new_citation)

        # Check the citation is present at the end
        self.assertIn(new_citation, local_info.citations)


class TestRemoveCitation(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_citation_remove_valid(self):
        """Test removing a citation from the Info object"""

        local_info = deepcopy(self.info)
        citation_to_remove = next(iter(local_info.citations))

        # Check the citation is present
        self.assertIn(citation_to_remove, local_info.citations)

        # Remove the citation
        local_info.citation_remove(citation_to_remove)

        # Check the citation is not present
        self.assertNotIn(citation_to_remove, local_info.citations)

    def test_citation_remove_invalid(self):
        """Test removing a citation from the Info object"""

        local_info = deepcopy(self.info)
        citation_to_remove = "invalid-citation"

        # Check the citation is not present
        self.assertNotIn(citation_to_remove, local_info.citations)

        # Remove the citation
        with self.assertRaises(KeyError):
            local_info.citation_remove(citation_to_remove)


class TestAddCollection(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_collection_add(self):
        """Test adding a collection to the Info object"""

        local_info = deepcopy(self.info)
        new_collection = Collection.ARTIC

        # Check the collection is not present
        self.assertNotIn(new_collection, local_info.collections)

        # Append the collection
        local_info.collection_add(new_collection)

        # Check the collection is present at the end
        self.assertIn(new_collection, local_info.collections)


class TestRemoveCollection(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_collection_remove_valid(self):
        """Test removing a collection from the Info object"""

        local_info = deepcopy(self.info)
        collection_to_remove = next(iter(local_info.collections))

        # Check the collection is present
        self.assertIn(collection_to_remove, local_info.collections)

        # Remove the collection
        local_info.collection_remove(collection_to_remove)

        # Check the collection is not present
        self.assertNotIn(collection_to_remove, local_info.collections)

    def test_collection_remove_invalid(self):
        """Test removing a collection from the Info object"""

        local_info = deepcopy(self.info)
        collection_to_remove = Collection.MULTI_TARGET

        # Check the collection is not present
        self.assertNotIn(collection_to_remove, local_info.collections)

        # Remove the collection
        with self.assertRaises(KeyError):
            local_info.collection_remove(collection_to_remove)


class TestChangeDescription(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_change_description(self):
        """Test changing the description of the Info object"""

        local_info = deepcopy(self.info)
        new_description = "test-description"

        # Check the description is not present
        self.assertNotEqual(new_description, local_info.description)

        # Change the description
        local_info.description = new_description

        # Check the description is present
        self.assertEqual(new_description, local_info.description)


class TestChangeStatus(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_change_status(self):
        """Test changing the status of the Info object"""

        local_info = deepcopy(self.info)
        new_status = SchemeStatus.VALIDATED

        # Check the status is not present
        self.assertNotEqual(new_status, local_info.status)

        # Change the status
        local_info.status = new_status

        # Check the status is present
        self.assertEqual(new_status, local_info.status)


class TestChangeLicense(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_change_license(self):
        """Test changing the license of the Info object"""

        local_info = deepcopy(self.info)
        new_license = "test-license"

        # Check the license is not present
        self.assertNotEqual(new_license, local_info.license)

        # Change the license
        local_info.license = new_license

        # Check the license is present
        self.assertEqual(new_license, local_info.license)


class TestChangeDerivedFrom(unittest.TestCase):
    def setUp(self) -> None:
        self.info = base_info

    def test_change_derivedfrom(self):
        """Test changing the derivedfrom of the Info object"""

        local_info = deepcopy(self.info)
        new_derivedfrom = "test-derivedfrom"

        # Check the derivedfrom is not present
        self.assertNotEqual(new_derivedfrom, local_info.derivedfrom)

        # Change the derivedfrom
        local_info.derivedfrom = new_derivedfrom

        # Check the derivedfrom is present
        self.assertEqual(new_derivedfrom, local_info.derivedfrom)


if __name__ == "__main__":
    unittest.main()
