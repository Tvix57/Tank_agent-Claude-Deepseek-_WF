#!/usr/bin/env python3
"""Проверка инвариантов `.deepseek` (`.deepseek/sync/INVARIANTS.md`).

Запуск: `python3 .deepseek/scripts/selftest.py [--repo <корень>]`. Код 0 — все инварианты выполнены,
1 — есть нарушения (список печатается). Только stdlib.
"""

import argparse
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

MARKER = "<!-- GENERATED"
TOOLS = ("read", "bash", "write", "edit", "task", "skill", "grep", "glob",
         "web_search", "web_fetch", "message")
HAND_FILES = ("README.md", "instructions/bridge.md", "instructions/contracts.md", "instructions/rules.md",
              "instructions/runtime.md", "instructions/checkpoint.md", "sync/CONVERSION.md",
              "sync/MIGRATION.md", "sync/POLICY.md", "sync/HAZARDS.md", "sync/INVARIANTS.md")
GENERATED = ("CLAUDE.ds.md", "instructions/project.md", "schema.yml")
GENERATED_MARK = re.compile(r"^<!-- GENERATED", re.M)
EXCLUDE_PATTERNS = ("AGENTS.md",)


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def files(root, pattern="*"):
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob(pattern) if p.is_file())


def check(root):
    repo, dz, claude = Path(root), Path(root) / ".deepseek", Path(root) / ".claude"
    problems = []

    # 1. .claude не ссылается на .deepseek (CLAUDE.md исключён: туда секция не добавляется)
    for path in files(claude, "*.md"):
        for number, line in enumerate(read(path).split("\n"), 1):
            if ".deepseek" in line:
                problems.append("#1 %s:%d — ссылка на .deepseek в .claude" % (
                    path.relative_to(repo).as_posix(), number))

    # 2. ручные файлы на месте и не помечены как генерируемые
    for rel in HAND_FILES:
        text = read(dz / rel)
        if not text:
            problems.append("#2 нет ручного файла: .deepseek/%s" % rel)
        elif GENERATED_MARK.search(text):
            problems.append("#2 .deepseek/%s помечен как GENERATED" % rel)

    # 3. генерируемые файлы на месте и в ожидаемом виде
    for rel in GENERATED:
        path = dz / rel
        text = read(path)
        if not text:
            problems.append("#3 нет файла: .deepseek/%s (запусти export)" % rel)
            continue
        if rel == "schema.yml" and "schema: 1" not in text:
            problems.append("#3 .deepseek/schema.yml без `schema: 1`")
        if rel == "instructions/project.md" and "AGENTS.md — правила проекта" not in text:
            problems.append("#3 .deepseek/instructions/project.md без шапки правил проекта")
        if rel == "CLAUDE.ds.md" and "Раскладка .deepseek" not in text:
            problems.append("#3 .deepseek/CLAUDE.ds.md без секции-указателя")

    # 4. у каждого агента .claude есть пара в .deepseek
    for path in files(claude / "agents", "*.md"):
        rel = path.relative_to(claude / "agents").as_posix()
        if ".claude/agent-memory-local/" in rel:
            agent = rel.split(".claude/agent-memory-local/", 1)[1]
            twin = dz / "agent-memory-local" / agent
        else:
            twin = dz / "agents" / rel
        if not twin.is_file():
            problems.append("#4 нет пары для .claude/agents/%s" % rel)

    # 5. у каждого документа .claude есть пара в .deepseek
    for path in files(claude / "docs", "*.md"):
        rel = path.relative_to(claude / "docs").as_posix()
        if rel.startswith(("incoming/", ".claude/")):
            continue
        if not (dz / "docs" / rel).is_file():
            problems.append("#5 нет пары для .claude/docs/%s" % rel)

    # 6. AGENTS.md: шапка и блок dz:bridge
    agents_md = read(repo / "AGENTS.md")
    if "AGENTS.md — правила проекта" not in agents_md:
        problems.append("#6 AGENTS.md без шапки правил проекта")
    if "<!-- dz:bridge:start -->" not in agents_md:
        problems.append("#6 AGENTS.md без блока dz:bridge")

    # 7. bridge.md содержит все инструменты
    bridge = read(dz / "instructions/bridge.md")
    for tool in TOOLS:
        if not re.search(r"`%s`" % re.escape(tool), bridge):
            problems.append("#7 bridge.md без инструмента `%s`" % tool)

    # 8. convert.py/selftest.py симметричны между репозиториями
    # Имена каталогов различаются (`client`/`server` в рабочем каталоге, `Client`/`Server` в WF-папке),
    # поэтому сосед ищется без учёта регистра.
    names = ("server", "Server") if repo.name.lower() == "client" else ("client", "Client")
    sibling = next((repo.parent / name for name in names if (repo.parent / name).is_dir()), None)
    if sibling is not None:
        for name in ("convert.py", "selftest.py"):
            mine, other = dz / "scripts" / name, sibling / ".deepseek/scripts" / name
            if other.is_file() and mine.read_bytes() != other.read_bytes():
                problems.append("#8 scripts/%s расходится с %s/.deepseek/scripts/%s" % (
                    name, sibling.name, name))

    # 9. схема
    if "schema: 1" not in read(dz / "schema.yml"):
        problems.append("#9 .deepseek/schema.yml отсутствует или schema != 1")

    # 10. журнал
    if "export" not in read(dz / "sync/STATE.md") and "import" not in read(dz / "sync/STATE.md"):
        problems.append("#10 sync/STATE.md без строк export/import")

    # 11. в агентах и скиллах нет ссылок на .claude
    for path in files(dz / "agents", "*.md") + [p for p in files(dz / "skills", "*.md")]:
        for number, line in enumerate(read(path).split("\n"), 1):
            if "](" in line and ".claude/" in line:
                problems.append("#11 %s:%d — ссылка на .claude" % (path.relative_to(repo).as_posix(), number))
                break

    # 12. контур исключён из git через .git/info/exclude.
    # Решение Пользователя 2026-11-06: `.deepseek/` под git, `.claude/` под git — восстановление
    # рабочих файлов идёт по фалам с ревью, поэтому исключения нет. Требуется только AGENTS.md:
    # он генерируется конвертером и не должен попадать в историю.
    # Контур может лежать вне рабочего репозитория (WF-папка вне контейнера, `/wf/Client`): git-корня
    # рядом нет, исключение настраивается в рабочем каталоге (`/workspace/client`) — здесь проверять нечего.
    if (repo / ".git").exists():
        exclude = read(repo / ".git/info/exclude")
        for pattern in EXCLUDE_PATTERNS:
            if not any(line.strip() == pattern for line in exclude.split("\n")):
                problems.append("#12 .git/info/exclude без строки `%s` (контур попадёт в git status)" % pattern)

    # 13. скрипты контура: компилируются и считают токены на синтетическом журнале dsh
    problems.extend(check_dsh_scripts(repo))
    return problems


def check_dsh_scripts(repo):
    """Компиляция всех скриптов + прогон token_usage_check_dsh.py на синтетическом журнале."""
    import json
    import subprocess
    import tempfile

    dz = repo / ".deepseek"
    problems = []
    scripts = sorted((dz / "scripts").glob("*.py"))
    for script in scripts:
        proc = subprocess.run([sys.executable, "-m", "py_compile", str(script)], capture_output=True, text=True)
        if proc.returncode != 0:
            problems.append("#13 %s не компилируется: %s" % (script.name, proc.stderr.strip().split("\n")[-1]))

    token_script = dz / "scripts/token_usage_check_dsh.py"
    if not token_script.is_file():
        problems.append("#13 нет scripts/token_usage_check_dsh.py — контроль токенов не работает")
        return problems
    with tempfile.TemporaryDirectory() as tmp:
        session_dir = Path(tmp) / "--w--" / "s1"
        session_dir.mkdir(parents=True)
        now_ms = int(__import__("time").time() * 1000)
        rows = [{"type": "session/header", "seq": 0, "time": now_ms, "data": {}}]
        for i in range(6):
            rows.append({"type": "llm/response", "seq": i + 1, "time": now_ms,
                         "data": {"usage": {"inputTokens": 1000, "outputTokens": 1000,
                                            "cacheReadTokens": 9000}}})
        (session_dir / "session.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, str(token_script), "3600", "--sessions-root", tmp],
                              capture_output=True, text=True)
        try:
            report = json.loads(proc.stdout)
        except ValueError:
            problems.append("#13 token_usage_check_dsh.py не вернул JSON: %s" % proc.stdout[:200])
            return problems
        expected = {"idle": False, "requests": 6, "total_input": 60000, "output_tokens": 6000}
        got = {"idle": report.get("idle"), "requests": report.get("base_session", {}).get("requests"),
               "total_input": report.get("base_session", {}).get("total_input"),
               "output_tokens": report.get("base_session", {}).get("output_tokens")}
        if got != expected:
            problems.append("#13 token_usage_check_dsh.py считает неверно: %s вместо %s" % (got, expected))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(prog="selftest.py", description="Инварианты .deepseek.")
    parser.add_argument("--repo", default=None)
    args = parser.parse_args(argv)
    root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[2]
    problems = check(root)
    for problem in problems:
        print("✗ " + problem)
    print("")
    print("selftest: нарушений %d" % len(problems) if problems else "selftest: все инварианты выполнены")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
