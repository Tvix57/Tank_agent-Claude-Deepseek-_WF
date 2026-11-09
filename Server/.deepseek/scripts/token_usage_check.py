#!/usr/bin/env python3
"""
Почасовой контроль расхода токенов для многоагентной системы (см.
/workspace/server/.claude/docs/agent-system-workflow.md). Не часть кодовой базы проекта — служебный
инструмент, .git/info/exclude.

Источники данных:
- Транскрипт текущей сессии: ~/.claude/projects/-workspace-server/<sessionId>.jsonl (основная сессия,
  isSidechain=false).
- Вывод субагентов: <scratchpad>/-workspace-server/<sessionId>/tasks/<agentId>.output — те же
  usage-блоки, что и в основном транскрипте, но для конкретного вызова через Agent tool.
- Сопоставление agentId -> subagent_type берётся из tool_use (name="Agent", input.subagent_type) и
  парного tool_result (текст "agentId: <hex>") в основном транскрипте.

Пороги (см. CLAUDE.md, раздел "Контроль расхода токенов"):
- RATIO_THRESHOLD: input/output > 10:1 -> контекст раздут.
- HIT_RATE_THRESHOLD: cache hit rate < 0.70 у типа агента с 2+ вызовами за окно -> кэш не работает.

"input" везде = эффективный input = input_tokens + cache_creation_input_tokens + cache_read_input_tokens
(не "сырой" input_tokens, который почти всегда ~0 при активном кэшировании и бесполезен для метрики).

Ограничение: если сессия стартовала не в /workspace/server (например смешанная client+server сессия),
транскрипт физически лежит под другим project-каталогом (-workspace-client) — этот скрипт его не
найдёт. Актуально для чисто серверных сессий, что покрывает основной случай входа в пайплайн.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from glob import glob

RATIO_THRESHOLD = 10.0
HIT_RATE_THRESHOLD = 0.70
MIN_INVOCATIONS_FOR_HIT_RATE = 2
MIN_TURNS_FOR_RATIO = 5  # первый ход после простоя (TTL кэша истёк) даёт cache_creation-скачок и
                          # огромный ratio на выборке из 1-2 ходов — это не раздутие контекста, а
                          # артефакт холодного старта; ниже этого числа ходов в окне ratio не проверяем

PROJECTS_DIR = os.path.expanduser("~/.claude/projects/-workspace-server")
SCRATCH_ROOT_CANDIDATES = glob("/tmp/claude-*/-workspace-server")

AGENT_ID_RE = re.compile(r"agentId:\s*([a-f0-9]+)")


def find_current_session_jsonl():
    files = glob(os.path.join(PROJECTS_DIR, "*.jsonl"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def find_tasks_dir(session_id):
    for root in SCRATCH_ROOT_CANDIDATES:
        candidate = os.path.join(root, session_id, "tasks")
        if os.path.isdir(candidate):
            return candidate
    return None


def iter_json_lines(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_ts(entry):
    ts = entry.get("timestamp")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def empty_bucket():
    return {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0, "turns": 0}


def add_usage(bucket, usage):
    bucket["input_tokens"] += usage.get("input_tokens", 0) or 0
    bucket["output_tokens"] += usage.get("output_tokens", 0) or 0
    bucket["cache_read_input_tokens"] += usage.get("cache_read_input_tokens", 0) or 0
    bucket["cache_creation_input_tokens"] += usage.get("cache_creation_input_tokens", 0) or 0
    bucket["turns"] += 1


def total_input(bucket):
    """Весь input, включая переиспользованный кэш — знаменатель для hit rate."""
    return (bucket["input_tokens"] + bucket["cache_read_input_tokens"]
            + bucket["cache_creation_input_tokens"])


def billed_input(bucket):
    """Только НОВЫЙ (не из кэша) input — для ratio. Переиспользование кэша - не "раздутие",
    исключаем cache_read, иначе метрика почти всегда >>10 на любой сессии с работающим кэшем и
    превращается в шум вместо сигнала."""
    return bucket["input_tokens"] + bucket["cache_creation_input_tokens"]


def hit_rate(bucket):
    total = total_input(bucket)
    return (bucket["cache_read_input_tokens"] / total) if total else None


def ratio(bucket):
    out = bucket["output_tokens"]
    return (billed_input(bucket) / out) if out else None


def main():
    window_seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)

    session_path = find_current_session_jsonl()
    if not session_path:
        print(json.dumps({"error": "session transcript not found", "projects_dir": PROJECTS_DIR}))
        return
    session_id = os.path.splitext(os.path.basename(session_path))[0]

    base_bucket = empty_bucket()
    agent_calls = {}  # tool_use_id -> {"subagent_type":..., "description":...}
    agent_id_by_tool_use = {}  # tool_use_id -> agentId

    for entry in iter_json_lines(session_path):
        ts = parse_ts(entry)
        msg = entry.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == "Agent":
                inp = block.get("input", {}) or {}
                agent_calls[block.get("id")] = {
                    "subagent_type": inp.get("subagent_type", "unknown"),
                    "description": inp.get("description", ""),
                }
            elif block.get("type") == "tool_result":
                text_content = block.get("content")
                text = (text_content if isinstance(text_content, str)
                        else json.dumps(text_content, ensure_ascii=False))
                m = AGENT_ID_RE.search(text or "")
                if m:
                    agent_id_by_tool_use[block.get("tool_use_id")] = m.group(1)

        if entry.get("type") == "assistant" and msg.get("usage") and ts and ts >= cutoff:
            add_usage(base_bucket, msg["usage"])

    # subagent_type -> aggregated bucket, only for calls whose agentId output file has activity
    # within the window
    per_type = {}
    tasks_dir = find_tasks_dir(session_id)

    for tool_use_id, agent_id in agent_id_by_tool_use.items():
        call_info = agent_calls.get(tool_use_id, {"subagent_type": "unknown"})
        subagent_type = call_info["subagent_type"]
        if not tasks_dir:
            continue
        out_path = os.path.join(tasks_dir, f"{agent_id}.output")
        if not os.path.isfile(out_path):
            continue
        for sub_entry in iter_json_lines(out_path):
            sub_ts = parse_ts(sub_entry)
            sub_msg = sub_entry.get("message") or {}
            if sub_entry.get("type") == "assistant" and sub_msg.get("usage") and sub_ts and sub_ts >= cutoff:
                bucket = per_type.setdefault(subagent_type, {"invocations": set(), **empty_bucket()})
                add_usage(bucket, sub_msg["usage"])
                bucket["invocations"].add(agent_id)

    report = {
        "session_id": session_id,
        "window_seconds": window_seconds,
        "base_session": {
            **base_bucket,
            "total_input": total_input(base_bucket),
            "billed_input": billed_input(base_bucket),
            "ratio": ratio(base_bucket),
            "hit_rate": hit_rate(base_bucket),
        },
        "agents": {},
        "flags": [],
    }

    total = dict(base_bucket)
    for subagent_type, bucket in per_type.items():
        invocations = len(bucket.pop("invocations"))
        r = ratio(bucket)
        hr = hit_rate(bucket)
        report["agents"][subagent_type] = {
            **bucket,
            "invocations": invocations,
            "total_input": total_input(bucket),
            "billed_input": billed_input(bucket),
            "ratio": r,
            "hit_rate": hr,
        }
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens",
                  "turns"):
            total[k] += bucket[k]

        if bucket["turns"] >= MIN_TURNS_FOR_RATIO and r is not None and r > RATIO_THRESHOLD:
            report["flags"].append({
                "type": "ratio", "agent": subagent_type, "value": round(r, 1),
                "threshold": RATIO_THRESHOLD,
            })
        if invocations >= MIN_INVOCATIONS_FOR_HIT_RATE and hr is not None and hr < HIT_RATE_THRESHOLD:
            report["flags"].append({
                "type": "hit_rate", "agent": subagent_type, "value": round(hr, 2),
                "threshold": HIT_RATE_THRESHOLD, "invocations": invocations,
            })

    total_r = ratio(total)
    if total["turns"] >= MIN_TURNS_FOR_RATIO and total_r is not None and total_r > RATIO_THRESHOLD:
        report["flags"].append({"type": "ratio", "agent": "TOTAL", "value": round(total_r, 1),
                                 "threshold": RATIO_THRESHOLD})

    report["total"] = {**total, "total_input": total_input(total), "billed_input": billed_input(total),
                        "ratio": total_r, "hit_rate": hit_rate(total)}

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
