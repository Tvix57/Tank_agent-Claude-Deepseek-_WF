#!/usr/bin/env python3
"""Конвертер раскладок `.claude` (Claude Code) <-> `.deepseek` (DeepSeek Harness / dsh).

Служебный инструмент проекта: работает в репозитории, где лежит сам (рядом с `.claude`),
аргументы CLI одинаковы для client и server. Полная спецификация — `.deepseek/sync/CONVERSION.md`.

Команды:
  export [--force] [--strict]   .claude -> .deepseek
  import [--force] [--strict]   .deepseek -> .claude (docs/memory в обе стороны, обслуживаемые файлы)
  check [--strict]              статус конвертируемых файлов: missing / changed / new / ok + для memory
  drift [--strict]              обратная сверка сгенерированного (.deepseek, docs-зеркала, AGENTS.md)
  status                        сводная карта раскладок .claude и .deepseek

Ручные файлы `.deepseek/{README.md,instructions/,sync/}` не перезаписываются: они не содержат
заголовок `<!-- GENERATED`. Код возврата 1 при расхождениях (--strict: и при опережении .claude).
Только stdlib: Python 3.9+.
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

MARKER = "<!-- GENERATED"
MIRROR_LOG_START = "<!-- dz:mirrors:start -->"
MIRROR_LOG_END = "<!-- dz:mirrors:end -->"
BUGS_BLOCK_START = "<!-- dz:bugs:start -->"
BUGS_BLOCK_END = "<!-- dz:bugs:end -->"

CONVERTER_VERSION = "1.0"
GENERATOR = ".deepseek/scripts/convert.py (версия " + CONVERTER_VERSION + ")"

# Что участвует в конвертации. Инфраструктура клиента (checkpoints, worktrees, кэш) — нет.
CONTENT_SCOPE = ("memory/", "docs/", "agents/", "skills/")
DOCS_SKIP_PREFIXES = (".claude/", "incoming/")
DOCS_SKIP_FILES = {".DS_Store"}

TOOL_MAP = {
    "Read": "read", "Bash": "bash", "Write": "write", "Edit": "edit",
    "Agent": "task", "Skill": "skill", "SkillTool": "skill", "Grep": "grep", "Glob": "glob",
    "WebSearch": "web_search", "WebFetch": "web_fetch", "SendMessage": "message",
}
DEEPSEEK_TOOLS = set(TOOL_MAP.values())
TOOL_REVERSE = {v: k for k, v in TOOL_MAP.items()}
BUILTIN_AGENTS = {
    "general-purpose": "general-purpose", "Explore": "explore", "Plan": "plan",
    "explore": "explore", "plan": "plan", "worker": "worker",
}
BUILTIN_AGENTS_REVERSE = {
    "general-purpose": "general-purpose", "explore": "Explore", "plan": "Plan", "worker": "worker",
}

MODEL_TIERS = {
    "opus": "pro", "sonnet": "flash", "haiku": "flash", "fable": "pro", "pro": "pro", "flash": "flash",
}
TIER_CHAIN = {
    "haiku": ["opus", "sonnet", "haiku"], "sonnet": ["opus", "sonnet", "haiku"],
    "opus": ["opus", "sonnet", "haiku"], "fable": ["opus", "sonnet", "haiku"],
}
MODEL_NAMES = {"pro": ("deepseek-v4-pro", "deepseek-flash"), "flash": ("deepseek-flash", "deepseek-v4-pro")}
DEFAULT_MODELS = {"lead": "deepseek-v4-pro", "specialist": "deepseek-flash"}

MEMORY_TYPE_PREFIX = {"feedback": "feedback", "project": "project", "reference": "reference", "user": "reference"}


DZ_SCHEMA = """# Схема `.deepseek` — временная страховка на случай блокировки Claude Code.
# Файл машинный, правится вместе со скиллом sync (`.deepseek/sync/MIGRATION.md`).
schema: 1
layout: .deepseek
engine: deepseek
generated_by: %s
converted_at: {{CONVERTED_AT}}
source_layout: .claude
description: >-
  Зеркало `.claude`: инструкции, агенты, скиллы, документация и память проекта для продолжения
  работы в DeepSeek Harness (dsh), когда Claude Code недоступен.
""" % GENERATOR

DZ_LAYOUT_MD = """# Раскладка `.deepseek`

Зеркало `.claude` с теми же сущностями в терминах DeepSeek. Соответствие один-к-одному:

| `.claude` | `.deepseek` | Что это |
|---|---|---|
| `CLAUDE.md` | `AGENTS.md` (корень репозитория) | Инструкции проекта; у dsh — штатное имя |
| `CLAUDE.md` | `instructions/project.md` | Правила проекта для dsh (полный текст CLAUDE.md) |
| `.claude/agents/<группа>/<имя>.md` | `agents/<группа>/<имя>.md` | Определения агентов, тот же YAML frontmatter |
| `.claude/agents/<группа>/.claude/agent-memory-local/` | `agent-memory-local/` | Личная память специалистов (перенесена из вложенного `.claude`) |
| `.claude/skills/<имя>/` | `skills/<имя>/` | Скиллы: `SKILL.md` + файлы рядом |
| `.claude/docs/` | `docs/` | Документация: архитектура, стандарты, `game-design/*-gdd.md` |
| `.claude/settings.local.json` (hooks) | `hooks.json` | Хуки в нейтральном формате |
| `.claude/session_state.json` | `state/session_state.json` | Ветка предыдущей сессии |
| `.claude/memory/*.md` | `memory/*.md` | Общая память: тот же текст, `name` = имя файла |
| `.claude/scripts/*.py` | `scripts/*` | Скрипты (кроме `convert.py` — он живёт только здесь) |
| `.claude/memory/MEMORY.md` | `memory/MEMORY.md`, `memory/INDEX.md` | Указатель всей памяти проекта |

Файлы, которых в `.claude` нет: `README.md` (быстрый старт), `instructions/`, `sync/`, `CLAUDE.ds.md`
и `AGENTS.md` в корне — генерируются. Обратный путь (`import`) их не трогает.
"""

PROJECT_HEADER = """# AGENTS.md — правила проекта для DeepSeek

Источник: `CLAUDE.md` этого репозитория, копия без изменений по смыслу. Файл сгенерирован
`%s`; править нужно `CLAUDE.md`, сюда переносить через `python3 .deepseek/scripts/convert.py export`.

Далее «WF» — `.deepseek/docs/agent-system-workflow.md` (в `.claude`-режиме: `.claude/docs/agent-system-workflow.md`).
DEEPSEEK-ONLY правила этого файла — в `.deepseek/instructions/rules.md`.

---

""" % GENERATOR

RESTORE_BLOCK = """
---

## DEEPSEEK-ONLY: вернуть этот файл к CLAUDE.md (перед возвратом в Claude Code)

Симлинк `CLAUDE.md -> AGENTS.md` возможен только там, где `CLAUDE.md` нет (например, отдельный git
worktree). Порядок:

1. `grep -n 'DEEPSEEK-ONLY' AGENTS.md` — всё после первого маркера в `CLAUDE.md` не переносить.
2. Удалить `CLAUDE.md`-симлинк, записать `CLAUDE.md` без хвоста и без строки про `%s`.
   Потерялся исходный текст — он лежит в `.deepseek/instructions/project.md`.
3. `python3 .deepseek/scripts/convert.py drift` — `.claude` не должен упоминать `.deepseek`.
4. `git status -s CLAUDE.md .claude` — в диффе только ожидаемые правки задачи.
""" % GENERATOR


# ---------------------------------------------------------------- утилиты


def now():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def read_text(path):
    data = Path(path).read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def norm_newlines(text):
    return text.replace("\r\n", "\n")


def write_if_changed(path, content, force, out):
    """Пишет файл, только если содержимое изменилось. True — файл записан."""
    path = Path(path)
    if path.exists() and not path.is_file():
        out.warn("не файл, пропущено: %s" % path)
        return False
    if path.is_file():
        try:
            current = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            current = None
        if current == content and not force:
            return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))
    return True


def is_generated(path):
    path = Path(path)
    if not path.is_file():
        return False
    return bool(GENERATED_MARK.search(path.read_text(encoding="utf-8", errors="replace")))


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def dump_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def rel_posix(path, root):
    return Path(path).relative_to(root).as_posix()


class Out:
    """Вывод без зависимостей; собирает предупреждения."""

    def __init__(self):
        self.warnings = []

    def line(self, text=""):
        print(text)

    def warn(self, text):
        self.warnings.append(text)
        print("! %s" % text)

    def item(self, code, path, extra=""):
        tail = ("  " + extra) if extra else ""
        print("  %-8s %s%s" % (code, path, tail))


# ---------------------------------------------------------------- markdown


TOKEN_LINK = re.compile(r"\]\((\.[^)\s]*)\)")
PATH_DZ = re.compile(r"(?<![\w.-])\.claude/")
PATH_CLAUDE = re.compile(r"(?<![\w.-])\.deepseek/")
# `session_state.json` в `.deepseek` лежит в подкаталоге `state/`: общий префикс даёт неверный путь.
STATE_DZ = re.compile(r"(?<![\w.-])\.deepseek/(?:state/)?session_state\.json")
STATE_CLAUDE = re.compile(r"(?<![\w.-])\.claude/(?:state/)?session_state\.json")
PATH_WF_DZ = re.compile(r"((?:/|\.)?)\.claude/docs/agent-system-workflow\.md")
PATH_WF_CLAUDE = re.compile(r"((?:/|\.)?)\.deepseek/docs/agent-system-workflow\.md")
# Ссылка на правило ГДД: внутри `код`, в [[вики-ссылке]] или в markdown-ссылке. Заголовки (# ‹gdd-x›,
# {#gdd-x}) и внешние якоря страницы не трогаются: у них другой контекст.
GDD_DZ = re.compile(r"(?<=`)#(?=gdd-)|(?<=\[\[)#(?=gdd-)|(?<=\]\()#(?=gdd-)")
GDD_CLAUDE = re.compile(r"(?<=`)(?<!`#)(?=gdd-)|(?<=\[\[)(?=gdd-)|(?<=\]\()(?=gdd-)")
# Инструмент запуска субагента и его параметр: в Claude Code `Agent` + `subagent_type`, в dsh `task` + тип.
# Оборот «вызов `Agent` tool» — исключение: там `Agent` стоит в бэктиках как имя, а не как имя инструмента.
AGENT_TOOL_DZ = re.compile(r"(?<!вызов\s)(?<!вызов\s`)(?:Agent\s+tool|`Agent`\s+tool)")
AGENT_TOOL_CLAUDE = re.compile(r"`task`")
SUBAGENT_TYPE_DZ = re.compile(r"`subagent_type`|subagent_type")
SUBAGENT_TYPE_CLAUDE = re.compile(r"тип агента")
# Параметр фонового запуска в dsh не существует: фраза про него переводится в требование синхронности.
BG_DZ = re.compile(r"в каждом вызове `?Agent tool`? указывай `run_in_background: false`\n"
                   r"\(по умолчанию агенты уходят в фон\)\.")
BG_CLAUDE = re.compile(r"ответе несколькими вызовами, но тоже с `run_in_background: false`\.")


def swap_paths(target, src, dst):
    """Меняет префикс `src` на `dst` у относительных и абсолютных путей в ссылке."""
    target = re.sub(r"(\]\(|^|[\s(`'\"])(\.{0,2}/?)" + re.escape(src) + "/", r"\1\2" + dst + "/", target)
    return target.replace("/" + src + "/", "/" + dst + "/")


def claude_to_dz(text):
    text = PATH_WF_DZ.sub(r"\1.deepseek/docs/agent-system-workflow.md", text)
    text = TOKEN_LINK.sub(lambda m: "](" + swap_paths(m.group(1), ".claude", ".deepseek") + ")", text)
    text = PATH_DZ.sub(".deepseek/", text)
    text = STATE_DZ.sub(".deepseek/state/session_state.json", text)
    text = BG_DZ.sub("результат нужен до твоего ответа, поэтому дождись его, а не\n"
                     "передавай работу в фон.", text)
    text = BG_CLAUDE.sub("ответе несколькими вызовами, но тоже синхронно.", text)
    text = AGENT_TOOL_DZ.sub("`task`", text)
    text = SUBAGENT_TYPE_DZ.sub("тип агента", text)
    return GDD_DZ.sub("", text)


def dz_to_claude(text):
    text = PATH_WF_CLAUDE.sub(r"\1.claude/docs/agent-system-workflow.md", text)
    text = TOKEN_LINK.sub(lambda m: "](" + swap_paths(m.group(1), ".deepseek", ".claude") + ")", text)
    text = PATH_CLAUDE.sub(".claude/", text)
    text = STATE_CLAUDE.sub(".claude/session_state.json", text)
    text = AGENT_TOOL_CLAUDE.sub("Agent tool", text)
    text = SUBAGENT_TYPE_CLAUDE.sub("`subagent_type`", text)
    return GDD_CLAUDE.sub("#", text)


def split_frontmatter(text):
    """(fm, body); fm is None, если блока нет или он не закрыт."""
    text = norm_newlines(text)
    if not text.startswith("---\n"):
        return None, text
    match = re.compile(r"^---[ \t]*$", re.M).search(text, 4)
    if not match:
        return None, text
    return text[4:match.start()].rstrip("\n"), text[match.end():].lstrip("\n")


def format_frontmatter(body):
    return "---\n" + body.rstrip("\n") + "\n---\n\n"


FORMAT_KEYS = ("claude", "description", "title")

# Ключи-блоки: `ключ: |` и строки с отступом сохраняются как многострочное значение.
BLOCK_KEYS = ("description", "title", "claude", "traits", "tools")


def parse_fm(fm):
    """Плоский разбор: ключ -> строка; `ключ: |` собирается многострочным значением."""
    data, key, block = {}, None, None
    for line in fm.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] not in (" ", "\t") and ":" in line:
            key, value = line.split(":", 1)
            key, value = key.strip(), value.strip()
            block = [] if value == "|" else None
            data[key] = "" if block is not None else value
        elif key and line[:1] in (" ", "\t"):
            if block is not None:
                block.append(line[2:] if line.startswith("  ") else line.strip())
            else:
                data[key] = (data.get(key, "") + " " + line.strip()).strip()
        if block is not None:
            data[key] = "\n".join(block)
    return data


def fm_scalar(value):
    plain = re.search(r":\s|^\s|\s$|#|\"", value) is None and value not in ("true", "false", "null")
    return value if plain else json.dumps(value, ensure_ascii=False)


def parse_trait_list(raw):
    raw = (raw or "").strip()
    if raw.startswith("["):
        return [x.strip() for x in raw.strip("[]").split(",") if x.strip()]
    return [x.strip() for x in raw.split(",") if x.strip()]


def render_frontmatter(pairs, multiline=()):
    lines = ["---"]
    for key, value in pairs:
        if value is None:
            continue
        text = str(value)
        if key in multiline and ("\n" in text or len(text) > 120):
            lines.append("%s: |" % key)
            lines.extend("  " + part if part else "" for part in text.split("\n"))
        else:
            lines.append("%s: %s" % (key, text))
    lines.append("---")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- агенты


MODEL_REVERSE = {"pro": "opus", "flash": "sonnet"}


def convert_model_forward(model):
    tier = MODEL_TIERS.get((model or "").strip())
    if tier is None:
        return DEFAULT_MODELS["specialist"], "model '%s' не распознан -> %s" % (model, DEFAULT_MODELS["specialist"])
    return MODEL_NAMES[tier][0], None


def convert_model_back(name, dz_model):
    tier = "pro" if dz_model == "deepseek-v4-pro" else "flash" if dz_model == "deepseek-flash" else None
    if tier is None:
        return "sonnet", "модель '%s' не из набора -> sonnet" % dz_model
    return MODEL_REVERSE[tier], None


def claude_note(notes):
    return ("<!-- convert: %s -->\n" % "; ".join(notes)) if notes else ""


def convert_agent_to_dz(text):
    fm, body = split_frontmatter(text)
    if fm is None:
        return text, ["нет frontmatter — файл скопирован как есть"]
    meta = parse_fm(fm)
    notes, traits = [], []
    model, warn = convert_model_forward(meta.get("model", ""))
    if warn:
        notes.append(warn)
    traits.append(model)
    tools = meta.get("tools") or meta.get("allowed-tools")
    if tools:
        mapped, dropped = [], []
        for item in parse_trait_list(tools):
            key = item.rstrip("()")
            if key in TOOL_MAP:
                if TOOL_MAP[key] not in mapped:
                    mapped.append(TOOL_MAP[key])
            else:
                dropped.append(item)
        if dropped:
            notes.append("инструменты без прямого аналога в dsh: %s" % ", ".join(dropped))
        if mapped:
            traits.append("tools=" + ",".join(mapped))
    if meta.get("memory"):
        traits.append("memory=local")
    pairs = [("name", meta.get("name")), ("description", meta.get("description")),
             ("traits", ", ".join(traits))]
    return render_frontmatter(pairs, multiline=("description",)) + claude_note(notes) + claude_to_dz(body), notes


def convert_agent_to_claude(text, stem):
    fm, body = split_frontmatter(text)
    if fm is None:
        return text, ["нет frontmatter — файл скопирован как есть"]
    meta = parse_fm(fm)
    notes, tools, extra, model_raw, memory = [], [], [], None, None
    for trait in parse_trait_list(meta.get("traits", "")):
        if "=" in trait:
            key, value = trait.split("=", 1)
            key, value = key.strip(), value.strip()
            if key == "tools":
                mapped, dropped = [], []
                for item in value.split(","):
                    item = item.strip()
                    if not item:
                        continue
                    if item in TOOL_REVERSE:
                        if TOOL_REVERSE[item] not in mapped:
                            mapped.append(TOOL_REVERSE[item])
                    else:
                        dropped.append(item)
                if dropped:
                    notes.append("инструменты без аналога в Claude Code: %s" % ", ".join(dropped))
                tools = mapped
            elif key == "memory":
                memory = "local" if value == "local" else None
            else:
                extra.append(trait)
        elif model_raw is None and MODEL_TIERS.get(trait):
            model_raw = trait
        else:
            extra.append(trait)
    model, warn = convert_model_back(meta.get("name") or stem, model_raw or "flash")
    if warn:
        notes.append(warn)
    if extra:
        notes.append("лишние traits проигнорированы: %s" % ", ".join(extra))
    pairs = [("name", meta.get("name") or stem), ("description", meta.get("description")),
             ("tools", ", ".join(tools) if tools else None), ("model", model), ("memory", memory)]
    return render_frontmatter(pairs, multiline=("description",)) + claude_note(notes) + dz_to_claude(body), notes


def agent_paths(base):
    """Все .md-агенты внутри agents/ (включая вложенные .claude/agent-memory-local). Файлы на `_` —
    шаблоны и черновики, в конвертации не участвуют."""
    root = Path(base) / "agents"
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file() and not p.name.startswith("_"))


def memory_file_name(stem):
    return stem.replace("-", "_") + ".md"




# ---------------------------------------------------------------- память


MEMORY_LINE = re.compile(r"^- \[(?P<title>[^\]]+)\]\((?P<target>[^)]+)\)(?P<rest>.*)$")


def memory_type_from_stem(stem):
    return MEMORY_TYPE_PREFIX.get(stem.split("_", 1)[0], "project")


def memory_entry_to_dz(text, stem):
    """Файл памяти .claude/memory -> формат DeepSeek.

    YAML `.claude` сохраняется целиком под ключом `claude` (для точного обратного импорта), сверху —
    плоские поля, удобные агенту. Ссылки на .claude не переписываются: их заменяет memory/INDEX.md."""
    fm, body = split_frontmatter(text)
    meta = parse_fm(fm) if fm else {}
    kind = (meta.get("metadata.type") or meta.get("type") or "").strip()
    if kind not in MEMORY_TYPE_PREFIX:
        kind = memory_type_from_stem(stem)
    title = (meta.get("title") or meta.get("metadata.title") or "").strip()
    if not title:
        raw = meta.get("description") or stem.replace("_", " ")
        title = re.split(r"\.\s", raw.split("\n")[0])[0].strip().strip('"')
        title = re.sub(r"^(feedback|project|reference|user)[-_]", "", title)
    head = ["---", "schema: 1", "name: %s.md" % stem, "type: %s" % kind,
            "title: %s" % fm_scalar(title.strip()), "source: .claude/memory/%s.md" % stem]
    if meta.get("metadata.category"):
        head.append("category: %s" % fm_scalar(meta["metadata.category"]))
    if meta.get("metadata.modified") or meta.get("modified"):
        head.append("updated: %s" % (meta.get("metadata.modified") or meta.get("modified")))
    head.append("claude: |")
    if fm:
        head.extend("  " + line.rstrip() if line.strip() else "" for line in fm.rstrip("\n").split("\n"))
    head.append("---")
    return "\n".join(head) + "\n\n" + body.lstrip("\n")


def memory_entry_to_claude(text, path):
    """Файл памяти DeepSeek -> (.claude текст, save_as).

    Оригинальный YAML `.claude` (ключ `claude`) восстанавливается байт-в-байт; нет его — собирается
    заново по плоским полям (значит, файл родился в DeepSeek)."""
    fm, body = split_frontmatter(text)
    meta = parse_fm(fm) if fm else {}
    stem = Path(path).stem
    m = re.search(r"\.claude/memory/(.+?)\.md$", meta.get("source", ""))
    save_as = m.group(1) if m and m.group(1) != stem else None
    body = dz_to_claude(body)
    original = meta.get("claude", "")
    if original:
        return format_frontmatter(original) + body.lstrip("\n"), save_as
    kind = meta.get("type") if meta.get("type") in MEMORY_TYPE_PREFIX else memory_type_from_stem(stem)
    lines = ["---", "name: " + fm_scalar(stem.replace("_", "-")),
             "description: " + fm_scalar(meta.get("title") or stem.replace("_", " ")),
             "metadata:", "  node_type: memory", "  type: " + kind,
             "  category: " + fm_scalar(meta.get("category") or "Общие правила проекта"),
             "  originSessionId: " + fm_scalar(meta.get("originSessionId") or "deepseek"),
             "  modified: " + fm_scalar(meta.get("updated") or meta.get("modified") or ""), "---"]
    return "\n".join(lines) + "\n\n" + body.lstrip("\n"), save_as


def index_line_to_dz(line, root):
    m = MEMORY_LINE.match(line)
    if not m:
        return claude_to_dz(line)
    target = m.group("target")
    if "/docs/" in target:
        new = ".deepseek/docs/" + target.split("/docs/", 1)[1]
    elif "/memory/" in target:
        new = ".deepseek/memory/" + Path(target).name
    elif target.startswith("/"):
        new = target
    else:
        name = Path(target).name
        docs_hit = (Path(root) / "docs" / name).is_file()
        new = ".deepseek/docs/" + name if docs_hit else ".deepseek/memory/" + name
    return "- [%s](%s)%s" % (m.group("title"), new, m.group("rest"))


def convert_index_md(text, root):
    out = []
    for line in norm_newlines(text).split("\n"):
        out.append(index_line_to_dz(line, root) if line.startswith("- [") else claude_to_dz(line))
    return "\n".join(out)



# ---------------------------------------------------------------- хуки


HOOK_EVENT_MAP = {"SessionStart": "session_start", "PreCompact": "pre_compact", "PostCompact": "post_compact",
                  "UserPromptSubmit": "user_prompt_submit", "Stop": "stop", "SessionEnd": "session_end",
                  "Notification": "notification", "PreToolUse": "pre_tool_use", "PostToolUse": "post_tool_use"}
HOOK_EVENT_REVERSE = {v: k for k, v in HOOK_EVENT_MAP.items()}


def hooks_from_settings(settings):
    events = []
    for name, groups in ((settings or {}).get("hooks") or {}).items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            group = group or {}
            for hook in group.get("hooks") or []:
                events.append({"event": HOOK_EVENT_MAP.get(name, name), "matcher": group.get("matcher", ""),
                               "type": hook.get("type", "command"), "command": hook.get("command", "")})
    return {"schema": 1,
            "note": "Сгенерировано из .claude/settings.local.json. Поддержку хуков в dsh проверять отдельно — "
                    "см. .deepseek/instructions/runtime.md#hooks.",
            "events": events}


def settings_from_hooks(hooks, current):
    settings = dict(current or {})
    grouped = {}
    for event in (hooks or {}).get("events", []):
        grouped.setdefault(HOOK_EVENT_REVERSE.get(event.get("event"), event.get("event")), []).append(event)
    result = {}
    for name, events in grouped.items():
        by_matcher = {}
        for event in events:
            by_matcher.setdefault(event.get("matcher", ""), []).append(
                {"type": event.get("type", "command"), "command": event.get("command", "")})
        result[name] = [{"matcher": matcher, "hooks": entries} for matcher, entries in by_matcher.items()]
    settings["hooks"] = result
    return settings


# ---------------------------------------------------------------- AGENTS.md


BRIDGE_START = "<!-- dz:bridge:start -->"
BRIDGE_END = "<!-- dz:bridge:end -->"


def bridge_block(root):
    ready = (Path(root) / ".deepseek/docs/agent-system-workflow.md").is_file()
    return claude_to_dz("\n".join([
        BRIDGE_START,
        "",
        "## DeepSeek-раскладка (страховочный контур)",
        "",
        "Рядом с `.claude` лежит каталог `.deepseek` — те же инструкции, агенты, скиллы и документация",
        "для продолжения работы в DeepSeek, если Claude Code недоступен. Карта соответствия и скилл",
        "синхронизации — `.deepseek/README.md`; агентам без явной раскладки читать `.claude` (основной",
        "источник истины).",
        "",
        "- Сгенерировано из `.claude`; править нужно `.claude`, затем `python3 .deepseek/scripts/convert.py export`.",
        "- Обратное слияние: `python3 .deepseek/scripts/convert.py import`.",
        "- Состояние снимка: `python3 .deepseek/scripts/convert.py drift`.",
        "- Готовность dsh-раскладки: %s" % ("workflow на месте" if ready else "workflow ОТСУТСТВУЕТ"),
        "",
        BRIDGE_END,
        "",
    ]))


def strip_block(text, start, end):
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end) + r"\n?", re.S)
    return pattern.sub("", text)


ACCEPT_SECTION = """## Раскладка .deepseek (DeepSeek Harness)

Если Claude Code недоступен, эта же команда работает по раскладке `.deepseek`:

- инструкции проекта — `AGENTS.md` корня репозитория (для dsh) и `CLAUDE.ds.md` (для Claude Code, читается
  из подкаталога);
- агенты, скиллы, документация, память — те же файлы в `.deepseek/agents|skills|docs|memory`;
  карта соответствия — `.deepseek/instructions/bridge.md`;
- спецификация конвертера — `.deepseek/sync/CONVERSION.md`;
- инварианты — `.deepseek/sync/INVARIANTS.md`; регрессия — `python3 .deepseek/scripts/selftest.py`.

Правки вести в `.claude`, затем `python3 .deepseek/scripts/convert.py export`."""


def append_accept_section(claude_md_text):
    """Добавляет в CLAUDE.md короткую секцию-ссылку (идемпотентно)."""
    text = norm_newlines(claude_md_text).rstrip("\n") + "\n"
    if ACCEPT_SECTION.split("\n", 1)[0] in text:
        return text
    return text + "\n" + ACCEPT_SECTION + "\n"


# ---------------------------------------------------------------- копирование


def tree_files(root):
    root = Path(root)
    if not root.is_dir():
        return {}
    return {rel_posix(p, root): p for p in sorted(root.rglob("*")) if p.is_file()}


def docs_files(base):
    root = Path(base) / "docs"
    return {rel: path for rel, path in tree_files(root).items()
            if not rel.startswith(DOCS_SKIP_PREFIXES) and Path(rel).name not in DOCS_SKIP_FILES}


def copy_docs(src_base, dst_base, force, out, counters):
    """Текстовые копии docs/: ссылки между документами не зависят от имени каталога раскладки."""
    src, dst = docs_files(src_base), Path(dst_base) / "docs"
    counters["docs"] = len(src)
    return sum(write_if_changed(dst / rel, read_text(path), force, out) for rel, path in src.items())


def memory_map(root):
    root = Path(root)
    if not root.is_dir():
        return {}
    return {p.stem: p for p in sorted(root.glob("*.md")) if p.stem != "MEMORY"}


def copy_memory(src_base, dst_base, force, out, counters):
    entries = memory_map(Path(src_base) / "memory")
    counters["memory"] = len(entries)
    written = 0
    for stem, path in entries.items():
        content = memory_entry_to_dz(read_text(path), stem)
        if write_if_changed(Path(dst_base) / "memory" / (stem + ".md"), content, force, out):
            written += 1
    return written


def copy_scripts(src_base, dst_base, force, out):
    written = 0
    for rel, path in tree_files(Path(src_base) / "scripts").items():
        if not rel.endswith(".py") or Path(rel).name == "convert.py" or "__pycache__" in rel:
            continue
        if write_if_changed(Path(dst_base) / "scripts" / rel, read_text(path), force, out):
            written += 1
    return written


README = ("README.md", "instructions/bridge.md", "instructions/contracts.md", "instructions/rules.md",
          "instructions/runtime.md", "instructions/checkpoint.md",
          "sync/CONVERSION.md", "sync/MIGRATION.md", "sync/POLICY.md", "sync/HAZARDS.md", "sync/INVARIANTS.md")

# Маркер генерируемого файла: только настоящий HTML-комментарий в начале строки. Так упоминания в
# документации (в обратных кавычках) не считаются.
GENERATED_MARK = re.compile(r"^<!-- GENERATED", re.M)


def copy_skills(src_base, dst_base, direction, force, out, counters):
    written, count = 0, 0
    for rel, path in tree_files(Path(src_base) / "skills").items():
        if "__pycache__" in rel:
            continue
        target = Path(dst_base) / "skills" / rel
        if Path(rel).name != "SKILL.md":
            written += write_if_changed(target, read_text(path), force, out)
            continue
        count += 1
        text = read_text(path)
        if path.suffix.lower() == ".md":
            content = claude_to_dz(text) if direction == "to_dz" else dz_to_claude(text)
        else:
            content = text
        written += write_if_changed(target, content, force, out)
    counters["skills"] = count
    return written


def copy_agents(src_base, dst_base, direction, force, out, counters):
    written, count = 0, 0
    for path in agent_paths(src_base):
        rel = path.relative_to(Path(src_base) / "agents").as_posix()
        if ".claude/agent-memory-local/" in rel:
            agent = rel.split(".claude/agent-memory-local/", 1)[1]
            content = read_text(path)
        else:
            target_rel = rel
            count += 1
            content = convert_agent_pair(path, direction, out, rel)
        target = Path(dst_base) / ("agent-memory-local/" + agent if ".claude/agent-memory-local/" in rel
                                   else "agents/" + target_rel)
        written += write_if_changed(target, content, force, out)
    counters["agents"] = count
    return written


def convert_agent_pair(path, direction, out, rel):
    """direction to_dz/to_claude; предупреждения выводятся один раз на файл."""
    text = read_text(path)
    if direction == "to_dz":
        content, notes = convert_agent_to_dz(text)
    else:
        content, notes = convert_agent_to_claude(text, path.stem)
    if notes and out is not None:
        out.warn("%s: %s" % (rel, "; ".join(notes)))
    return content


def agents_equal(claude_path, dz_path):
    """Совпадает ли пара агентов — с учётом направления правки (в любую сторону)."""
    claude_text, dz_text = read_text(claude_path), read_text(dz_path)
    return (convert_agent_to_dz(claude_text)[0] == dz_text
            or convert_agent_to_claude(dz_text, dz_path.stem)[0] == claude_text)



# ---------------------------------------------------------------- EXPORT


def schema_dict(text):
    result = {}
    for line in norm_newlines(text).split("\n"):
        if not line or line.startswith("#") or line.startswith("  ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def render_schema(root, generated_at):
    values = schema_dict(DZ_SCHEMA)
    values["converted_at"] = generated_at
    lines = ["# Схема `.deepseek` — временная страховка на случай блокировки Claude Code.",
             "# Машинный файл: обновляет convert.py при export.",
             "schema: 1", "layout: .deepseek", "engine: deepseek",
             "generated_by: " + GENERATOR, "converted_at: " + values["converted_at"],
             "source_layout: .claude", "description: >-",
             "  Зеркало `.claude`: инструкции, агенты, скиллы, документация и память проекта для",
             "  продолжения работы в DeepSeek Harness (dsh), когда Claude Code недоступен.",
             "repositories:",
             "  - " + Path(root).name]
    return "\n".join(lines) + "\n"


def cmd_export(root, args, out):
    claude, dz = Path(root) / ".claude", Path(root) / ".deepseek"
    if not claude.is_dir():
        out.warn("нет .claude — экспортировать нечего")
        return 1
    counters, changed = {}, 0
    claude_md = Path(root) / "CLAUDE.md"

    if claude_md.is_file():
        source = read_text(claude_md)
        project = split_block(split_block(source, BRIDGE_START, BRIDGE_END), ACCEPT_SECTION)
        project = claude_to_dz(project.rstrip()) + "\n"
        body = PROJECT_HEADER + project + RESTORE_BLOCK
        changed += write_if_changed(dz / "instructions/project.md", body, args.force, out)
        agents_md = PROJECT_HEADER + project + bridge_block(root) + RESTORE_BLOCK.strip("\n") + "\n"
        changed += write_if_changed(Path(root) / "AGENTS.md", agents_md, args.force, out)
        pointer = "<!-- GENERATED из CLAUDE.md. DEEPSEEK-ONLY правила — .deepseek/instructions/project.md, " \
                  "далее .deepseek/instructions/rules.md -->\n\n" + ACCEPT_SECTION + "\n"
        changed += write_if_changed(dz / "CLAUDE.ds.md", pointer, args.force, out)
    else:
        out.warn("CLAUDE.md не найден — AGENTS.md, instructions/project.md и CLAUDE.ds.md не обновлялись")

    changed += copy_agents(claude, dz, "to_dz", args.force, out, counters)
    changed += copy_skills(claude, dz, "to_dz", args.force, out, counters)
    changed += copy_docs(claude, dz, args.force, out, counters)
    changed += copy_memory(claude, dz, args.force, out, counters)
    changed += copy_scripts(claude, dz, args.force, out)

    index_src = claude / "memory/MEMORY.md"
    if index_src.is_file():
        text = convert_index_md(read_text(index_src), dz)
        changed += write_if_changed(dz / "memory/MEMORY.md", text, args.force, out)
        index = ("# Индекс памяти проекта\n\nРаздел «DeepSeek» читают агенты под dsh: здесь обычные ссылки,\n"
                 "работают и в браузере. Раздел «Claude Code» — копия `.claude/memory/MEMORY.md` без правок.\n\n"
                 "## DeepSeek\n\n" + text + "\n## Claude Code (как в .claude)\n\n" + read_text(index_src))
        changed += write_if_changed(dz / "memory/INDEX.md", index, args.force, out)

    hooks_src = claude / "settings.local.json"
    settings = load_json(hooks_src) if hooks_src.is_file() else None
    if settings is not None:
        changed += write_if_changed(dz / "hooks.json", dump_json(hooks_from_settings(settings)), args.force, out)

    state_src = claude / "session_state.json"
    if state_src.is_file():
        changed += write_if_changed(dz / "state/session_state.json", read_text(state_src), args.force, out)

    changed += write_if_changed(dz / "schema.yml", render_schema(root, now()), args.force, out)
    append_state(dz, "export", "снимок .claude -> .deepseek", counters)
    out.line("")
    out.line("export: записано файлов — %d (агентов %s, скиллов %s, документов %s, записей памяти %s)" % (
        changed, counters.get("agents", 0), counters.get("skills", 0), counters.get("docs", 0),
        counters.get("memory", 0)))
    return 0


def split_block(text, start, end=None):
    """Удаляет блок start..end (включительно); без end — до конца файла."""
    at = text.find(start)
    if at < 0:
        return text
    stop = text.find(end, at) if end else -1
    if stop < 0:
        return text[:at]
    return text[:at] + text[stop + len(end):]


def append_state(dz, action, summary, counters):
    path = Path(dz) / "sync/STATE.md"
    if not path.is_file():
        return
    with path.open("a", encoding="utf-8") as fh:
        fh.write("| %s | %s | %s | %s |\n" % (now(), action, summary, json.dumps(counters, ensure_ascii=False)))



# ---------------------------------------------------------------- IMPORT


def cmd_import(root, args, out):
    claude, dz = Path(root) / ".claude", Path(root) / ".deepseek"
    if not dz.is_dir():
        out.warn("нет .deepseek — импортировать нечего")
        return 1
    counters = {"docs": 0, "memory": 0, "state": 0}
    conflicts, notes = [], []

    src_docs, dst_docs = docs_files(dz), docs_files(claude)   # docs: текст общий, переносим в обе стороны
    for rel, path in src_docs.items():
        if write_if_changed(claude / "docs" / rel, read_text(path), args.force, out):
            counters["docs"] += 1
    for rel, path in dst_docs.items():
        if rel not in src_docs and write_if_changed(dz / "docs" / rel, read_text(path), args.force, out):
            counters["docs"] += 1

    claude_memory = claude / "memory"
    claude_memory.mkdir(parents=True, exist_ok=True)

    # агенты, которых в .claude ещё нет: DeepSeek-формат -> формат Claude Code
    for path in agent_paths(dz):
        rel = path.relative_to(dz / "agents").as_posix()
        target = claude / "agents" / rel
        if target.is_file() and not args.force:
            continue
        if write_if_changed(target, convert_agent_pair(path, "to_claude", out, rel), args.force, out):
            out.line("  new      .claude/agents/%s (создан import)" % rel)
    for stem, path in memory_map(dz / "memory").items():      # память: назад в .claude-формат
        rendered, save_as = memory_entry_to_claude(read_text(path), path)
        target = claude_memory / ((save_as or stem) + ".md")
        if target.is_file() and not args.force:
            if read_text(target).strip() != rendered.strip():
                conflicts.append(rel_posix(target, root))
            continue
        if write_if_changed(target, rendered, args.force, out):
            counters["memory"] += 1
    for stem, path in memory_map(claude_memory).items():       # и обратно: новое в .claude
        if not (dz / "memory" / (stem + ".md")).is_file():
            content = memory_entry_to_dz(read_text(path), stem)
            if write_if_changed(dz / "memory" / (stem + ".md"), content, args.force, out):
                counters["memory"] += 1

    for rel, path in tree_files(dz / "notes").items():         # заметки DeepSeek -> личная память агентов
        if rel.startswith("TEMPLATE") or not rel.endswith(".md"):
            continue
        text = read_text(path)
        agent = re.search(r"^agent:\s*(\S+)", text, re.M)
        value = re.search(r"## Запись\n(.*)\Z", text, re.S)
        if not agent or not value:
            notes.append("notes/%s: нет полей agent/Запись — пропущено" % rel)
            continue
        entry = text.split("\n")[0].lstrip("# ").strip() or Path(rel).stem
        agent_dir = claude / "agents/.claude/agent-memory-local" / agent.group(1)
        body = "# %s\n\nПеренесено из DeepSeek-заметки, сессия %s.\n\n%s\n" % (
            entry, now()[:10], value.group(1).strip())
        if write_if_changed(agent_dir / ("deepseek_%s.md" % Path(rel).stem), body, True, out):
            counters["state"] += 1
        index = agent_dir / "MEMORY.md"
        line = "- [%s](deepseek_%s.md) — перенесено из DeepSeek %s\n" % (entry, Path(rel).stem, now()[:10])
        old = read_text(index) if index.is_file() else ""
        if line not in old:
            write_if_changed(index, (old.rstrip("\n") + "\n" if old else "") + line, True, out)

    hooks_src = dz / "hooks.json"
    settings_path = claude / "settings.local.json"
    if hooks_src.is_file():
        current = load_json(settings_path) if settings_path.is_file() else {}
        merged = settings_from_hooks(load_json(hooks_src), current)
        if write_if_changed(settings_path, dump_json(merged), args.force, out):
            counters["state"] += 1
    state_src = dz / "state/session_state.json"
    if state_src.is_file() and write_if_changed(claude / "session_state.json", read_text(state_src),
                                                args.force, out):
        counters["state"] += 1

    append_state(dz, "import", "перенос .deepseek -> .claude", counters)
    out.line("")
    out.line("import: документов %d, записей памяти %d, служебных %d" % (
        counters["docs"], counters["memory"], counters["state"]))
    for conflict in conflicts:
        out.warn("расхождение, файл оставлен как в .claude (--force перезапишет): %s" % conflict)
    for note in notes:
        out.warn(note)
    return 1 if conflicts and args.strict else 0



# ---------------------------------------------------------------- CHECK


def check_pairs(root):
    claude, dz = Path(root) / ".claude", Path(root) / ".deepseek"
    pairs = []
    for path in agent_paths(claude):
        rel = path.relative_to(claude / "agents").as_posix()
        if ".claude/agent-memory-local/" in rel:
            agent = rel.split(".claude/agent-memory-local/", 1)[1]
            pairs.append(("agent", "agents/" + rel, "agent-memory-local/" + agent))
        else:
            pairs.append(("agent", "agents/" + rel, "agents/" + rel))
    for rel in tree_files(claude / "skills"):
        pairs.append(("skill", "skills/" + rel, "skills/" + rel))
    for rel in docs_files(claude):
        pairs.append(("docs", "docs/" + rel, "docs/" + rel))
    for stem in memory_map(claude / "memory"):
        pairs.append(("memory", "memory/%s.md" % stem, "memory/%s.md" % stem))
    if (claude / "settings.local.json").is_file():
        pairs.append(("hooks", "settings.local.json", "hooks.json"))
    if (claude / "session_state.json").is_file():
        pairs.append(("state", "session_state.json", "state/session_state.json"))
    known = {p[1] for p in pairs}
    for path in agent_paths(dz):                       # зеркало, которого уже нет в .claude
        rel = path.relative_to(dz / "agents").as_posix()
        if "agents/" + rel not in known:
            pairs.append(("agent", "agents/" + rel, "agents/" + rel))
    return pairs


def pair_status(root, kind, src, dst):
    claude, dz = Path(root) / ".claude", Path(root) / ".deepseek"
    spath, dpath = claude / src, dz / dst
    if not spath.is_file():
        return "new"
    if not dpath.is_file():
        return "missing"
    text = read_text(dpath)
    if kind == "agent":
        same = agents_equal(spath, dpath)
    elif kind == "memory":
        same = memory_entry_to_claude(text, dpath)[0] == read_text(spath) or \
            memory_entry_to_dz(read_text(spath), spath.stem) == text
    elif kind == "hooks":
        same = hooks_from_settings(load_json(spath)) == (load_json(dpath) or {})
    elif kind == "skill" and dpath.suffix == ".md":
        source = read_text(spath)
        same = claude_to_dz(source) == text
    else:
        same = read_text(spath) == text
    return "ok" if same else "changed"


def cmd_check(root, args, out):
    rows = [(pair_status(root, *p), p[1], p[2]) for p in check_pairs(root)]
    for code, src, dst in rows:
        out.item(code, src, "-> %s" % dst)
    problems = [r for r in rows if r[0] != "ok"]
    out.line("")
    out.line("check: файлов %d, в синхронизации %d, changed %d, new %d, missing %d" % (
        len(rows), len(rows) - len(problems), sum(r[0] == "changed" for r in rows),
        sum(r[0] == "new" for r in rows), sum(r[0] == "missing" for r in rows)))
    if any(r[0] == "missing" for r in rows):
        out.line("missing — нет в .deepseek: `export` (или `export --force`).")
    if problems:
        out.line("changed/new — по смыслу: правка .claude -> export; правка DeepSeek -> import.")
    return 1 if problems and args.strict else 0


# ---------------------------------------------------------------- DRIFT


def cmd_drift(root, args, out):
    claude, dz = Path(root) / ".claude", Path(root) / ".deepseek"
    issues, blocking = [], False

    behind = [p for p in check_pairs(root) if pair_status(root, *p) != "ok"]
    if behind:
        blocking = True
        issues.append("снимок отстал: %d файл(ов) расходятся с .claude — нужен export" % len(behind))
        for code, src, dst in behind[:8]:
            out.item(code, src, "-> %s" % dst)
        if len(behind) > 8:
            out.item("...", "и ещё %d" % (len(behind) - 8))
        missing = [p for p in behind if pair_status(root, *p) == "missing"]
        if missing:
            issues.append("нет пары в .deepseek (агент/файл заведён в .claude): %s — сначала `export`, "
                          "потом решение по POLICY.md" % ", ".join(p[1] for p in missing[:5]))

    hand = [rel for rel in README if is_generated(dz / rel)]
    hand += ["sync/" + rel for rel, path in tree_files(dz / "sync").items() if is_generated(path)]
    if hand:
        issues.append("ручные файлы .deepseek заменены сгенерированными: %s" % ", ".join(hand))

    leaked = []
    for path in [Path(root) / "CLAUDE.md"] + list(tree_files(claude).values()):
        if not path.is_file():
            continue
        for number, line in enumerate(norm_newlines(read_text(path)).split("\n"), 1):
            if ".deepseek" in line or "/deepseek/" in line:
                leaked.append("%s:%d" % (rel_posix(path, root), number))
    if leaked:
        issues.append("ссылки на .deepseek в .claude (конвертер их переводит, но лучше не допускать): %s"
                      % ", ".join(leaked[:6]))

    required = [rel for rel in ("instructions/project.md", "CLAUDE.ds.md", "schema.yml",
                                "sync/INVARIANTS.md", "sync/STATE.md", "README.md")
                if not (dz / rel).is_file()]
    if (claude / "memory/MEMORY.md").is_file() and not (dz / "memory/INDEX.md").is_file():
        required.append("memory/INDEX.md")
    if required:
        blocking = True
        issues.append("нет обязательных файлов: %s — запусти `export --force`" % ", ".join(required))

    bridge = Path(root) / "AGENTS.md"
    if not bridge.is_file():
        blocking = True
        issues.append("нет AGENTS.md в корне — запусти `export`")
    elif BRIDGE_START not in read_text(bridge):
        issues.append("AGENTS.md без блока dz:bridge — правлен руками или не генерировался")

    for text in issues:
        out.line("* " + text)
    if not issues:
        out.line("drift: расхождений нет — снимок совпадает с .claude, ручные файлы на месте.")
    return 1 if issues and args.strict else 0



# ---------------------------------------------------------------- STATUS


def cmd_status(root, args, out):
    claude, dz = Path(root) / ".claude", Path(root) / ".deepseek"
    schema = schema_dict(read_text(dz / "schema.yml")) if (dz / "schema.yml").is_file() else {}
    rows = [("агенты", len(agent_paths(claude)), len(agent_paths(dz))),
            ("скиллы (SKILL.md)", len([1 for r in tree_files(claude / "skills") if r.endswith("SKILL.md")]),
             len([1 for r in tree_files(dz / "skills") if r.endswith("SKILL.md")])),
            ("документы docs/", len(docs_files(claude)), len(docs_files(dz))),
            ("память memory/", len(memory_map(claude / "memory")), len(memory_map(dz / "memory")))]
    out.line("схема .deepseek: %s, снимок от %s" % (schema.get("schema", "—"), schema.get("converted_at", "—")))
    out.line("")
    out.line("%-22s %8s %10s" % ("раскладка", ".claude", ".deepseek"))
    for label, left, right in rows:
        out.line("%-22s %8d %10d" % (label, left, right))
    state = {"ok": 0, "changed": 0, "new": 0, "missing": 0}
    for pair in check_pairs(root):
        state[pair_status(root, *pair)] += 1
    out.line("")
    out.line("синхронизация: %s" % ", ".join("%s %d" % (k, v) for k, v in state.items() if v))
    return 0



# ---------------------------------------------------------------- SYNC-AGENTS

AGENT_GROUPS = ("analysts", "developers", "librarians", "integration")


def _agent_pairs(root, direction):
    """[(группа, путь источника, путь назначения)] по всем группам агентов."""
    base = Path(root)
    src_base = base / (".claude" if direction == "to_dz" else ".deepseek")
    dst_base = base / (".deepseek" if direction == "to_dz" else ".claude")
    result = []
    for group in AGENT_GROUPS:
        src_dir = src_base / "agents" / group
        if not src_dir.is_dir():
            continue
        for src in sorted(src_dir.glob("*.md")):
            if src.name.startswith(("_", ".")):
                continue
            result.append((group, src, dst_base / "agents" / group / src.name))
    return result


def agent_body(path):
    return split_frontmatter(read_text(path))[1]


def render_agent(path, direction):
    text = read_text(path)
    if direction == "to_dz":
        return convert_agent_to_dz(text)[0]
    return convert_agent_to_claude(text, path.stem)[0]


def body_diff(src_body, dst_body, normalize):
    """
    Отличия правил. Источник приводится к системе назначения только для путей и якорей; сравнение
    идёт со строками назначения как есть. Возвращает (only_src, only_dst).
    """
    src_lines = [l.strip() for l in norm_newlines(normalize(src_body)).split("\n") if l.strip()]
    dst_lines = [l.strip() for l in norm_newlines(dst_body).split("\n") if l.strip()]
    remaining = list(dst_lines)
    only_src = []
    for line in src_lines:
        if line in remaining:
            remaining.remove(line)
        else:
            only_src.append(line)
    return only_src, remaining


def gdd_anchor_diff(src_body, dst_body, direction):
    """
    Отдельная проверка форм ссылок на ГДД: `#gdd-x` в `.claude` соответствует `gdd-x` в `.deepseek`.
    Возвращает список расхождений (строка источника, ожидаемая в назначении, фактическая).
    """
    def bare(text):
        return text.replace("`#gdd-", "`gdd-")

    def sharp(text):
        return re.sub(r"`gdd-", "`#gdd-", text)

    expected, actual = src_body, dst_body
    if direction == "to_dz":
        expected = bare(src_body)      # источник .claude -> назначение .deepseek
    else:
        actual = sharp(dst_body)       # назначение .claude получает форму с #
        expected = src_body
    problems = []
    for src_line in expected.split("\n"):
        if "`gdd-" not in src_line:
            continue
        match = [l for l in actual.split("\n") if l.strip() == src_line.strip()]
        if not match:
            problems.append(src_line.strip())
    return problems


def cmd_sync_agents(root, args, out):
    direction = args.direction
    if direction not in ("to_dz", "to_claude"):
        out.warn("sync-agents: укажите направление --direction to_dz | to_claude")
        return 2
    if args.apply and not args.yes:
        out.warn("sync-agents: запись файлов требует подтверждения Пользователя — --apply --yes")
        return 2

    base = Path(root)
    normalize = claude_to_dz if direction == "to_dz" else dz_to_claude
    src_label = ".claude" if direction == "to_dz" else ".deepseek"
    dst_label = ".deepseek" if direction == "to_dz" else ".claude"

    create, differs, same = [], [], 0
    for _group, src, dst in _agent_pairs(root, direction):
        if not dst.exists():
            create.append((src, dst))
            continue
        only_src, only_dst = body_diff(agent_body(src), agent_body(dst), normalize)
        anchors = gdd_anchor_diff(agent_body(src), agent_body(dst), direction)
        if anchors:
            only_src = list(only_src) + ["[якорь ГДД] " + line for line in anchors]
        if only_src or only_dst:
            differs.append((dst, only_src, only_dst))
        else:
            same += 1

    for src, dst in create:
        out.line("СОЗДАТЬ   %s -> %s" % (rel_posix(src, base), rel_posix(dst, base)))
        if args.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(render_agent(src, direction), encoding="utf-8")

    for dst, only_src, only_dst in differs:
        out.line("")
        out.line("ОТЛИЧИЯ   %s" % rel_posix(dst, base))
        for line in only_src[:30]:
            out.line("  + %s" % line)
        if len(only_src) > 30:
            out.line("  ... ещё %d" % (len(only_src) - 30))
        for line in only_dst[:15]:
            out.line("  - %s" % line)
        if len(only_dst) > 15:
            out.line("  ... ещё %d" % (len(only_dst) - 15))

    out.line("")
    out.line("sync-agents %s -> %s: создать %d, с отличиями %d, без отличий %d%s" % (
        src_label, dst_label, len(create), len(differs), same,
        "" if args.apply else " (пробный прогон, файлы не менялись)"))
    return 0

# ---------------------------------------------------------------- CLI


def main(argv=None):
    parser = argparse.ArgumentParser(prog="convert.py", description="Конвертер .claude <-> .deepseek.")
    parser.add_argument("command", choices=("export", "import", "check", "drift", "status", "sync-agents"))
    parser.add_argument("--repo", default=None, help="корень репозитория (по умолчанию — два уровня выше скрипта)")
    parser.add_argument("--force", action="store_true", help="перезаписать даже при совпадении/конфликте")
    parser.add_argument("--strict", action="store_true", help="код возврата 1 при расхождениях")
    parser.add_argument("--direction", default=None, choices=("to_dz", "to_claude"),
                        help="sync-agents: направление переноса")
    parser.add_argument("--apply", action="store_true", help="sync-agents: записать файлы")
    parser.add_argument("--yes", action="store_true", help="sync-agents: подтверждение Пользователя")
    args = parser.parse_args(argv)
    root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[2]
    out = Out()
    handler = {"export": cmd_export, "import": cmd_import, "check": cmd_check,
               "drift": cmd_drift, "status": cmd_status,
               "sync-agents": cmd_sync_agents}[args.command]
    return handler(root, args, out)


if __name__ == "__main__":
    sys.exit(main())


