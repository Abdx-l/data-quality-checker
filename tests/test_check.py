import csv
import json
from pathlib import Path
import tempfile
import unittest

from check import evaluate, render


class QualityTests(unittest.TestCase):
    def test_known_failures_and_safe_html(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv_path, config = root / "data.csv", root / "rules.json"
            with csv_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["id", "amount", "name", "status"])
                for i in range(20):
                    writer.writerow([i if i < 17 else "", "bad" if i < 3 else "2", "<script>" if i == 0 else "Jane", "yes"])
            config.write_text(json.dumps({"rules": [
                {"type": "not_null", "column": "id"},
                {"type": "range", "column": "amount", "min": 0, "max": 10},
                {"type": "unique", "column": "id"},
                {"type": "regex", "column": "name", "pattern": "[A-Za-z]+"},
                {"type": "allowed_values", "column": "status", "values": ["no"]},
                {"type": "row_count_change", "previous": 10, "max_fraction": 0.2}
            ]}), encoding="utf-8")
            count, results = evaluate(csv_path, config)
            self.assertEqual(count, 20)
            self.assertEqual([r["failed_count"] for r in results], [3, 3, 2, 1, 20, 1])
            page = render(count, results)
            self.assertIn("&lt;script&gt;", page)
            self.assertNotIn("<script>", page)
            self.assertEqual(len(results[4]["samples"]), 5)


if __name__ == "__main__":
    unittest.main()

