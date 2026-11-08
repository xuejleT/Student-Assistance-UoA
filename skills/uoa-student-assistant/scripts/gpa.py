#!/usr/bin/env python3
"""Calculate general UoA GPA from explicit academic rows, without network access."""

import argparse
import csv
import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

RULE_URL = "https://uoa.custhelp.com/app/answers/detail/a_id/2454/~/calculating-your-grade-point-average"
GRADE_VALUES = {
    "A+": 9, "A": 8, "A-": 7, "B+": 6, "B": 5, "B-": 4,
    "C+": 3, "C": 2, "C-": 1, "D+": 0, "D": 0, "D-": 0,
    "F": 0, "DNS": 0, "DNC": 0,
}
PASS_GRADES = {"P", "PASS", "CPL", "COMPLETED"}
PENDING_GRADES = {"", "NA", "N/A", "ENROLLED", "IN PROGRESS", "PENDING"}


def number(value, label):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label} must be a finite number")
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a finite number") from None
    if not result.is_finite():
        raise ValueError(f"{label} must be a finite number")
    return result


def text(value):
    return "" if value is None else str(value).strip()


def numeric(value):
    if value is None:
        return None
    return float(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def normalize_rows(rows):
    if not isinstance(rows, list):
        raise ValueError("Input must be an array or an object containing a courses array")
    normalized, seen = [], set()
    for index, raw in enumerate(rows, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"Row {index} must be an object")
        course = " ".join(text(raw.get("course")).upper().split())
        term = text(raw.get("term"))
        if not course or not term:
            raise ValueError(f"Row {index}: course and term are required")
        year_value = number(raw.get("year"), f"Row {index} year")
        if year_value != year_value.to_integral_value() or not 1900 <= year_value <= 2200:
            raise ValueError(f"Row {index}: year must be an integer from 1900 to 2200")
        year = int(year_value)
        attempt = text(raw.get("attempt_id"))
        key = (course, year, term.casefold(), attempt)
        if key in seen:
            raise ValueError(f"Duplicate record for {course}, {year}, {term}; supply distinct attempt_id values if appropriate")
        seen.add(key)
        points_raw = raw.get("points")
        points = None if points_raw is None or text(points_raw) == "" else number(points_raw, f"Row {index} points")
        if points is not None and points < 0:
            raise ValueError(f"Row {index}: points cannot be negative")
        normalized.append({
            "row": index, "course": course, "year": year, "term": term,
            "programme": text(raw.get("programme")), "attempt_id": attempt,
            "grade": text(raw.get("grade")).upper(), "points": points,
        })
    return normalized


def calculate(rows, *, year=None, term=None, programme=None,
              target_gpa=None, future_points=None):
    rows = normalize_rows(rows)
    if programme and any(not r["programme"] for r in rows):
        raise ValueError("Programme filtering requires programme on every row; unknown assignments cannot be silently excluded")
    selected = [r for r in rows if
                (year is None or r["year"] == year) and
                (term is None or r["term"].casefold() == term.casefold()) and
                (programme is None or r["programme"].casefold() == programme.casefold())]
    denominator = Decimal(0)
    weighted = Decimal(0)
    unresolved = 0
    decisions = []
    for row in selected:
        grade, points = row["grade"], row["points"]
        value = None
        if points == 0:
            state, reason = "excluded", "zero_point_requirement"
        elif grade in PENDING_GRADES:
            state, reason = "excluded", "pending_result"
        elif grade in PASS_GRADES:
            state, reason = "excluded", "pass_grade"
        elif grade == "W" and row["year"] >= 2023:
            state, reason = "excluded", "withdrawal_2023_onward"
        elif grade not in GRADE_VALUES and grade != "W":
            state, reason = "unresolved", "unrecognized_grade"
        elif points is None:
            state, reason = "unresolved", "missing_course_points"
        else:
            value = Decimal(0 if grade == "W" else GRADE_VALUES[grade])
            state, reason = "included", "pre_2023_withdrawal_zero" if grade == "W" else "final_grade"
            denominator += points
            weighted += points * value
        unresolved += state == "unresolved"
        decisions.append({**row, "points": numeric(points), "grade_value": numeric(value),
                          "state": state, "reason": reason})
    known_gpa = weighted / denominator if denominator else None
    warnings = []
    if not selected:
        warnings.append("No records match the selected scope")
    if not denominator:
        warnings.append("No eligible graded course points; GPA is undefined")
    if unresolved:
        warnings.append("Unresolved graded records prevent a complete calculation")
    result = {
        "method": "UoA general 9-point GPA; not a certified or faculty-specific GPA",
        "rule_url": RULE_URL,
        "scope": {"year": year, "term": term, "programme": programme,
                  "population": "selected supplied records; completeness not independently verified"},
        "selected_rows": len(selected), "eligible_points": numeric(denominator),
        "weighted_grade_points": numeric(weighted),
        "unresolved_rows": unresolved,
        "calculation_complete_for_supplied_scope": not bool(unresolved),
        "calculated_gpa": numeric(known_gpa) if not unresolved else None,
        "known_rows_gpa": numeric(known_gpa), "rows": decisions, "warnings": warnings,
    }
    if (target_gpa is None) != (future_points is None):
        raise ValueError("target_gpa and future_points must be supplied together")
    if target_gpa is not None:
        target = number(target_gpa, "target_gpa")
        future = number(future_points, "future_points")
        if not 0 <= target <= 9 or future <= 0:
            raise ValueError("target_gpa must be from 0 to 9 and future_points must be positive")
        if unresolved:
            result["forecast"] = {"status": "blocked_by_unresolved_records"}
        else:
            required = (target * (denominator + future) - weighted) / future
            status = ("unattainable_with_specified_points" if required > 9 else
                      "target_met_even_with_zero_future_average" if required <= 0 else
                      "within_grade_scale")
            result["forecast"] = {
                "target_gpa": numeric(target), "future_eligible_points": numeric(future),
                "required_future_average": numeric(required), "status": status,
                "assumption": "Additional GPA-bearing attempts only; no replacement of existing attempts",
            }
    return result


def load_rows(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        if Path(path).suffix.lower() == ".csv":
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not {"course", "year", "term", "points", "grade"}.issubset(reader.fieldnames):
                raise ValueError("CSV requires course, year, term, points and grade headers")
            return list(reader)
        data = json.load(handle, parse_float=Decimal)
        return data.get("courses") if isinstance(data, dict) else data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 CSV/JSON academic records")
    parser.add_argument("--year", type=int)
    parser.add_argument("--term")
    parser.add_argument("--programme")
    parser.add_argument("--target-gpa")
    parser.add_argument("--future-points")
    parser.add_argument("--output", type=Path, help="Optional private result path; otherwise stdout")
    args = parser.parse_args(argv)
    try:
        if args.output and args.output.resolve() == args.input.resolve():
            raise ValueError("Output must not overwrite the input")
        result = calculate(load_rows(args.input), year=args.year, term=args.term,
                           programme=args.programme, target_gpa=args.target_gpa,
                           future_points=args.future_points)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 2 if result["unresolved_rows"] else 0
    except (OSError, ValueError, InvalidOperation) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
