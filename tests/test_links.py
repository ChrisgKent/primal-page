import unittest

from primal_page.schemas import Links


class TestLinks(unittest.TestCase):
    def test_link_add(self):
        links = Links()

        # Add a link to all correct linkfield
        linktoadd = "https://example.com"
        for linkfield in links.model_fields.keys():
            links.append_link(linkfield, linktoadd)
            self.assertEqual(getattr(links, linkfield), [linktoadd])

        # Add a link to an incorrect linkfield
        with self.assertRaises(AttributeError):
            links.append_link("invalid", linktoadd)

    def test_link_remove(self):
        linktoremove = "https://example.com"
        links = Links(protocols=[linktoremove])

        # Remove the link from protocols
        links.link_remove("protocols", linktoremove)
        self.assertEqual(links.protocols, [])

        # Remove a link from an incorrect linkfield
        with self.assertRaises(AttributeError):
            links.link_remove("invalid", linktoremove)

        # Remove a link that is not in the linkfield
        with self.assertRaises(ValueError):
            links.link_remove("protocols", linktoremove)


if __name__ == "__main__":
    unittest.main()
