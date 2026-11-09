"""
Почасовой контроль расхода токенов в сессии DeepSeek Harness (dsh).

Аналог `.claude/scripts/token_usage_check.py` для режима DeepSeek: те же метрики и пороги, другой
источник данных — журнал сессии dsh.

Источник (`--sessions-root`, иначе автопоиск):
- JSONL-журнал сессии: `<root>/<projectKey(cwd)>/<sessionId>/session*.jsonl[.zstd]`. Формат — каталог
  событий dsh (`docs/persistence-catalog.md`): строка-заголовок, затем по событию на строку.
  `.zstd` читается только при `--compression none`; иначе нужен zstd (см. `.deepseek/instructions/runtime.md#tokens`).
- События `usage` несут `TokenUsage`: `inputTokens`, `outputTokens`, `cacheReadTokens`,
  `cacheWriteTokens`, `reasoningTokens` (см. `packages/llm/llm/src/types.ts`).
- Субагенты — отдельные сессии: считается их `usage`, если `--include-subagents` и в журнале есть ссылки
  на дочерние сессии.

Пороги (`.claude/docs/agent-system-workflow.md#token-economy`): ratio эффективного input к output > 10:1
(у библиотекарей и integration — 25:1), cache hit rate < 0.70 при 2+ вызовах.

Эффективный input = inputTokens + cacheReadTokens + cacheWriteTokens; cache hit rate =
cacheReadTokens / эффективный input.

Выход — JSON того же вида, что у claude-скрипта (`session_id`, `window_seconds`, `idle`, `base_session`,
`agents`, `flags`, `total`), чтобы промпт-обёртка разбирала оба варианта одинаково.

Запуск: `python3 .deepseek/scripts/token_usage_check.py [окно_сек] [--sessions-root <путь>]
[--compression none] [--include-subagents]`
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

RATIO_THRESHOLD = 10.0
READ_HEAVY_RATIO_THRESHOLD = 25.0
READ_HEAVY_ROLE = re.compile(r"librarian|^integration-")
HIT_RATE_THRESHOLD = 0.70
MIN_INVOCATIONS_FOR_HIT_RATE = 2
MIN_TURNS_FOR_RATIO = 5

ROOT_CANDIDATES = (
    os.path.expanduser("~/.deepseek/sessions"),
    os.path.expanduser("~/.dsh/sessions"),
    os.path.expanduser("~/.deepseek"),
    os.path.expanduser("~/.dsh"),
)
ROOT_ENV = ("DSH_SESSIONS_ROOT", "DEEPSEEK_SESSIONS_ROOT", "DSH_HOME")
LOG_SUFFIXES = (".jsonl", ".jsonl.zstd")


# ---------------------------------------------------------------- поиск журнала


def encode_segment(raw):
    """Повторяет `encodeSegment` из `session-persistence-jsonl/src/format.ts`."""
    if raw == ".":
        return "~002E"
    if raw == "..":
        return "~002E~002E"
    out = []
    for ch in raw:
        out.append(ch if (ch != "~" and re.match(r"[A-Za-z0-9._-]", ch)) else "~%04X" % ord(ch))
    return "".join(out)


def project_key(cwd):
    """Повторяет `projectKey` из `session-persistence-jsonl/src/format.ts`."""
    readable, separator_run = [], False
    for ch in cwd:
        if ch in "/\\:":
            if not separator_run:
                readable.append("-")
            separator_run = True
        elif ch != "~" and re.match(r"[A-Za-z0-9._-]", ch):
            readable.append(ch)
            separator_run = False
        else:
            readable.append("~%04X" % ord(ch))
            separator_run = False
    slug = re.sub(r"^-+", "", "".join(readable)) or "root"
    return "--%s--" % slug[:251]


def root_candidates(explicit):
    if explicit:
        return [os.path.abspath(os.path.expanduser(explicit))]
    found = [os.environ[key] for key in ROOT_ENV if os.environ.get(key)]
    found += [p for p in ROOT_CANDIDATES if os.path.isdir(p)]
    return [p for p in found if os.path.isdir(p)]


def root_error(root):
    """Причина, по которой корень не годится, или None. Явно заданный несуществующий путь — не «нет
    корня», а ошибка в аргументе."""
    if not os.path.isdir(root):
        return {"error": "sessions-root not found", "sessions_root": root,
                "hint": "каталог не существует: проверь --sessions-root"}
    return None


def log_files(root):
    """Все журналы сессий под root: (путь, session_id, mtime)."""
    result = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if not name.endswith(LOG_SUFFIXES) or name.endswith(".lock"):
                continue
            path = os.path.join(dirpath, name)
            session_id = os.path.basename(dirpath)
            result.append((path, session_id, os.path.getmtime(path)))
    return result


def pick_session(root, explicit_session):
    """Журнал нужной сессии: по id, иначе самый свежий по mtime."""
    files = log_files(root)
    if not files:
        return None, files
    if explicit_session:
        for path, session_id, _ in files:
            if session_id.startswith(explicit_session) or explicit_session in path:
                return path, files
        return None, files
    return max(files, key=lambda item: item[2])[0], files


# ---------------------------------------------------------------- чтение


def read_text(path):
    """Текст журнала. `.zstd` раскупается модулем `zstandard`, если он стоит; иначе — честная ошибка
    (тихий «0 токенов» был бы хуже пропуска)."""
    with open(path, "rb") as fh:
        data = fh.read()
    if not path.endswith(".zstd"):
        return data.decode("utf-8", errors="replace")
    try:
        import zstandard  # необязательная зависимость, см. runtime.md#tokens
    except ImportError:
        raise SystemExit(json.dumps({
            "error": "zstd-session-log",
            "path": path,
            "hint": "журнал сжат Zstandard. Либо `pip install zstandard`, либо запусти dsh с "
                    "`compression: none` для JSONL без сжатия (см. .deepseek/instructions/runtime.md#tokens)",
        }, ensure_ascii=False))
    reader = zstandard.ZstdDecompressor().stream_reader(data)
    return reader.read().decode("utf-8", errors="replace")


def iter_records(text):
    """Строки журнала -> объекты. Битые строки пропускаются: журнал дописывается во время чтения."""
    for line in text.split("\n"):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            yield json.loads(line)
        except ValueError:
            continue


def event_time(record):
    """Время события в epoch-секундах. Поле `time` — число (мс или с) либо ISO-строка."""
    value = record.get("time") or record.get("timestamp")
    if isinstance(value, (int, float)):
        return value / 1000.0 if value > 1e11 else float(value)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                parsed = datetime.strptime(value.replace("Z", "+0000") if fmt.endswith("Z") else value, fmt)
                return parsed.timestamp()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None



# ---------------------------------------------------------------- метрики


def empty_bucket():
    return {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0, "reasoning_tokens": 0, "requests": 0}


def add_usage(bucket, usage):
    """TokenUsage dsh -> агрегат в именах, которые ждёт промпт (как у claude-скрипта)."""
    bucket["input_tokens"] += int(usage.get("inputTokens") or 0)
    bucket["output_tokens"] += int(usage.get("outputTokens") or 0)
    bucket["cache_read_input_tokens"] += int(usage.get("cacheReadTokens") or 0)
    bucket["cache_creation_input_tokens"] += int(usage.get("cacheWriteTokens") or 0)
    bucket["reasoning_tokens"] += int(usage.get("reasoningTokens") or 0)
    bucket["requests"] += 1


def total_input(bucket):
    return (bucket["input_tokens"] + bucket["cache_read_input_tokens"]
            + bucket["cache_creation_input_tokens"])


def ratio(bucket):
    """Эффективный input / output; None, если запросов мало или output пуст."""
    if bucket["requests"] < MIN_TURNS_FOR_RATIO or not bucket["output_tokens"]:
        return None
    return total_input(bucket) / bucket["output_tokens"]


def hit_rate(bucket):
    """Доля input, взятого из кэша. None, если эффективного input нет."""
    total = total_input(bucket)
    return None if not total else bucket["cache_read_input_tokens"] / total


AGENT_EVENT = re.compile(r"^subagent/(started|finished)$")


def agent_name(record):
    """Имя дочернего агента: `agent`, `name`, `type`, `subagentType` или `descriptor.name`."""
    data = record.get("data") or {}
    for container in (data, data.get("descriptor") or {}, data.get("agent") or {}):
        if not isinstance(container, dict):
            continue
        for key in ("agent", "name", "type", "subagentType"):
            value = container.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def collect(path, cutoff, include_subagents):
    """(base_bucket, {имя агента: bucket}) за окно."""
    base, agents, current_agent = empty_bucket(), {}, None
    for record in iter_records(read_text(path)):
        ts = event_time(record)
        if ts is not None and ts < cutoff:
            continue
        kind = record.get("type") or ""
        payload = record.get("data") if isinstance(record.get("data"), dict) else record
        if AGENT_EVENT.match(kind):
            current_agent = agent_name(record) if kind.endswith("started") else None
        usage = (payload or {}).get("usage")
        if not isinstance(usage, dict):
            continue
        if include_subagents and current_agent:
            add_usage(agents.setdefault(current_agent, empty_bucket()), usage)
        else:
            add_usage(base, usage)
    return base, agents



# ---------------------------------------------------------------- отчёт


def build_report(session_id, window_seconds, base, agents):
    idle = base["requests"] == 0 and not any(b["requests"] for b in agents.values())
    report = {
        "session_id": session_id,
        "window_seconds": window_seconds,
        "source": "dsh",
        "idle": idle,
        "base_session": {**base, "total_input": total_input(base), "ratio": ratio(base),
                         "hit_rate": hit_rate(base)},
        "agents": {},
        "flags": [],
    }
    total = dict(base)
    for name, bucket in agents.items():
        if not bucket["requests"]:
            continue
        r, hr = ratio(bucket), hit_rate(bucket)
        report["agents"][name] = {**bucket, "total_input": total_input(bucket), "ratio": r, "hit_rate": hr}
        for key in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                    "cache_creation_input_tokens", "reasoning_tokens", "requests"):
            total[key] += bucket[key]
        threshold = READ_HEAVY_RATIO_THRESHOLD if READ_HEAVY_ROLE.search(name) else RATIO_THRESHOLD
        if bucket["requests"] >= MIN_TURNS_FOR_RATIO and r is not None and r > threshold:
            report["flags"].append({"type": "ratio", "agent": name, "value": round(r, 1),
                                    "threshold": threshold})
        if bucket["requests"] >= MIN_INVOCATIONS_FOR_HIT_RATE and hr is not None and hr < HIT_RATE_THRESHOLD:
            report["flags"].append({"type": "hit_rate", "agent": name, "value": round(hr, 2),
                                    "threshold": HIT_RATE_THRESHOLD,
                                    "invocations": bucket["requests"]})
    total_r = ratio(total)
    if total["requests"] >= MIN_TURNS_FOR_RATIO and total_r is not None and total_r > RATIO_THRESHOLD:
        report["flags"].append({"type": "ratio", "agent": "TOTAL", "value": round(total_r, 1),
                                "threshold": RATIO_THRESHOLD})
    report["total"] = {**total, "total_input": total_input(total), "ratio": total_r,
                       "hit_rate": hit_rate(total)}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="token_usage_check_dsh.py",
                                     description="Расход токенов в сессии DeepSeek Harness.")
    parser.add_argument("window_seconds", nargs="?", type=int, default=3600)
    parser.add_argument("--sessions-root", default=None, help="корень журналов dsh (по умолчанию автопоиск)")
    parser.add_argument("--session", default=None, help="id или часть пути нужной сессии")
    parser.add_argument("--include-subagents", action="store_true", default=True,
                        help="считать usage субагентов отдельно от основной сессии")
    args = parser.parse_args(argv)

    roots = root_candidates(args.sessions_root)
    if not roots:
        print(json.dumps({
            "error": "sessions-root not found",
            "candidates": list(ROOT_CANDIDATES),
            "hint": "укажи корень журналов dsh: --sessions-root <путь> или DSH_SESSIONS_ROOT",
        }, ensure_ascii=False))
        return 1
    root = roots[0]
    problem = root_error(root)
    if problem:
        print(json.dumps(problem, ensure_ascii=False))
        return 1
    path, files = pick_session(root, args.session)
    if not path:
        print(json.dumps({
            "error": "session transcript not found",
            "sessions_root": root,
            "logs": len(files),
            "hint": "проверь --session или что dsh пишет журнал в этот корень",
        }, ensure_ascii=False))
        return 1

    cutoff = datetime.now(timezone.utc).timestamp() - args.window_seconds
    base, agents = collect(path, cutoff, args.include_subagents)
    report = build_report(os.path.basename(os.path.dirname(path)), args.window_seconds, base, agents)
    report["log"] = path
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

