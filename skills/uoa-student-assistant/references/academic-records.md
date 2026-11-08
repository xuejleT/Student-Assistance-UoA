# Academic records and GPA

Official sources checked 2026-11-01:
- https://www.auckland.ac.nz/en/students/digital-tools-support/sso/timetables-grades-and-course-history/view-grades.html
- https://uoa.custhelp.com/app/answers/detail/a_id/2454/~/calculating-your-grade-point-average
- https://www.auckland.ac.nz/en/students/academic-information/exams-and-final-results/after-exams/final-results.html

Programme GPA/course-assignment guidance: https://uoa.custhelp.com/app/answers/detail/a_id/16988 . The unofficial transcript can establish programme assignments; cumulative history alone cannot.

## Navigation and evidence

Observed: Student Homepage > Academic Data opens Academic Records/Course History. Expand the side panel for View Grades, New Unofficial Transcript, Previous Unofficial Transcript and Programme GPA. These are navigation hints, not permanent selectors; inspect the live page.

Course History exposes class/course, description, term, grade, points and status. Extract actual row cells: blank grade/points cells must stay blank rather than shifting later fields. In-progress courses are not final grades. Non-credit requirements such as ACADINT may have blank points; never assume 15 points.

Use View Grades for a requested term. Prefer displayed Programme GPA or term/cumulative figures on an unofficial transcript and label the scope. Do not create a new transcript request if an existing view answers the question. If generation is necessary, explain the step and inspect the workflow; never purchase an official document for a general GPA query.

Canvas marks are provisional; SSO publishes approved final grades. Predictions and Canvas totals cannot replace final SSO results.

## General GPA rules

A+ 9, A 8, A- 7, B+ 6, B 5, B- 4, C+ 3, C 2, C- 1; D+, D, D-, F, DNS and DNC 0. Weight by course points. Exclude Pass grades and W from 2023 onward; W before 2023 counts as zero. Zero-point requirements do not affect numerator/denominator. Keep repeated attempts unless an evidenced faculty rule differs.

Unknown grades, CP, transferred credits and missing points require clarification of their rule. NA, blank grades and ENROLLED are pending, not zero. Term, cumulative and programme GPA populations differ; special admission/scholarship/honours methods require the relevant faculty rule.

## GPA helper

`scripts/gpa.py` requires Python 3.10+, standard library only. Input: UTF-8 CSV with headers, JSON array, or `{ "courses": [...] }`.

| Field | Meaning |
| --- | --- |
| course | Required course code |
| year | Required integer enrolment year |
| term | Required term label; preserve wording |
| points | Numeric course points; null/blank is unresolved for a graded row; verified non-credit rows use 0 |
| grade | Final letter grade; null/blank for pending |
| programme | Optional programme identifier; required on every row when filtering by programme |
| attempt_id | Optional identifier for separate records of the same course/year/term |

Keep repeated attempts as separate rows. Duplicate course/year/term/attempt_id keys cause an error, preventing silent double-counting. Do not duplicate programme assignments into cumulative records.

```powershell
python <skill-path>/scripts/gpa.py <private-history.json>
python <skill-path>/scripts/gpa.py <private-history.csv> --year 2026 --term "Semester One"
python <skill-path>/scripts/gpa.py <private-history.json> --programme BSc
python <skill-path>/scripts/gpa.py <private-history.json> --target-gpa 6 --future-points 60
```

Filters combine. No filters means all supplied rows, a cumulative GPA only if history is complete. Output includes scope, row decisions and rule URL. `calculated_gpa` is null for unresolved graded records; `known_rows_gpa` is partial only. Target forecasts are suppressed if unresolved. Pending courses are excluded/listed. Empty/all-excluded populations have null GPA, never zero. Output is stdout unless `--output` is explicitly supplied.

Target scenarios calculate the required average across future GPA-bearing points. Above 9 is unattainable under that fixed scenario. Do not assume future enrolment, grades or programme eligibility. Present source/displayed values separately from general-method calculations and forecasts.
