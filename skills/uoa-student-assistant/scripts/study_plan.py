#!/usr/bin/env python3
"""Build an Auckland study brief from explicitly observed, local evidence."""

import argparse
import json
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


TIMEZONE = "Pacific/Auckland"
KINDS = {"assignment", "announcement", "material", "reading", "practice", "class", "exam", "past_paper"}
FIXED = {"class", "exam"}
STUDY = {"assignment", "material", "reading", "practice", "past_paper"}
FIELDS = ("date", "due", "personal_due", "closes", "available_from", "start", "end")
SOURCE_STATES = {"checked", "partial", "blocked", "unchecked"}
ITEM_STATES = {"pending", "complete", "cancelled", "unknown"}
ACCESS_PARAMETERS = {
    "access_token", "authorization", "id_token", "relaystate", "samlrequest", "samlresponse",
    "sesskey", "sig", "signature", "token", "x-amz-credential", "x-amz-security-token", "x-amz-signature",
}
STEPS = {
    "assignment": "阅读作业要求，推进下一步",
    "material": "整理课件要点",
    "reading": "完成指定阅读并记下问题",
    "practice": "按课程规则复习并练习",
    "past_paper": "按主题复习历年题目",
}


def string(row, field, *, required=False):
    value = row.get(field)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value.strip()


def rows(document, field):
    result = document.get(field, [])
    if not isinstance(result, list) or any(not isinstance(row, dict) for row in result):
        raise ValueError(f"{field} must be an array of objects")
    return result


def moment(value, zone, *, timed=False):
    if not timed and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return date.fromisoformat(value)
    if "T" in value:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + ("+00:00" if value.endswith("Z") else ""))
        if parsed.utcoffset() is not None:
            return parsed.astimezone(zone)
    raise ValueError("Use YYYY-MM-DD for date-only evidence, or ISO date-time with an explicit offset")


def day(value):
    return value.date() if isinstance(value, datetime) else value


def utc(value):
    return value.astimezone(timezone.utc)


def at_start(value, zone):
    return utc(datetime.combine(value, time.min, zone))


def normalize_time(row, field, zone, *, required=False, timed=False):
    value = string(row, field, required=required)
    return None if value is None else moment(value, zone, timed=timed).isoformat()


def stable_url(row):
    url = string(row, "url", required=True)
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or re.search(r"[\s<>\\]", url)):
        raise ValueError("url must be a usable HTTP(S) evidence link without embedded credentials")
    if any(key.casefold() in ACCESS_PARAMETERS for section in (parsed.query, parsed.fragment)
           for key, _ in parse_qsl(section, keep_blank_values=True)):
        raise ValueError("url contains an access-bearing parameter. Use the stable source page link")
    if unquote(parsed.path).casefold().startswith("/feeds/calendars/user_"):
        raise ValueError("url is a private Canvas calendar feed. Use the stable source page link")
    return url


def source_records(document, zone):
    sources = {}
    for row in rows(document, "sources"):
        name = string(row, "source", required=True)
        key = name.casefold()
        status = row.get("status")
        if key in sources or not isinstance(status, str) or status not in SOURCE_STATES:
            raise ValueError("sources require distinct names and checked, partial, blocked or unchecked status")
        sources[key] = {
            "source": name, "status": status,
            "checked_at": normalize_time(row, "checked_at", zone, timed=True),
            "detail": string(row, "detail"),
        }
    return sources


def evidence_row(row, zone):
    item = {field: string(row, field, required=True) for field in ("course", "term", "kind", "source", "title")}
    item["course"] = " ".join(item["course"].upper().split())
    item["year"] = row.get("year")
    if type(item["year"]) is not int or not 1900 <= item["year"] <= 2200:
        raise ValueError("year must be an integer between 1900 and 2200")
    item["status"] = string(row, "status") or "unknown"
    if item["kind"] not in KINDS or item["status"] not in ITEM_STATES:
        raise ValueError("Unrecognized item kind or status")
    item["url"] = stable_url(row)
    for field in ("source_id", "link_key", "next_step"):
        item[field] = string(row, field)
    item["checked_at"] = normalize_time(row, "checked_at", zone, required=True, timed=True)
    for field in FIELDS:
        item[field] = normalize_time(row, field, zone, timed=field in {"start", "end"})
    if item["start"] and item["end"] and cutoff(item["end"], zone) <= cutoff(item["start"], zone):
        raise ValueError("An event end must be after its start")
    item["minutes"] = row.get("minutes")
    if item["minutes"] is not None and (type(item["minutes"]) is not int or not 1 <= item["minutes"] <= 10080):
        raise ValueError("minutes must be an integer between 1 and 10080")
    if type(row.get("stale", False)) is not bool:
        raise ValueError("stale must be a boolean")
    item["stale"] = row.get("stale", False)
    return item


def cutoff(value, zone):
    parsed = moment(value, zone)
    return utc(parsed) if isinstance(parsed, datetime) else at_start(parsed, zone)


def source_identity(item):
    return (
        item["course"], item["year"], item["term"].casefold(), item["kind"],
        item["source"].casefold(), "id" if item["source_id"] else "url",
        item["source_id"] or item["url"],
    )


def newest(rows_to_check, zone):
    fresh = [item for item in rows_to_check if not item["stale"]]
    candidates = fresh or rows_to_check
    latest = max(cutoff(item["checked_at"], zone) for item in candidates)
    distinct = {
        json.dumps(item, sort_keys=True, ensure_ascii=False): item
        for item in candidates if cutoff(item["checked_at"], zone) == latest
    }
    return [distinct[key] for key in sorted(distinct)]


def resolve_time(evidence, field, zone):
    values = {item[field] for item in evidence if item[field]}
    if len(values) < 2:
        return next(iter(values), None), False
    exact = [value for value in values if "T" in value]
    if len(exact) == 1 and all(day(moment(value, zone)) == day(moment(exact[0], zone)) for value in values):
        return exact[0], False
    return None, True


def summarize(identity, evidence, zone):
    ordered = sorted(evidence, key=lambda item: cutoff(item["checked_at"], zone), reverse=True)
    fresh = [item for item in ordered if not item["stale"]]
    primary = (fresh or ordered)[0]
    item = {field: primary[field] for field in ("course", "year", "term", "kind", "title")}
    item["key"] = list(identity)
    item["evidence"] = ordered
    item["issues"] = [] if fresh else ["stale_only"]
    statuses = {entry["status"] for entry in fresh} - {"unknown"}
    item["status"] = next(iter(statuses)) if len(statuses) == 1 else "unknown"
    if len(statuses) > 1:
        item["issues"].append("status_conflict")
    for field in FIELDS:
        item[field], conflict = resolve_time(fresh, field, zone)
        if conflict:
            item["issues"].append(f"{field}_conflict")
    item["deadline"] = item["personal_due"] or item["due"]
    item["deadline_scope"] = "personal" if item["personal_due"] else "course" if item["due"] else None
    if any(issue in item["issues"] for issue in ("due_conflict", "personal_due_conflict")):
        item["deadline"] = item["deadline_scope"] = None
    if item["deadline"] and item["closes"]:
        due = moment(item["deadline"], zone)
        closes = moment(item["closes"], zone)
        if day(due) > day(closes) or (isinstance(due, datetime) and isinstance(closes, datetime) and utc(due) > utc(closes)):
            item["issues"].append("deadline_after_close")
            item["deadline"] = item["deadline_scope"] = None
    if item["start"] and item["end"] and cutoff(item["end"], zone) <= cutoff(item["start"], zone):
        item["issues"].append("event_times_conflict")
        item["start"] = item["end"] = None
    if item["kind"] in FIXED and not (item["start"] and item["end"]):
        item["issues"].append("event_time_incomplete")
    item["next_step"] = next((entry["next_step"] for entry in fresh if entry["next_step"]), STEPS.get(item["kind"]))
    item["minutes"] = next((entry["minutes"] for entry in fresh if entry["minutes"]), None)
    return item


def collect(document, zone):
    sources = source_records(document, zone)
    observations = {}
    for index, row in enumerate(rows(document, "items"), 1):
        try:
            item = evidence_row(row, zone)
        except ValueError as error:
            raise ValueError(f"Item {index}: {error}") from None
        name = item["source"].casefold()
        source = sources.setdefault(name, {
            "source": item["source"], "status": "unchecked", "checked_at": None, "detail": "未提供来源核查状态",
        })
        item["source"] = source["source"]
        item["stale"] = item["stale"] or source["status"] in {"unchecked", "blocked"}
        observations.setdefault(source_identity(item), []).append(item)
    groups = {}
    for identity, observations_for_item in sorted(observations.items()):
        links = {item["link_key"] for item in observations_for_item if item["link_key"]}
        if len(links) > 1:
            raise ValueError("One source item has conflicting explicit link_key values")
        group = identity[:4] + ("link", next(iter(links))) if links else identity
        groups.setdefault(group, []).extend(newest(observations_for_item, zone))
    return [summarize(key, group, zone) for key, group in sorted(groups.items())], [sources[key] for key in sorted(sources)]


def anchor_dates(item, zone):
    values = [item[field] for field in ("deadline", "closes", "available_from", "start", "end") if item[field]]
    if not values and item["date"]:
        values = [item["date"]]
    if item["issues"]:
        values.extend(entry[field] for entry in item["evidence"] for field in FIELDS if entry[field])
    return sorted({day(moment(value, zone)) for value in values})


def in_window(item, first, stop, zone):
    dates = anchor_dates(item, zone)
    if item["kind"] in FIXED and dates:
        return dates[0] < stop and dates[-1] >= first
    if not dates:
        return True
    if any(first <= value < stop for value in dates):
        return True
    if item["kind"] not in {"assignment", "practice"} or item["status"] in {"complete", "cancelled"}:
        return False
    deadline = item["deadline"] or item["closes"]
    if deadline:
        return day(moment(deadline, zone)) < first
    return bool(item["issues"]) and dates[-1] < first


def event_ranges(items, zone):
    for item in items:
        if item["kind"] not in FIXED or item["status"] == "cancelled":
            continue
        if item["start"] and item["end"] and not any(entry["stale"] for entry in item["evidence"]):
            yield cutoff(item["start"], zone), cutoff(item["end"], zone)
            continue
        for entry in item["evidence"]:
            start, end = entry["start"], entry["end"]
            if start and end:
                yield cutoff(start, zone), cutoff(end, zone)
            elif start or end or entry["date"]:
                value = day(moment(start or end or entry["date"], zone))
                yield at_start(value, zone), at_start(value + timedelta(days=1), zone)


def open_windows(document, items, first, stop, now, zone):
    lower = max(at_start(first, zone), now)
    upper = at_start(stop, zone)
    available = []
    for entry in rows(document, "availability"):
        start = utc(moment(string(entry, "start", required=True), zone, timed=True))
        end = utc(moment(string(entry, "end", required=True), zone, timed=True))
        if end <= start:
            raise ValueError("Availability end must be after start")
        start, end = max(lower, start), min(upper, end)
        if start < end:
            available.append((start, end))
    merged = []
    for start, end in sorted(available):
        if merged and merged[-1][1] >= start:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    for busy_start, busy_end in sorted(event_ranges(items, zone)):
        remaining = []
        for start, end in merged:
            if busy_start >= end or busy_end <= start:
                remaining.append((start, end))
                continue
            if start < busy_start:
                remaining.append((start, busy_start))
            if busy_end < end:
                remaining.append((busy_end, end))
        merged = remaining
    return merged


def schedule(document, items, first, stop, now, zone):
    blocks, unplaced = [], []
    free = open_windows(document, items, first, stop, now, zone)
    tasks = [item for item in items if item["kind"] in STUDY and item["status"] not in {"complete", "cancelled"}]
    limit = at_start(stop, zone)

    def task_cutoff(item):
        return min((cutoff(item[field], zone) for field in ("deadline", "closes") if item[field]), default=limit)

    for item in sorted(tasks, key=task_cutoff):
        deadline = task_cutoff(item)
        reason = None
        if any(issue in item["issues"] for issue in (
            "stale_only", "status_conflict", "due_conflict", "personal_due_conflict", "closes_conflict", "deadline_after_close",
            "available_from_conflict",
        )):
            reason = "verify_evidence"
        elif not item["minutes"]:
            reason = "no_estimate"
        elif deadline <= now:
            reason = "cutoff_passed_or_same_day_date_only"
        elif not document.get("availability"):
            reason = "no_availability"
        else:
            duration = timedelta(minutes=item["minutes"])
            ready = now
            if item["available_from"]:
                observed = moment(item["available_from"], zone)
                ready = utc(observed) if isinstance(observed, datetime) else at_start(observed + timedelta(days=1), zone)
            for index, (start, end) in enumerate(free):
                begin = max(start, ready)
                finish = begin + duration
                if finish <= min(end, deadline):
                    blocks.append({
                        "key": item["key"], "course": item["course"], "title": item["title"],
                        "next_step": item["next_step"], "minutes": item["minutes"],
                        "start": begin.astimezone(zone).isoformat(), "end": finish.astimezone(zone).isoformat(),
                    })
                    free[index:index + 1] = [(left, right) for left, right in ((start, begin), (finish, end)) if left < right]
                    break
            else:
                reason = "no_fitting_slot"
        if reason:
            unplaced.append({"key": item["key"], "course": item["course"], "title": item["title"], "reason": reason})
    return sorted(blocks, key=lambda block: cutoff(block["start"], zone)), unplaced


def changes(previous, current, first, stop, zone):
    old = {tuple(item["key"]): item for item in previous}
    new = {tuple(item["key"]): item for item in current}
    result = []
    for key in sorted(old.keys() | new.keys()):
        before, after = old.get(key), new.get(key)
        if not any(in_window(item, first, stop, zone) for item in (before, after) if item is not None):
            continue
        item = after or before
        change = {"key": item["key"], "course": item["course"], "title": item["title"]}
        if before is None:
            result.append(dict(change, type="newly_observed"))
        elif after is None:
            result.append(dict(change, type="not_observed_this_run"))
        else:
            fields = {
                field: {"before": before[field], "after": after[field]}
                for field in ("status", "deadline", "deadline_scope", *FIELDS, "issues") if before[field] != after[field]
            }
            if fields:
                result.append(dict(change, type="changed", fields=fields))
    return result


def build_plan(document, previous=None):
    if not isinstance(document, dict) or (previous is not None and not isinstance(previous, dict)):
        raise ValueError("Evidence must be a JSON object")
    zone = ZoneInfo(TIMEZONE)
    as_of = string(document, "as_of")
    now = moment(as_of, zone, timed=True) if as_of else datetime.now(zone)
    start = string(document, "start_date")
    first = moment(start, zone) if start else now.date()
    if isinstance(first, datetime):
        raise ValueError("start_date must be an Auckland date, YYYY-MM-DD")
    stop = first + timedelta(days=7)
    current, sources = collect(document, zone)
    timeline = [item for item in current if in_window(item, first, stop, zone)]
    timeline.sort(key=lambda item: (anchor_dates(item, zone) or [date.max])[0])
    blocks, unplaced = schedule(document, timeline, first, stop, utc(now), zone)
    differences = None if previous is None else changes(collect(previous, zone)[0], current, first, stop, zone)
    return {
        "start_date": first.isoformat(), "end_date": (stop - timedelta(days=1)).isoformat(),
        "timezone": TIMEZONE, "as_of": now.isoformat(), "sources": sources, "timeline": timeline,
        "study_blocks": blocks, "unscheduled": unplaced, "changes": differences,
    }


FIELD_LABELS = {
    "date": "发布或事件日期", "due": "课程截止", "personal_due": "个人截止",
    "deadline": "适用截止", "closes": "关闭提交", "available_from": "开放时间", "start": "开始", "end": "结束",
    "deadline_scope": "截止适用范围", "status": "状态", "issues": "待核实事项",
}
LABELS = {
    "checked": "已核查", "partial": "部分核查", "blocked": "访问受阻", "unchecked": "未核查",
    "pending": "待完成", "complete": "已完成", "cancelled": "已取消", "unknown": "状态未确认",
    "class": "课程班次", "exam": "考试", "announcement": "公告", "assignment": "作业", "reading": "阅读",
    "practice": "练习", "material": "课件", "past_paper": "历年试题", "personal": "个人", "course": "课程",
    "verify_evidence": "先核实来源或日期", "no_estimate": "缺少预计用时", "no_availability": "未提供空闲时间",
    "cutoff_passed_or_same_day_date_only": "已到保守排程界限。若仅有日期，请核对当天的具体时间",
    "no_fitting_slot": "截止前未找到足够长的空闲时段", "stale_only": "只有以往记录，本次未核实",
    "status_conflict": "来源对完成状态的记载有冲突", "deadline_after_close": "截止晚于关闭提交，待核实",
    "event_times_conflict": "班次或考试的起止时间有冲突",
    "event_time_incomplete": "班次或考试的起止时间未核实完整",
    "newly_observed": "本次新观察到", "not_observed_this_run": "本次未查到，状态待核实", "changed": "本次观察到变化",
}


def md(text):
    return re.sub(r"([\\`*_{}\[\]<>#|~])", r"\\\1", " ".join(str(text).split()))


def label(value):
    if value is None:
        return "未核实"
    if isinstance(value, list):
        return "、".join(map(label, value)) or "无"
    if value.endswith("_conflict") and value.removesuffix("_conflict") in FIELD_LABELS:
        return FIELD_LABELS[value.removesuffix("_conflict")] + "在不同记录中不一致"
    return LABELS.get(value, md(value))


def event_dates(item):
    return " · ".join(
        f"{FIELD_LABELS[field]} {label(item[field])}{'（只显示日期）' if 'T' not in item[field] else ''}"
        for field in FIELDS if item[field]
    )


def render_markdown(plan):
    lines = [
        f"# 学习周计划 · {plan['start_date']} 至 {plan['end_date']}", "",
        f"时区 {plan['timezone']} · 生成于 {plan['as_of']}", "", "## 来源核查", "",
    ]
    for source in plan["sources"]:
        details = [label(source["status"]), source["checked_at"], md(source["detail"]) if source["detail"] else None]
        lines.append(f"- {md(source['source'])} · " + " · ".join(value for value in details if value))
    if not plan["sources"]:
        lines.append("未提供本次来源核查记录。")
    lines += ["", "## 课程事项", ""]
    for item in plan["timeline"]:
        info = [label(item["kind"]), label(item["status"]), event_dates(item)]
        if item["deadline"]:
            info.append(f"适用{label(item['deadline_scope'])}截止 {item['deadline']}")
        if item["issues"]:
            info.append(label(item["issues"]))
        if item["next_step"] and item["status"] not in {"complete", "cancelled"}:
            info.append(md(item["next_step"]) + (f"（预计 {item['minutes']} 分钟）" if item["minutes"] else ""))
        lines.append(f"- **{md(item['course'])} · {md(item['title'])}** · {item['year']} {md(item['term'])} · "
                     + " · ".join(value for value in info if value))
        for entry in item["evidence"]:
            detail = f" · {event_dates(entry)}" if event_dates(entry) else ""
            freshness = "上次核实" if entry["stale"] else "核实于"
            lines.append(f"  - {md(entry['source'])} {freshness} {entry['checked_at']}{detail} [原页](<{entry['url']}>)")
    if not plan["timeline"]:
        lines.append("当前输入没有可列入这七天的事项。请以来源核查状态判断覆盖范围。")
    lines += ["", "## 建议学习时段", ""]
    for block in plan["study_blocks"]:
        lines.append(f"- {block['start']} → {block['end']} · {md(block['course'])} · {md(block['title'])} · {md(block['next_step'])}")
    if not plan["study_blocks"]:
        lines.append("当前输入未排出具体学习时间块。")
    if plan["unscheduled"]:
        lines += ["", "### 待安排", ""]
        for entry in plan["unscheduled"]:
            lines.append(f"- {md(entry['course'])} · {md(entry['title'])} · {label(entry['reason'])}")
    if plan["changes"] is not None:
        lines += ["", "## 与上次核查相比", ""]
        for change in plan["changes"]:
            summary = " · ".join(
                f"{FIELD_LABELS[field]} {label(values['before'])} → {label(values['after'])}"
                for field, values in change.get("fields", {}).items()
            )
            lines.append(f"- {md(change['course'])} · {md(change['title'])} · {label(change['type'])}"
                         + (f" · {summary}" if summary else ""))
        if not plan["changes"]:
            lines.append("本次与上次输入的观察结果一致。")
    return "\n".join(lines) + "\n"


def read_json(path):
    with path.open(encoding="utf-8-sig") as source:
        return json.load(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, help="observed evidence in UTF-8 JSON")
    parser.add_argument("--previous", type=Path, help="an earlier input evidence file for comparison")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path, help="write a new UTF-8 file instead of stdout")
    args = parser.parse_args()
    try:
        plan = build_plan(read_json(args.evidence), read_json(args.previous) if args.previous else None)
        report = json.dumps(plan, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_markdown(plan)
        if args.output:
            with args.output.open("x", encoding="utf-8") as output:
                output.write(report)
        else:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout.write(report)
    except ZoneInfoNotFoundError:
        parser.exit(2, "Study plan needs an IANA time-zone database with Pacific/Auckland.\n")
    except (OSError, ValueError, OverflowError) as error:
        parser.exit(2, f"Could not build study plan: {error}\n")


if __name__ == "__main__":
    main()
