#!/usr/bin/env python3
"""Convert MetaCubeX geosite YAML rule sets into Egern-native YAML.

Source: https://github.com/MetaCubeX/meta-rules-dat/tree/meta/geo/geosite
Failure-safe: all downloads and validations complete before writing any files.
"""
import argparse
import json
from pathlib import Path
import re
import urllib.request
import yaml

UPSTREAM = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/{slug}.yaml"
FIELDS = ("domain_set", "domain_suffix_set", "domain_keyword_set",
          "domain_regex_set", "domain_wildcard_set")
DOMAIN_RE = re.compile(r"^[A-Za-z0-9_*-]+(?:\.[A-Za-z0-9_*-]+)*$")


def convert_payload(payload):
    if not isinstance(payload, list) or not payload:
        raise ValueError("Expected a nonempty payload array")
    groups = {key: set() for key in FIELDS}
    for raw in payload:
        if not isinstance(raw, str):
            raise ValueError(f"Non-string rule: {raw!r}")
        entry = raw.strip()
        if not entry:
            continue
        if entry.startswith("+."):
            field, value = "domain_suffix_set", entry[2:]
        elif entry.startswith("full:"):
            field, value = "domain_set", entry[5:]
        elif entry.startswith("domain:"):
            field, value = "domain_suffix_set", entry[7:]
        elif entry.startswith("keyword:"):
            field, value = "domain_keyword_set", entry[8:]
        elif entry.startswith("regexp:"):
            field, value = "domain_regex_set", entry[7:]
        elif entry.startswith("regex:"):
            field, value = "domain_regex_set", entry[6:]
        elif entry.startswith("*."):
            field, value = "domain_wildcard_set", entry
        elif ":" in entry or entry.startswith((".", "+", "-")):
            raise ValueError(f"Unsupported geosite syntax: {entry!r}")
        else:
            field, value = "domain_set", entry

        value = value.strip()
        if not value:
            raise ValueError(f"Empty value in rule {entry!r}")
        if field in ("domain_set", "domain_suffix_set") and not DOMAIN_RE.fullmatch(value):
            raise ValueError(f"Invalid domain in {entry!r}")
        groups[field].add(value)

    result = {field: sorted(groups[field]) for field in FIELDS if groups[field]}
    if not result:
        raise ValueError("No rules found after conversion")
    return result


def fetch_rules(slug):
    if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9_!+@-]+", slug):
        raise ValueError(f"Invalid upstream category: {slug!r}")
    url = UPSTREAM.format(slug=slug)
    req = urllib.request.Request(url, headers={
        "User-Agent": "meta-to-egern-github-actions/1.0"
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        parsed = yaml.safe_load(response.read().decode("utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Not a YAML object: {url}")
    return url, convert_payload(parsed.get("payload"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", default="groups.json")
    parser.add_argument("--out", default="rules")
    args = parser.parse_args()
    categories = json.loads(Path(args.groups).read_text(encoding="utf-8"))
    if not isinstance(categories, dict) or not categories:
        raise ValueError("groups.json must be a nonempty object")

    # Do all remote work first; an upstream failure cannot overwrite existing output.
    result = {}
    for name, slug in categories.items():
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError(f"Invalid output filename: {name!r}")
        source_url, rules = fetch_rules(slug)
        content = (
            "# Auto-generated from MetaCubeX/meta-rules-dat; DO NOT EDIT.\n"
            f"# Source: {source_url}\n"
            f"# Rule counts: {', '.join(f'{field}={len(values)}' for field, values in rules.items())}\n"
            + yaml.safe_dump(rules, allow_unicode=True,
                             sort_keys=False, default_flow_style=False)
        )
        if yaml.safe_load(content) != rules:
            raise ValueError(f"YAML output failed validation: {name}")
        result[name + ".yaml"] = content
        print(f"{name}: {sum(len(values) for values in rules.values())} rules")

    target = Path(args.out)
    target.mkdir(parents=True, exist_ok=True)
    for filename, content in result.items():
        (target / filename).write_text(content, encoding="utf-8")
    for prior in target.glob("*.yaml"):
        if prior.name not in result:
            prior.unlink()
    print(f"Converted {len(result)} categories into {target}/")


if __name__ == "__main__":
    main()
