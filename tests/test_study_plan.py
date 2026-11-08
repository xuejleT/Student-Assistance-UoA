"""Synthetic study plan cases. No live student data or websites are used."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT / "skills/uoa-student-assistant/scripts/study_plan.py"
spec = importlib.util.spec_from_file_location("study_plan", SCRIPT)
study_plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study_plan)

CHECKED_AT = "2026-11-09T08:00:00+13:00"


def item(source_id="assignment:1", **values):
    row = {
        "course": "SAMPLE 100", "year": 2026, "term": "Semester Two", "kind": "assignment",
        "title": "Sample task", "source": "Canvas", "source_id": source_id,
        "url": "https://example.invalid/course/assignments/1", "checked_at": CHECKED_AT,
        "status": "pending", "minutes": 30,
    }
    row.update(values)
    return row


def snapshot(items=(), **values):
    document = {
        "start_date": "2026-11-09", "as_of": CHECKED_AT, "items": list(items),
        "sources": [dict(source=name, status="checked", checked_at=CHECKED_AT)
                    for name in ("Canvas", "SSO", "CodeRunner", "Library")],
    }
    document.update(values)
    return document


def window(start, end):
    return {"start": f"2026-11-10T{start}:00+13:00", "end": f"2026-11-10T{end}:00+13:00"}


class StudyPlanTests(unittest.TestCase):
    def test_personal_due_is_distinct_from_course_due_and_close(self):
        data = snapshot([item(due="2026-11-10", personal_due="2026-11-11T17:00:00+13:00", closes="2026-11-13")])
        plan = study_plan.build_plan(data)
        record = plan["timeline"][0]
        self.assertEqual(record["due"], "2026-11-10")
        self.assertEqual(record["deadline"], "2026-11-11T17:00:00+13:00")
        self.assertEqual(record["deadline_scope"], "personal")
        self.assertEqual(record["closes"], "2026-11-13")

    def test_close_is_not_displayed_as_due(self):
        data = snapshot([item(closes="2026-11-10")], availability=[window("10:00", "11:00")])
        plan = study_plan.build_plan(data)
        self.assertIsNone(plan["timeline"][0]["deadline"])
        self.assertEqual(plan["timeline"][0]["closes"], "2026-11-10")
        self.assertFalse(plan["study_blocks"])

    def test_date_only_preserves_unknown_time_and_schedules_before_that_day(self):
        data = snapshot([item(due="2026-11-10")], availability=[window("09:00", "10:00")])
        plan = study_plan.build_plan(data)
        self.assertEqual(plan["timeline"][0]["deadline"], "2026-11-10")
        self.assertIn("只显示日期", study_plan.render_markdown(plan))
        self.assertEqual(plan["unscheduled"][0]["reason"], "no_fitting_slot")

    def test_explicit_announcement_conflict_is_reported_with_both_links(self):
        assignment = item(link_key="course-task:1", due="2026-11-11")
        update = item("announcement:1", link_key="course-task:1", due="2026-11-12",
                      url="https://example.invalid/course/announcements/1")
        plan = study_plan.build_plan(snapshot([assignment, update], availability=[window("09:00", "10:00")]))
        record, = plan["timeline"]
        self.assertIsNone(record["deadline"])
        self.assertIn("due_conflict", record["issues"])
        self.assertEqual({evidence["due"] for evidence in record["evidence"]}, {"2026-11-11", "2026-11-12"})
        report = study_plan.render_markdown(plan)
        self.assertIn(assignment["url"], report)
        self.assertIn(update["url"], report)
        self.assertEqual(plan["unscheduled"][0]["reason"], "verify_evidence")

    def test_explicit_link_refines_date_across_sources_without_guessing(self):
        assignment = item(link_key="same", due="2026-11-10")
        exact = item(source="CodeRunner", link_key="same", due="2026-11-09T12:00:00Z")
        plan = study_plan.build_plan(snapshot([assignment, exact]))
        record, = plan["timeline"]
        self.assertEqual(record["deadline"], "2026-11-10T01:00:00+13:00")
        self.assertFalse(record["issues"])

    def test_deadline_later_than_close_is_flagged(self):
        plan = study_plan.build_plan(snapshot([item(personal_due="2026-11-11", closes="2026-11-10")]))
        record, = plan["timeline"]
        self.assertIn("deadline_after_close", record["issues"])
        self.assertIsNone(record["deadline"])

    def test_repeated_rows_and_old_observations_collapse_deterministically(self):
        previous = item(due="2026-11-11", checked_at="2026-11-08T10:00:00+13:00")
        current = item(due="2026-11-13")
        result = study_plan.build_plan(snapshot([previous, current, current]), snapshot([previous]))
        self.assertEqual(len(result["timeline"][0]["evidence"]), 1)
        self.assertEqual(result["timeline"][0]["deadline"], "2026-11-13")
        change, = result["changes"]
        self.assertEqual(change["fields"]["deadline"], {"before": "2026-11-11", "after": "2026-11-13"})
        same = study_plan.build_plan(snapshot([current, current]), snapshot([current]))
        self.assertEqual(same["changes"], [])

    def test_same_title_and_id_across_sources_are_distinct_without_link(self):
        other = item(source="CodeRunner")
        separate_meeting = item("other:1")
        plan = study_plan.build_plan(snapshot([item(), other, separate_meeting]))
        self.assertEqual(len(plan["timeline"]), 3)

    def test_blocked_and_missing_records_are_not_treated_as_removals_or_current(self):
        stale = item(source="CodeRunner", due="2026-11-12", checked_at="2026-11-08T08:00:00+13:00")
        current = snapshot([stale], sources=[{"source": "CodeRunner", "status": "blocked", "detail": "Login expired"}])
        plan = study_plan.build_plan(current, snapshot([stale, item()]))
        record, = plan["timeline"]
        self.assertEqual(record["issues"], ["stale_only"])
        self.assertIsNone(record["deadline"])
        self.assertTrue(record["evidence"][0]["stale"])
        self.assertEqual(plan["sources"][0]["status"], "blocked")
        self.assertEqual({entry["type"] for entry in plan["changes"]}, {"changed", "not_observed_this_run"})
        self.assertIn("Login expired", study_plan.render_markdown(plan))

    def test_partial_source_retains_unchecked_detail_without_overwriting_fresh_item(self):
        old = item(due="2026-11-14", stale=True, link_key="same", source="Library")
        fresh = item(due="2026-11-13", link_key="same")
        data = snapshot([old, fresh], sources=[{"source": "Canvas", "status": "checked"},
                                                {"source": "Library", "status": "partial", "detail": "No full text"}])
        record, = study_plan.build_plan(data)["timeline"]
        self.assertEqual(record["deadline"], "2026-11-13")
        self.assertEqual(sum(entry["stale"] for entry in record["evidence"]), 1)

    def test_timed_classes_are_excluded_from_feasible_windows(self):
        fixed = item("meeting:1", kind="class", source="SSO", title="Lecture", **window("09:30", "10:30"))
        assignment = item(due="2026-11-10T11:30:00+13:00", minutes=45)
        completed = item("assignment:2", status="complete", minutes=30)
        plan = study_plan.build_plan(snapshot([fixed, assignment, completed], availability=[window("09:00", "11:30"),
                                                                                            window("09:20", "09:45")]))
        block, = plan["study_blocks"]
        self.assertEqual(block["start"], "2026-11-10T10:30:00+13:00")
        self.assertEqual(block["end"], "2026-11-10T11:15:00+13:00")

    def test_release_leaves_earlier_slots_available_for_other_work(self):
        later = item("assignment:2", available_from="2026-11-10T10:00:00+13:00", due="2026-11-10T10:45:00+13:00")
        earlier = item(due="2026-11-11")
        plan = study_plan.build_plan(snapshot([later, earlier], availability=[window("09:00", "11:00")]))
        self.assertEqual([block["start"] for block in plan["study_blocks"]],
                         ["2026-11-10T09:00:00+13:00", "2026-11-10T10:00:00+13:00"])

    def test_date_only_exam_blocks_that_day_with_explicit_issue(self):
        exam = item("exam:1", kind="exam", source="SSO", date="2026-11-10")
        plan = study_plan.build_plan(snapshot([exam, item()], availability=[window("09:00", "11:00")]))
        self.assertFalse(plan["study_blocks"])
        self.assertIn("event_time_incomplete", next(row for row in plan["timeline"] if row["kind"] == "exam")["issues"])

    def test_open_overdue_work_and_relevant_undated_material_are_preserved(self):
        old = item(due="2026-11-08", closes="2026-11-16")
        future = item("assignment:2", due="2026-11-16")
        material = item("material:1", kind="material", title="Lecture notes")
        plan = study_plan.build_plan(snapshot([old, future, material]))
        self.assertEqual([entry["evidence"][0]["source_id"] for entry in plan["timeline"]], ["assignment:1", "material:1"])
        self.assertEqual(plan["end_date"], "2026-11-15")

    def test_dst_repeat_uses_elapsed_time_instead_of_clock_labels(self):
        available = {"start": "2026-04-05T02:30:00+13:00", "end": "2026-04-05T02:30:00+12:00"}
        data = snapshot([item(minutes=60)], start_date="2026-04-05", as_of="2026-04-05T01:00:00+13:00",
                        availability=[available])
        block, = study_plan.build_plan(data)["study_blocks"]
        self.assertEqual((block["start"], block["end"]), (available["start"], available["end"]))

    def test_ambiguous_offset_and_non_http_links_are_rejected(self):
        for changes in (dict(due="2026-11-10T17:00"), dict(url="javascript:alert(1)"), dict(minutes=True)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                study_plan.build_plan(snapshot([item(**changes)]))

    def test_access_parameters_are_rejected_without_echoing_the_value(self):
        prefix = "https://example.invalid/course?course=100"
        for tail in ("&access_token=secret", "&RelayState=secret", "&X-Amz-Signature=secret",
                     "&SAMLResponse=secret", "&sesskey=", "#%54oken=secret"):
            with self.subTest(tail=tail), self.assertRaises(ValueError) as error:
                study_plan.build_plan(snapshot([item(url=prefix + tail)]))
            self.assertNotIn("secret", str(error.exception))
        public_link = prefix + "&id=21#overview"
        record, = study_plan.build_plan(snapshot([item(url=public_link)]))["timeline"]
        self.assertEqual(record["evidence"][0]["url"], public_link)

    def test_private_canvas_calendar_path_is_rejected_without_echoing_the_value(self):
        feed = "https://canvas.example.invalid/feeds/calendars/user_%73ecret.ics"
        with self.assertRaises(ValueError) as error:
            study_plan.build_plan(snapshot([item(url=feed)]))
        self.assertNotIn("secret", str(error.exception))

    def test_cli_writes_utf8_output_without_overwriting_existing_files(self):
        temp_root = PROJECT / "tmp"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as folder:
            source = Path(folder) / "evidence.json"
            source.write_text(json.dumps(snapshot([item(title="测试作业")])), encoding="utf-8-sig")
            output = Path(folder) / "weekly-plan.md"
            command = [sys.executable, str(SCRIPT), str(source), "--output", str(output)]
            result = subprocess.run(command, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("测试作业", output.read_text(encoding="utf-8"))
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            report = subprocess.run([sys.executable, str(SCRIPT), str(source), "--format", "json"],
                                    capture_output=True, encoding="utf-8", check=True)
            self.assertEqual(json.loads(report.stdout)["timeline"][0]["title"], "测试作业")


if __name__ == "__main__":
    unittest.main()
