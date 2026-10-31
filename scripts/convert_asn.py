#!/usr/bin/env python3
"""Publish selected MetaCubeX ASN CIDR lists as Egern-native rule sets.

ASN is a vast upstream collection (tens of thousands of categories).
Use Actions > Run workflow > ASN field, e.g. "AS13335,AS15169".
Do not confuse ASN IP prefix sets with Egern's separate ASN lookup engine.
"""
import argparse
from pathlib import Path
import re
import urllib.request
import yaml

from convert import convert_ip_payload, render_rule


def convert_asns(values, target):
    selected = [s.strip().upper() for s in values.split(",") if s.strip()]
    if not selected or len(selected) > 20:
        raise ValueError("Please provide between 1 and 20 AS numbers")
    if any(not re.fullmatch(r"AS[0-9]{1,10}", s) for s in selected):
        raise ValueError("ASN format must be AS13335 or AS13335,AS15169")
    all_output = {}
    for name in dict.fromkeys(selected):
        upstream_path = f"asn/{name}.list"
        url = f"https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/{upstream_path}"
        request = urllib.request.Request(url, headers={"User-Agent": "meta-to-egern/1.0"})
        with urllib.request.urlopen(request, timeout=60) as result:
            lines = [s.strip() for s in result.read().decode().splitlines()
                     if s.strip() and not s.lstrip().startswith("#")]
        groups = convert_ip_payload(lines)
        all_output[name] = render_rule(upstream_path, groups)
        print(f"{name}: {sum(len(v) for v in groups.values())} prefixes")
    target.mkdir(parents=True, exist_ok=True)
    for name, output in all_output.items():
        (target / (name + ".yaml")).write_text(output, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asn", required=True,
                        help="Comma-separated numbers, e.g. AS13335,AS15169")
    parser.add_argument("--out", default="rules/asn")
    args = parser.parse_args()
    convert_asns(args.asn, Path(args.out))


if __name__ == "__main__":
    main()
