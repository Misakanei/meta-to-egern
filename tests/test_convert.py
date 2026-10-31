import ipaddress
import sys
from pathlib import Path
import unittest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from convert import convert_payload, convert_ip_payload, render_rule


class ConverterTests(unittest.TestCase):
    def test_domains(self):
        result = convert_payload([
            "+.instagram.com", "+.cdninstagram.com",
            "graph.instagram.com", "full:api.example.com",
            "domain:example.net", "keyword:instagram",
            r"regexp:^test\.example\.com$", "*.example.org",
            "+.instagram.com"
        ])
        self.assertEqual(result["domain_suffix_set"],
                         ["cdninstagram.com", "example.net", "instagram.com"])
        self.assertEqual(result["domain_set"],
                         ["api.example.com", "graph.instagram.com"])
        self.assertEqual(result["domain_keyword_set"], ["instagram"])
        self.assertEqual(result["domain_wildcard_set"], ["*.example.org"])
        self.assertEqual(result["domain_regex_set"], [r"^test\.example\.com$"])

    def test_ip_v4_v6_and_dedup(self):
        r = convert_ip_payload([
            "1.1.1.0/24", "1.1.1.0/24", "2001:db8::/32",
            "8.8.8.8"
        ])
        self.assertEqual(r["ip_cidr_set"], ["1.1.1.0/24", "8.8.8.8/32"])
        self.assertEqual(r["ip_cidr6_set"], ["2001:db8::/32"])
        self.assertEqual(
            yaml.safe_load(render_rule("geo/geoip/test.yaml", r)), r
        )

    def test_invalid_ip(self):
        with self.assertRaises(ValueError):
            convert_ip_payload(["example.com"])

    def test_invalid_domain_syntax(self):
        with self.assertRaises(ValueError):
            convert_payload(["unrecognized:whatever"])

    def test_empty(self):
        with self.assertRaises(ValueError):
            convert_payload([])
        with self.assertRaises(ValueError):
            convert_ip_payload([])


if __name__ == "__main__":
    unittest.main()
