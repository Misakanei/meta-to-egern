#!/usr/bin/env python3
"""Mirror all MetaCubeX YAML geosite/geoip categories into Egern rule sets.

The MetaCubeX 'meta' branch includes ASN .list/.mrs collections too.  Those
are cataloged but intentionally converted *on demand* because there are tens
of thousands of them.  See scripts/convert_asn.py.

Offline operation: upstream is a locally checked-out sparse Git repository.
All input files are parsed and validated before any generated rule is written.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import subprocess

import yaml

ROOTS = {
    "geo/geosite": "geosite",
    "geo/geoip": "geoip",
    "geo-lite/geosite": "lite/geosite",
    "geo-lite/geoip": "lite/geoip",
}
DOMAIN_RE = re.compile(r"^[A-Za-z0-9_*-]+(?:\.[A-Za-z0-9_*-]+)*$")
DOMAIN_FIELDS = ("domain_set", "domain_suffix_set", "domain_keyword_set",
                 "domain_regex_set", "domain_wildcard_set")


def convert_payload(payload):
    """Convert MetaCubeX domain payload into Egern sets, losslessly for known syntax."""
    if not isinstance(payload, list) or not payload:
        raise ValueError("Expected a nonempty domain payload array")
    groups = {key: set() for key in DOMAIN_FIELDS}
    for raw in payload:
        if not isinstance(raw, str):
            raise ValueError(f"Non-string domain rule: {raw!r}")
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
            raise ValueError(f"Empty rule: {entry!r}")
        if field in ("domain_set", "domain_suffix_set") and not DOMAIN_RE.fullmatch(value):
            raise ValueError(f"Invalid domain: {entry!r}")
        groups[field].add(value)

    result = {k: sorted(v) for k, v in groups.items() if v}
    if not result:
        raise ValueError("No usable domain rules")
    return result


def convert_ip_payload(payload):
    """Map IPv4 and IPv6 CIDRs to Egern native sets with address validation."""
    if not isinstance(payload, list) or not payload:
        raise ValueError("Expected a nonempty IP payload array")
    groups = {"ip_cidr_set": set(), "ip_cidr6_set": set()}
    for raw in payload:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"Invalid IP record: {raw!r}")
        try:
            network = ipaddress.ip_network(raw.strip(), strict=False)
        except ValueError as exc:
            raise ValueError(f"Unrecognized IP/CIDR rule {raw!r}") from exc
        key = "ip_cidr_set" if network.version == 4 else "ip_cidr6_set"
        groups[key].add(str(network))
    return {k: sorted(v) for k, v in groups.items() if v}


def parse_file(filename, kind):
    data = yaml.safe_load(filename.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or "payload" not in data:
        raise ValueError(f"Expected a YAML payload mapping in {filename}")
    payload = data["payload"]
    return convert_ip_payload(payload) if kind == "geoip" else convert_payload(payload)


def render_rule(upstream_path, groups):
    body = (
        "# Auto-generated from MetaCubeX/meta-rules-dat, branch meta.\n"
        f"# Source: https://github.com/MetaCubeX/meta-rules-dat/blob/meta/{upstream_path}\n"
        + yaml.safe_dump(groups, sort_keys=False, allow_unicode=True)
    )
    if yaml.safe_load(body) != groups:
        raise ValueError(f"Roundtrip verification failed for {upstream_path}")
    return body


def detect_asn_catalog(upstream):
    """Read *all* ASN category names via Git's tree, not GitHub's truncated API."""
    run = subprocess.run(
        ["git", "-C", str(upstream), "ls-tree", "-r", "--name-only",
         "HEAD", "--", "asn"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )
    names = set()
    for line in run.stdout.splitlines():
        m = re.fullmatch(r"asn/(AS\d+)\.list", line)
        if m:
            names.add(m.group(1))
    if not names:
        raise ValueError("Upstream ASN catalog is empty; sparse clone may have failed")
    return sorted(names, key=lambda v: int(v[2:]))


def build(upstream, aliases):
    generated = {}
    catalog = {}
    for source_dir, output_dir in ROOTS.items():
        inp_dir = upstream / source_dir
        if not inp_dir.is_dir():
            raise ValueError(f"Missing upstream directory: {inp_dir}")
        category_files = sorted(inp_dir.glob("*.yaml"))
        if not category_files:
            raise ValueError(f"No upstream YAML rules under {inp_dir}")
        kind = "geoip" if output_dir.endswith("geoip") else "geosite"
        names = {}
        for file in category_files:
            parts = parse_file(file, kind)
            upstream_path = f"{source_dir}/{file.name}"
            relative = f"{output_dir}/{file.name}"
            generated[relative] = render_rule(upstream_path, parts)
            names[file.stem] = {
                "path": f"rules/{relative}",
                "count": sum(len(v) for v in parts.values()),
            }
        catalog[output_dir] = names
        print(f"{output_dir}: {len(names)} categories")

    # Compatibility aliases for existing Egern installations.
    # Aliases don't limit the categories above.
    for name, slug in aliases.items():
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError(f"Unsafe alias filename: {name!r}")
        src = f"geosite/{slug}.yaml"
        if src not in generated:
            raise ValueError(f"Alias {name} references missing upstream category {slug}")
        generated[f"{name}.yaml"] = generated[src]

    asn_names = detect_asn_catalog(upstream)
    upstream_sha = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"],
        text=True
    ).strip()
    index = {
        "source": "MetaCubeX/meta-rules-dat",
        "branch": "meta",
        "upstream_sha": upstream_sha,
        "categories": {k: len(v) for k, v in catalog.items()},
        "asn_count": len(asn_names),
        "asn_mode": "on-demand; see scripts/convert_asn.py",
        "rules": catalog,
        "aliases": aliases,
    }
    return generated, index, asn_names


def publish(generated, index, asn_names, target, catalog_dir):
    """Write generated output only after the entire input tree was validated."""
    for relative, body in generated.items():
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Avoid changing unchanged files: makes Git updates much cheaper.
        if not destination.exists() or destination.read_text(encoding="utf-8") != body:
            destination.write_text(body, encoding="utf-8")

    expected = set(generated)
    for folder in (target / "geosite", target / "geoip",
                   target / "lite/geosite", target / "lite/geoip"):
        if folder.exists():
            for file in folder.glob("*.yaml"):
                if file.relative_to(target).as_posix() not in expected:
                    file.unlink()

    catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (catalog_dir / "asn.json").write_text(
        json.dumps({"count": len(asn_names), "categories": asn_names},
                   ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8"
    )


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--upstream", default="upstream")
    cli.add_argument("--out", default="rules")
    cli.add_argument("--catalog", default="catalog")
    cli.add_argument("--groups", default="groups.json")
    args = cli.parse_args()
    aliases = json.loads(Path(args.groups).read_text(encoding="utf-8"))
    if not isinstance(aliases, dict):
        raise ValueError("groups.json aliases must be an object")
    generated, index, asn = build(Path(args.upstream), aliases)
    publish(generated, index, asn, Path(args.out), Path(args.catalog))
    print(f"Built {len(generated)} Egern files, cataloged {len(asn)} ASN categories")


if __name__ == "__main__":
    main()
