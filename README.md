# Student Assistance UoA

An independent Codex skill for University of Auckland students. It helps you turn Canvas course material, CodeRunner practice, Student Services Online (SSO), the Curriculum Catalogue, and Library resources into a study plan with source links. The project is community maintained and has no official university affiliation.

## What you can do

| Task | What the skill produces |
| --- | --- |
| Weekly planning | A seven-day brief with deadlines, class and exam times, source links, and study blocks based on your availability |
| Course revision | Explanations and review notes from selected slides, Talis readings, and available past papers, with links or page references |
| Programming practice | Concept walkthroughs, original practice exercises, and review of permitted CodeRunner feedback |
| Enrolment planning | A proposed timetable and fallback, with prerequisites, required class components, and date-aware clash checks |
| Grades and calendars | A general GPA estimate from supplied records, or a calendar draft from verified dates |

## Install in Codex

Clone this repository or use **Code → Download ZIP** on GitHub and extract it. From the repository root, copy the whole `skills/uoa-student-assistant` directory into `.agents/skills/` for that workspace. For all workspaces, copy it into the `.agents/skills/` directory in your home folder instead. The installed folder should contain `uoa-student-assistant/SKILL.md` with its adjacent references and scripts. If updating, replace your previous copy of the skill folder while keeping any private study files elsewhere. See [OpenAI Docs on skill discovery](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills).

For example, on a fresh project installation in PowerShell:

```powershell
git clone https://github.com/xuejleT/Student-Assistance-UoA.git
Set-Location Student-Assistance-UoA
New-Item -ItemType Directory -Path .agents/skills -Force | Out-Null
Copy-Item -LiteralPath skills/uoa-student-assistant -Destination .agents/skills -Recurse
```

Open that workspace in Codex and invoke `$uoa-student-assistant` or choose it from the skill picker. For live access, use a supported browser session and complete school sign-in or MFA on the official page when prompted. Each service can have a separate session. The local helpers use Python 3.10 or later. The planner also needs an IANA timezone database with `Pacific/Auckland`. If Python cannot find it on Windows, run `python -m pip install tzdata` in the Python environment used to run the planner.

## Try these prompts

> 用 `$uoa-student-assistant` 帮我理解这门课的 Week 4 课件。用一个小例子解释最难的概念，最后出三道原创练习题，标出课件出处。

> Use `$uoa-student-assistant` to turn my Canvas deadlines and SSO class times into a seven-day plan. I can study on Tuesday and Thursday evenings. Cite the original pages and flag any conflicting dates.

> Use `$uoa-student-assistant` to find the assigned reading and one relevant past paper. Confirm which full texts you could open and outline a revision session.

To try the two helpers with fictional data and no school login:

```text
python skills/uoa-student-assistant/scripts/study_plan.py examples/weekly-plan.json
python skills/uoa-student-assistant/scripts/gpa.py examples/course-history.csv
```

Run `python -m unittest discover -s tests` to check the helpers. The examples and tests use synthetic data.

Read the [security and privacy notes](SECURITY.md) before using the skill on real course material. See [MIT License](LICENSE) for the source code and documentation in this repository.
