import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from convert import convert_payload


class ConverterTests(unittest.TestCase):
    def test_converts_and_deduplicates(self):
        output = convert_payload([
            "+.instagram.com", "+.cdninstagram.com",
            "graph.instagram.com", "full:api.example.com",
            "domain:example.net", "keyword:instagram",
            r"regexp:^test\.example\.com$", "*.example.org",
            "+.instagram.com"
        ])
        self.assertEqual(output["domain_suffix_set"], [
            "cdninstagram.com", "example.net", "instagram.com"])
        self.assertEqual(output["domain_set"], [
            "api.example.com", "graph.instagram.com"])
        self.assertEqual(output["domain_keyword_set"], ["instagram"])
        self.assertEqual(output["domain_wildcard_set"], ["*.example.org"])
        self.assertEqual(output["domain_regex_set"], [r"^test\.example\.com$"])

    def test_reject_unknown_rule(self):
        with self.assertRaises(ValueError):
            convert_payload(["unknown:foo"])

    def test_reject_empty(self):
        with self.assertRaises(ValueError):
            convert_payload([])


if __name__ == "__main__":
    unittest.main()
