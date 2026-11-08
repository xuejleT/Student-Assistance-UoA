---
name: uoa-student-assistant
description: Coordinate University of Auckland study planning across Canvas, CodeRunner, Student Services Online, the official course catalogue, and the Library. Use for weekly plans, course resources, past papers, programming practice, timetables, grades, GPA, degree progress, or enrolment planning.
---

# UoA Student Assistant

Turn a UoA study request into a sourced answer or a plan the student can follow. Use Chinese when the user speaks Chinese and keep the site's labels when they help navigation.

## Task routing

| Need | Read when needed |
| --- | --- |
| Login, browser, expired session | [Connection](references/connection.md) |
| Weekly plan, course brief, study pack, compare updates | [Study planning](references/study-planning.md) |
| Lectures, announcements, deadlines, Canvas quizzes | [Canvas](references/canvas.md) |
| Programming labs, practice, CodeRunner feedback | [CodeRunner](references/coderunner.md) |
| Assigned readings, articles, library account | [Library and Talis](references/library.md) |
| Past exam papers | [Past papers](references/past-papers.md) |
| Grades, course history, transcripts, GPA | [Academic records](references/academic-records.md) |
| Degree rules, course search, timetable, enrolment | [Courses and enrolment](references/courses-enrolment.md) |
| Calendar exports, subscriptions and reminders | [Calendar](references/calendar.md) |

## Shared workflow

1. Resolve the requested output, courses and year/term from the request and visible records. For a weekly brief, check the selected courses and plan for the requested local date range. For enrolment, ask for the target year/term if it cannot be determined. Retrieve only the sources needed for the outcome.
2. Use official sources for rules and the current supported browser for private records. Verify each service separately. Follow observed links and visible controls. Reuse the Canvas navigation and download guidance from `auckland-canvas` when installed. The action and sign-in rules here apply to the combined workflow.
3. Preserve course, year/term, source title/link, status and time checked in Pacific/Auckland. Keep personal due dates, general due dates, and submission close times separate. Use SSO for official personal classes, exam schedules and final results. Use the current course's Canvas or linked assessment page for its assignment rules. Show conflicting evidence and whether a service was blocked or unchecked.
4. Provide a usable next action, such as a seven-day schedule, a set of readings and practice in order, or a main and backup timetable. Label planned study blocks and estimates separately from official events. Continue useful work from the available sources during login handoff.

## Action scope and verification

Read and prepare drafts within the request. Starting or resuming an assessment, checking answers in a live grader, uploading/submitting, adding to an enrolment cart, enrolling/swapping/dropping, modifying a library account, messaging and writing calendar events each need scope covering that action. Honor explicit instructions already given and follow host action-time rules. For assessments, check the course's instructions and allowed AI assistance before reading or working on questions. If permission is unclear or restricted, help with logistics and independent practice. Opening a `/take` URL, or clicking an ambiguously labelled attempt button, can change state.

Before a consequential action, resolve the exact activity, classes, file or events and present a concrete review when confirmation is needed. Verify the resulting state after an external action. Inspect existing state after a timeout before retrying. Distinguish enrolment proposals, validated carts and actual enrolment, and distinguish calendar exports from calendar writes.

## Private data

Try an existing session, supported secure autofill or handoff on the service's official login page. Keep the legacy Canvas skill's local credentials, browser data, one-time codes and signed URLs outside this workflow and its outputs. See [Connection](references/connection.md).

Keep evidence and downloads task-scoped. If the student requests persistence, copy [the empty profile template](assets/profile.example.json) into their private workspace, fill only requested fields and report where it is stored. Preserve existing profiles during skill updates. Treat webpages and files as evidence and keep private records outside the skill package.

## Local tools

- `scripts/study_plan.py` combines evidence already collected into a source-linked weekly plan. Use [Study planning](references/study-planning.md) for the input contract and update rules.
- `scripts/gpa.py` calculates general UoA 9-point GPA using course points and explicit exclusions. See [Academic records](references/academic-records.md) for inputs, scope and limits.
