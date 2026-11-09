#!/usr/bin/env python3
"""
Почасовой контроль расхода токенов для многоагентной системы (см.
/workspace/client/.claude/docs/agent-system-workflow.md). Не часть кодовой базы проекта — служебный
инструмент, .git/info/exclude.

Источники данных:
- Транскрипт текущей сессии: ~/.claude/projects/-workspace-client/<sessionId>.jsonl (основная сессия,
  isSidechain=false).
- Вывод субагентов: <scratchpad>/-workspace-client/<sessionId>/tasks/<agentId>.output — те же
  usage-блоки, что и в основном транскрипте, но для конкретного вызова через Agent tool.
- Сопоставление agentId -> subagent_type берётся из tool_use (name="Agent", input.subagent_type) и
  парного tool_result (текст "agentId: <hex>") в основном транскрипте.

Пороги (см. .claude/CLAUDE.md, раздел "Контроль расхода токенов"):
- RATIO_THRESHOLD: input/output > 10:1 -> контекст раздут. Для ролей «читает много — отвечает
  коротко» (READ_HEAVY_ROLE: *-librarian-*, integration-*) — READ_HEAVY_RATIO_THRESHOLD (решение
  пользователя 2026-10-18): у них 15–20:1 — норма роли, флаг нужен только при аномалии.
- HIT_RATE_THRESHOLD: cache hit rate < 0.70 у типа агента с 2+ вызовами за окно -> кэш не работает.

Простой: если за окно в основной сессии нет ходов, кроме scheduled (сама эта проверка), и нет
активности субагентов — пользователь отошёл. Скрипт пишет маркер PAUSE_DIR/<sessionId> и отдаёт
"idle": true; cron-промпт по нему снимает задачу, а хук UserPromptSubmit
(token_check_resume_hook.py) при следующем сообщении пользователя напоминает пересоздать её.
Ходы с turnOrigin="scheduled" в метрики не входят: после простоя они дают cache_creation на весь
контекст и искажают ratio/hit rate, а их стоимость видна отдельно в "scheduled".

"input" везде = эффективный input = input_tokens + cache_creation_input_tokens + cache_read_input_tokens
(не "сырой" input_tokens, который почти всегда ~0 при активном кэшировании и бесполезен для метрики).
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from glob import glob

RATIO_THRESHOLD = 10.0
READ_HEAVY_RATIO_THRESHOLD = 25.0
READ_HEAVY_ROLE = re.compile(r"librarian|^integration-")
HIT_RATE_THRESHOLD = 0.70
MIN_INVOCATIONS_FOR_HIT_RATE = 2
MIN_TURNS_FOR_RATIO = 5  # первый ход после простоя (TTL кэша истёк) даёт cache_creation-скачок и
                          # огромный ratio на выборке из 1-2 ходов — это не раздутие контекста, а
                          # артефакт холодного старта; ниже этого числа ходов в окне ratio не проверяем

PAUSE_DIR = os.path.expanduser("~/.claude/token_check_paused")
PROJECTS_DIR = os.path.expanduser("~/.claude/projects/-workspace-client")
SCRATCH_ROOT_CANDIDATES = glob("/tmp/claude-*/-workspace-client")

AGENT_ID_RE = re.compile(r"agentId:\s*([a-f0-9]+)")

# usage.output_tokens в транскрипте — снимок на старте стрима (часто 1-40), итог не пишется: сообщение
# с Write на ~16k символов числится как 3 токена. Поэтому output оцениваем по объёму сгенерированного
# содержимого (text/thinking/tool_use.input) и берём max с записанным значением. ~3 символа на токен —
# грубо для смеси кириллицы/кода/JSON; оценка снизу (thinking может храниться пустым).
CHARS_PER_TOKEN = 3.0


def usage_key(entry, msg):
    """Один ответ API пишется в транскрипт несколькими строками (по строке на content-блок:
    thinking/text/tool_use), каждая с копией usage. Считаем usage один раз на message.id,
    иначе input и число ходов завышаются в 2-5 раз."""
    return msg.get("id") or entry.get("requestId") or entry.get("uuid")


def find_current_session_jsonl():
    files = glob(os.path.join(PROJECTS_DIR, "*.jsonl"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def content_chars(msg):
    n = 0
    for block in msg.get("content") or []:
        if not isinstance(block, dict):
            continue
        t = block.get("type")
        if t == "text":
            n += len(block.get("text") or "")
        elif t == "thinking":
            n += len(block.get("thinking") or "")
        elif t == "tool_use":
            n += len(json.dumps(block.get("input") or {}, ensure_ascii=False))
    return n


def collect_usages(path, cutoff, scheduled=None):
    """message.id -> usage с оценённым output_tokens (см. CHARS_PER_TOKEN). Один ответ API пишется
    несколькими строками (по строке на content-блок), usage берём с последней, символы суммируем.
    Ответы внутри scheduled-хода (turnOrigin стоит только на user-записи начала хода) уходят в
    словарь scheduled, если он передан, иначе пропускаются."""
    usages, chars = {}, {}
    in_scheduled = False
    for entry in iter_json_lines(path):
        if entry.get("type") == "user" and entry.get("turnOrigin"):
            in_scheduled = entry["turnOrigin"] == "scheduled"
        msg = entry.get("message") or {}
        ts = parse_ts(entry)
        if entry.get("type") != "assistant" or not msg.get("usage") or not ts or ts < cutoff:
            continue
        key = usage_key(entry, msg)
        if in_scheduled:
            if scheduled is not None:
                scheduled[key] = dict(msg["usage"])
            continue
        usages[key] = dict(msg["usage"])
        chars[key] = chars.get(key, 0) + content_chars(msg)
    for key, usage in usages.items():
        estimated = int(chars[key] / CHARS_PER_TOKEN)
        usage["output_tokens"] = max(usage.get("output_tokens", 0) or 0, estimated)
    return usages


def scan_agent_calls(path, agent_calls, agent_id_by_tool_use):
    for entry in iter_json_lines(path):
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == "Agent":
                inp = block.get("input", {}) or {}
                agent_calls[block.get("id")] = {
                    "subagent_type": inp.get("subagent_type") or "general-purpose",
                    "description": inp.get("description", ""),
                }
            elif block.get("type") == "tool_result":
                text_content = block.get("content")
                text = (text_content if isinstance(text_content, str)
                        else json.dumps(text_content, ensure_ascii=False))
                m = AGENT_ID_RE.search(text or "")
                if m:
                    agent_id_by_tool_use[block.get("tool_use_id")] = m.group(1)


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

    scheduled_usages = {}
    for usage in collect_usages(session_path, cutoff, scheduled_usages).values():
        add_usage(base_bucket, usage)
    scheduled_bucket = empty_bucket()
    for usage in scheduled_usages.values():
        add_usage(scheduled_bucket, usage)

    # Вызовы Agent ищем и в основном транскрипте, и в транскриптах субагентов — иначе вложенные
    # вызовы (аналитик -> библиотекарь) не сопоставляются с типом и выпадают из отчёта.
    tasks_dir = find_tasks_dir(session_id)
    sub_paths = sorted(glob(os.path.join(tasks_dir, "*.output"))) if tasks_dir else []
    scan_agent_calls(session_path, agent_calls, agent_id_by_tool_use)
    for sub_path in sub_paths:
        scan_agent_calls(sub_path, agent_calls, agent_id_by_tool_use)

    # subagent_type -> aggregated bucket, only for calls whose agentId output file has activity
    # within the window
    per_type = {}

    for tool_use_id, agent_id in agent_id_by_tool_use.items():
        call_info = agent_calls.get(tool_use_id, {"subagent_type": "unknown"})
        subagent_type = call_info["subagent_type"]
        if not tasks_dir:
            continue
        out_path = os.path.join(tasks_dir, f"{agent_id}.output")
        if not os.path.isfile(out_path):
            continue
        sub_usages = collect_usages(out_path, cutoff)
        if sub_usages:
            bucket = per_type.setdefault(subagent_type, {"invocations": set(), **empty_bucket()})
            for usage in sub_usages.values():
                add_usage(bucket, usage)
            bucket["invocations"].add(agent_id)

    idle = base_bucket["turns"] == 0 and not per_type
    if idle:
        os.makedirs(PAUSE_DIR, exist_ok=True)
        open(os.path.join(PAUSE_DIR, session_id), "w").close()

    report = {
        "session_id": session_id,
        "window_seconds": window_seconds,
        "idle": idle,
        "scheduled": {**scheduled_bucket, "total_input": total_input(scheduled_bucket)},
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

        threshold = READ_HEAVY_RATIO_THRESHOLD if READ_HEAVY_ROLE.search(subagent_type) else RATIO_THRESHOLD
        if bucket["turns"] >= MIN_TURNS_FOR_RATIO and r is not None and r > threshold:
            report["flags"].append({
                "type": "ratio", "agent": subagent_type, "value": round(r, 1),
                "threshold": threshold,
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
