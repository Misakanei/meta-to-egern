import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from convert_asn import normalize_asns, published_asns, convert_asns


class ASNTests(unittest.TestCase):
    def test_validate_sort_and_deduplicate(self):
        self.assertEqual(normalize_asns(["as15169", "AS13335", "AS13335"], limit=20),
                         ["AS13335", "AS15169"])
        with self.assertRaises(ValueError):
            normalize_asns(["ASx"])
        with self.assertRaises(ValueError):
            normalize_asns([])
        with self.assertRaises(ValueError):
            normalize_asns([f"AS{i}" for i in range(21)], limit=20)

    def test_only_refresh_published_files(self):
        with TemporaryDirectory() as path:
            base = Path(path)
            (base / "AS15169.yaml").write_text("old")
            (base / "AS13335.yaml").write_text("old")
            (base / "README.md").write_text("noop")
            self.assertEqual(published_asns(base), ["AS13335", "AS15169"])
            with patch("convert_asn.fetch_one", side_effect=lambda n: "new " + n):
                updated = convert_asns("", base, refresh=True)
            self.assertEqual(updated, 2)
            self.assertEqual((base / "AS13335.yaml").read_text(), "new AS13335")
            self.assertEqual((base / "AS15169.yaml").read_text(), "new AS15169")

    def test_fail_closed_if_any_download_fails(self):
        with TemporaryDirectory() as path:
            base = Path(path)
            for name in ("AS1", "AS2"):
                (base / f"{name}.yaml").write_text("old")
            def fetch(name):
                if name == "AS2":
                    raise OSError("upstream download failed")
                return "new"
            with patch("convert_asn.fetch_one", side_effect=fetch):
                with self.assertRaises(OSError):
                    convert_asns("", base, refresh=True)
            self.assertEqual((base / "AS1.yaml").read_text(), "old")
            self.assertEqual((base / "AS2.yaml").read_text(), "old")

    def test_no_published_asn_is_noop(self):
        with TemporaryDirectory() as path:
            self.assertEqual(convert_asns("", Path(path), refresh=True), 0)


if __name__ == "__main__":
    unittest.main()
