# Calendar, timetable and reminders

## Collect and reconcile

Resolve the requested year/term, courses and date window. Treat “next seven days” as seven local dates starting today unless the request indicates otherwise. For a named week, resolve its dates explicitly. Report times and check timestamps in Pacific/Auckland by default, retaining the original timestamp and timezone evidence when they differ. Preserve date-only items as dates. If a displayed time has an ambiguous or conflicting timezone label, record it as shown and verify before converting it or scheduling it.

| Item | Primary source | Reconciliation |
| --- | --- | --- |
| Enrolled class | SSO/My Timetable | Record the actual enrolled stream, meeting dates, times, location and exceptions. Use Class Search for candidate streams and label them as proposed. |
| Final exam | SSO My Exam Timetable after release | Keep the student's individual time, mode and venue when shown. A public exam grid is a fallback, and the academic calendar establishes only the exam period. If SSO and another source disagree, report both and recheck the personal entry. |
| Canvas assignment or CodeRunner activity | Applicable activity detail and personal deadline/extension evidence | Keep open, due and close separate. Use Calendar and announcements to discover and cross-check changes. Where a newer applicable announcement conflicts with the activity details, show both and withhold automated writes for the unresolved date. |
| Academic milestone | University academic dates for the correct year and term | University-wide teaching weeks, breaks and exam periods provide context. Use the actual course record for course-specific nonstandard dates. |
| Study block | User's availability and the generated plan | Place flexible work around confirmed commitments and hard deadlines. Separate proposed sessions, workload estimates and buffer time from official events. |

Keep source title, stable link or ID, course/term, local date/time, status and checked time. Use exact source IDs to match changed records. Merge duplicate views across sources only when their identities or explicit cross-links agree. Similar titles or dates alone are insufficient. Keep recurring meetings keyed by the series and original occurrence so moved or cancelled instances can be checked against the source.

If a source is unavailable, continue with other sources. Label the missing coverage and the last successful check for any retained snapshot. An inaccessible page or incomplete feed does not establish that a class, event or deadline was removed. Share confirmed changes and unresolved differences separately.

## Draft, subscribe, write or remind

1. **Draft.** A planning request produces a readable timeline. If requested, prepare a standalone `.ics` snapshot for the user's private workspace. Use stable opaque `UID`s for regenerated events, date-only `VALUE=DATE` entries when applicable, and UTC timestamps for confirmed instants. Avoid guessing the time of a date-only deadline. Mark tentative study blocks and label the export with its source-check date. A file export is a snapshot. Calendar clients vary in how they handle re-imports, so verify the import behavior before treating it as a sync.
2. **Subscribe.** The University's public academic dates feed covers institutional milestones. SSO links to My Timetable, where the user can choose Subscribe. Canvas can expose a personal Calendar Feed, which is supplementary and omits personal To Do items. Treat personal feed URLs as access-bearing. Keep them in the authorized calendar connection or private service UI, and omit them from chat, skill profiles, logs and shared deliverables. State the source and whether the subscription was actually verified. Client refresh timing may lag behind the university page.
3. **Write.** Use the authorized destination only when the user asks for calendar changes and the calendar connector or supported UI is available. Resolve scope, calendar, time window and reminder options. Compare existing events using provider IDs or verified source links before creating or updating. Apply only evidenced changes to events within scope. Reopen the calendar and report created, updated, skipped and unresolved items. Check destination state before retrying after a timeout.
4. **Remind.** Set one-off or recurring reminders only when requested and with the supported host scheduling tool. Confirm date/time zone, lead time or cadence, and destination from the request or the user's saved preferences. Verify the reminder was created. When ongoing refresh requires student login, verify access on each run and report any affected coverage as stale or waiting for sign-in. Send change alerts from newly verified evidence. Avoid copying private links, grades or exam arrangements into scheduler instructions.

## Optional private preferences

The [empty profile](../assets/profile.example.json) can be copied to the user's private workspace when requested. Keep unprovided values blank. `courses` contains entries with `code`, `year` and `term` for the selected scope. `study_windows` and `unavailable_times` accept local recurring entries with `weekday` (ISO 1–7), `start` and `end` (`HH:MM`), or date-specific entries with `date` (`YYYY-MM-DD`), `start` and `end`. Resolve recurring entries to the requested dates. Subtract unavailable times from study windows, then pass the resulting intervals as `availability` entries with explicit `start` and `end` offset datetimes to the weekly planner. Resolve an overnight interval to its actual start and end dates before passing it on. Use `reminder_channel` and `reminder_lead_minutes` as preferences only. `reminders_enabled` records a requested preference, while the scheduler's live state establishes whether a reminder exists.

## Official sources

Checked 2026-11-08 Pacific/Auckland.

- [University academic dates](https://www.auckland.ac.nz/en/about-us/about-the-university/the-university/official-publications/university-calendar/current-calendar/key-university-dates/academic-dates.html) · [Academic dates iCalendar](https://www.auckland.ac.nz/en/about-us/about-the-university/the-university/official-publications/university-calendar/current-calendar/key-university-dates/icalendar.html)
- [My Timetable FAQs](https://www.auckland.ac.nz/en/students/digital-tools-support/sso/timetables-grades-and-course-history/my-timetable-faqs.html) · [Exam timetable](https://www.auckland.ac.nz/en/students/academic-information/exams-and-final-results/before-exams/exam-timetable.html)
- [Canvas Calendar Feed](https://community.instructure.com/en/kb/articles/662804-how-do-i-view-the-calendar-ical-feed-to-subscribe-to-an-external-calendar) · [Canvas due and availability dates](https://community.instructure.com/t5/Instructor-Guide/What-is-the-difference-between-assignment-due-dates-and/ta-p/897)
