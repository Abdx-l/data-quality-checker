# Data Quality Checker

Run declarative quality rules against a CSV and produce an HTML report with exact failure counts and up to five example rows per rule. Supported checks are `not_null`, `range`, `unique`, `regex`, `allowed_values`, and `row_count_change`.

```sh
python check.py examples/orders.csv examples/rules.json --report report.html
python -m unittest discover -s tests -v
```

Rules use JSON, which is also a valid YAML subset. The process exits with code 1 when a rule fails, making it useful in CI. `row_count_change` compares the current row count with a prior count supplied in the rules file.

