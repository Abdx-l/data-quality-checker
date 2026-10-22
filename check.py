"""CSV data checks with a readable CI report."""
from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
import re


SUPPORTED = {"not_null", "range", "unique", "regex", "allowed_values", "row_count_change"}


def check(rows: list[dict[str, str]], columns: list[str], rules: list[dict]) -> list[dict]:
    findings = []
    for rule in rules:
        kind = rule.get("type")
        if kind not in SUPPORTED:
            raise ValueError(f"Unsupported rule: {kind}")
        column = rule.get("column")
        if kind != "row_count_change" and column not in columns:
            raise ValueError(f"Missing column: {column}")
        failed = []
        if kind == "row_count_change":
            prior = int(rule["previous"])
            limit = float(rule.get("max_fraction", 0.2))
            if prior < 0 or not 0 <= limit <= 1:
                raise ValueError("Invalid row count baseline or threshold")
            if abs(len(rows) - prior) / max(prior, 1) > limit:
                failed = [{"row": 0, "values": {"previous": prior, "current": len(rows)}}]
        else:
            seen = set()
            for index, row in enumerate(rows, 2):
                value = row[column] or ""
                bad = False
                if kind == "not_null":
                    bad = not value.strip()
                elif kind == "unique":
                    bad = value in seen
                    seen.add(value)
                elif kind == "range":
                    try:
                        number = float(value)
                        bad = not (number == number and float(rule["min"]) <= number <= float(rule["max"]))
                    except (ValueError, TypeError):
                        bad = True
                elif kind == "regex":
                    bad = re.fullmatch(rule["pattern"], value) is None
                elif kind == "allowed_values":
                    bad = value not in rule["values"]
                if bad:
                    failed.append({"row": index, "values": dict(row)})
        findings.append({"rule": rule, "failed_count": len(failed), "samples": failed[:5]})
    return findings


def evaluate(csv_path: Path, rules_path: Path) -> tuple[int, list[dict]]:
    config = json.loads(rules_path.read_text(encoding="utf-8"))
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV needs distinct headers")
        rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError("CSV row has more fields than its header")
    return len(rows), check(rows, reader.fieldnames, config["rules"])


def render(count: int, findings: list[dict]) -> str:
    sections = []
    for item in findings:
        label = html.escape(json.dumps(item["rule"], ensure_ascii=False))
        samples = "".join(f"<li>Row {sample['row']}: <code>{html.escape(json.dumps(sample['values'], ensure_ascii=False))}</code></li>" for sample in item["samples"])
        sections.append(f"<section><h2>{label}</h2><p>Failures: {item['failed_count']}</p><ol>{samples}</ol></section>")
    return "<!doctype html><html lang='en'><meta charset='utf-8'><title>Data quality</title><h1>Data quality report</h1>" + f"<p>Rows: {count}</p>" + "".join(sections) + "</html>"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("rules", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        count, findings = evaluate(args.csv, args.rules)
    except (ValueError, KeyError, json.JSONDecodeError) as ex:
        parser.error(str(ex))
    args.report.write_text(render(count, findings), encoding="utf-8")
    total = sum(item["failed_count"] for item in findings)
    print(f"{count} rows, {total} rule failures; {args.report}")
    raise SystemExit(1 if total else 0)

