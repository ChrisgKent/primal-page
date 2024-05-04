import unittest

from primal_page.schemas import Links


class TestLinks(unittest.TestCase):
    def test_add_link(self):
        links = Links()

        # Add a link to all correct linkfield
        linktoadd = "https://example.com"
        for linkfield in links.model_fields.keys():
            links.append_link(linkfield, linktoadd)
            self.assertEqual(getattr(links, linkfield), [linktoadd])

        # Add a link to an incorrect linkfield
        with self.assertRaises(AttributeError):
            links.append_link("invalid", linktoadd)

    def test_remove_link(self):
        linktoremove = "https://example.com"
        links = Links(protocals=[linktoremove])

        # Remove the link from protocals
        links.remove_link("protocals", linktoremove)
        self.assertEqual(links.protocals, [])

        # Remove a link from an incorrect linkfield
        with self.assertRaises(AttributeError):
            links.remove_link("invalid", linktoremove)

        # Remove a link that is not in the linkfield
        with self.assertRaises(ValueError):
            links.remove_link("protocals", linktoremove)


if __name__ == "__main__":
    unittest.main()
