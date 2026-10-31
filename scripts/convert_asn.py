#!/usr/bin/env python3
"""Publish selected MetaCubeX ASN CIDR lists as Egern-native rule sets.

ASN is a vast upstream collection (tens of thousands of categories).
Use Actions > Run workflow > ASN field; daily --refresh updates published files.
Do not confuse ASN IP prefix sets with Egern's separate ASN lookup engine.
"""
import argparse
from pathlib import Path
import re
import urllib.request
import yaml

from convert import convert_ip_payload, render_rule


def normalize_asns(raw_names, *, limit=None):
    """Validate AS numbers from either a user selection or published filenames."""
    names = [str(s).strip().upper() for s in raw_names if str(s).strip()]
    if not names:
        if limit is not None:
            raise ValueError("Provide at least one ASN (e.g. AS13335)")
        return []
    if any(not re.fullmatch(r"AS[0-9]{1,10}", n) for n in names):
        raise ValueError("ASN format must be AS13335 or AS13335,AS15169")
    names = sorted(set(names), key=lambda v: int(v[2:]))
    if limit is not None and len(names) > limit:
        raise ValueError(f"Maximum {limit} ASN categories per manual run")
    return names


def published_asns(target):
    """Only auto-refresh previously published ASN rules; do not expand 82k files."""
    if not target.exists():
        return []
    return normalize_asns(
        [p.stem for p in target.glob("AS*.yaml") if p.is_file()]
    )


def fetch_one(name):
    """Fetch an upstream CIDR snapshot; fail closed on an invalid/missing list."""
    upstream_path = f"asn/{name}.list"
    url = f"https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/{upstream_path}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "meta-to-egern/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        lines = [
            s.strip() for s in response.read().decode("utf-8-sig").splitlines()
            if s.strip() and not s.lstrip().startswith("#")
        ]
    groups = convert_ip_payload(lines)
    print(f"{name}: {sum(len(v) for v in groups.values())} prefixes")
    return render_rule(upstream_path, groups)


def convert_asns(values, target, *, refresh=False):
    """Download and validate all selected snapshots BEFORE overwriting any file.

    Manual mode publishes at most 20 ASN categories. Refresh mode discovers
    already-published categories and updates those only, every day.
    """
    if refresh:
        names = published_asns(target)
    else:
        names = normalize_asns(values.split(","), limit=20)
    if not names:
        print("No previously published ASN files; nothing to refresh")
        return 0

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(8, len(names))) as pool:
        contents = list(pool.map(fetch_one, names))

    target.mkdir(parents=True, exist_ok=True)
    changed = 0
    for name, content in zip(names, contents):
        dest = target / f"{name}.yaml"
        if not dest.exists() or dest.read_text(encoding="utf-8") != content:
            dest.write_text(content, encoding="utf-8")
            changed += 1
    print(f"ASN results: {len(names)} checked, {changed} updated")
    return changed


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--asn", help="Up to 20 ASN numbers, e.g. AS13335,AS15169")
    group.add_argument("--refresh", action="store_true",
                       help="Refresh every previously published ASN snapshot")
    parser.add_argument("--out", default="rules/asn")
    args = parser.parse_args()
    convert_asns(args.asn or "", Path(args.out), refresh=args.refresh)


if __name__ == "__main__":
    main()
