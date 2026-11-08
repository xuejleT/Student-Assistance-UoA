"""Synthetic GPA cases. No real student records are used."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/uoa-student-assistant/scripts/gpa.py"
TEMP_ROOT = Path(__file__).resolve().parents[1] / "tmp/test-gpa"
spec = importlib.util.spec_from_file_location("gpa", SCRIPT)
gpa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gpa)


def row(course="SAMPLE 100", grade="A", points=15, year=2026, term="Semester One", **extra):
    return dict(course=course, grade=grade, points=points, year=year, term=term, **extra)


class GeneralGpaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)

    def test_points_weighting(self):
        result = gpa.calculate([row(grade="A+"), row("SAMPLE 200", "B", 30)])
        self.assertEqual(result["eligible_points"], 45)
        self.assertEqual(result["calculated_gpa"], 6.3333)

    def test_repeated_attempts_are_retained(self):
        result = gpa.calculate([row(grade="D+", year=2025), row(grade="A")])
        self.assertEqual(result["calculated_gpa"], 4)
        self.assertEqual(result["selected_rows"], 2)

    def test_withdrawal_boundary(self):
        result = gpa.calculate([row(grade="W", year=2022), row(grade="W", year=2023),
                                row("SAMPLE 200", "A+")])
        self.assertEqual(result["eligible_points"], 30)
        self.assertEqual(result["calculated_gpa"], 4.5)

    def test_pass_pending_and_noncredit(self):
        result = gpa.calculate([row(grade="P"), row("SAMPLE 200", "NA"),
                                row("SAMPLE 300", "DNC", 0), row("SAMPLE 400", "B")])
        self.assertEqual(result["calculated_gpa"], 5)
        self.assertEqual(result["eligible_points"], 15)

    def test_dns_dnc_failures_count_zero(self):
        result = gpa.calculate([row(grade="DNS"), row("SAMPLE 200", "DNC"), row("SAMPLE 300", "A+")])
        self.assertEqual(result["calculated_gpa"], 3)

    def test_unknown_grade_blocks_and_suppresses_forecast(self):
        result = gpa.calculate([row(grade="CP"), row("SAMPLE 200", "B")], target_gpa=6, future_points=60)
        self.assertIsNone(result["calculated_gpa"])
        self.assertEqual(result["known_rows_gpa"], 5)
        self.assertEqual(result["forecast"]["status"], "blocked_by_unresolved_records")

    def test_missing_points_not_assumed(self):
        result = gpa.calculate([row(points=None)])
        self.assertEqual(result["unresolved_rows"], 1)
        self.assertIsNone(result["calculated_gpa"])

    def test_empty_and_all_excluded_are_undefined(self):
        for rows in ([], [row(grade="P")]):
            self.assertIsNone(gpa.calculate(rows)["calculated_gpa"])

    def test_filters(self):
        records = [row(programme="BSc"), row("SAMPLE 200", "C", programme="BA"),
                   row("SAMPLE 300", "D", year=2025, programme="BSc")]
        result = gpa.calculate(records, year=2026, term="semester one", programme="bsc")
        self.assertEqual(result["calculated_gpa"], 8)

    def test_programme_missing_assignment_rejected(self):
        with self.assertRaises(ValueError):
            gpa.calculate([row()], programme="BSc")

    def test_duplicates_rejected_and_attempt_ids_supported(self):
        with self.assertRaises(ValueError):
            gpa.calculate([row(), row()])
        result = gpa.calculate([row(attempt_id="a"), row(grade="B", attempt_id="b")])
        self.assertEqual(result["calculated_gpa"], 6.5)

    def test_invalid_numbers_rejected(self):
        for value in (-15, True, "NaN", "Infinity", "oops"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                gpa.calculate([row(points=value)])
        with self.assertRaises(ValueError):
            gpa.calculate([row(year=2026.5)])

    def test_forecast_uses_unrounded_accumulation(self):
        result = gpa.calculate([row(grade="B")], target_gpa=6, future_points=15)
        self.assertEqual(result["forecast"]["required_future_average"], 7)

    def test_unattainable_forecast(self):
        result = gpa.calculate([row(grade="D", points=120)], target_gpa=6, future_points=15)
        self.assertEqual(result["forecast"]["status"], "unattainable_with_specified_points")

    def test_csv_bom_and_cli_exit_codes(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(TEMP_ROOT.resolve()))
            file = Path(directory) / "synthetic.csv"
            file.write_text("course,year,term,points,grade\nSAMPLE 100,2026,Semester One,15,A\n", encoding="utf-8-sig")
            result = subprocess.run([sys.executable, str(SCRIPT), str(file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["calculated_gpa"], 8)
            file.write_text("course,year,term,points,grade\nSAMPLE 100,2026,Semester One,15,CP\n", encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), str(file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)

    def test_cli_does_not_overwrite_source(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(TEMP_ROOT.resolve()))
            file = Path(directory) / "synthetic.json"
            content = json.dumps({"courses": [row()]})
            file.write_text(content, encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), str(file), "--output", str(file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(file.read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
