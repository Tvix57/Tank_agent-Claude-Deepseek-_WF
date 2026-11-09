#!/usr/bin/env python3
"""Проверка, что сессия DeepSeek стартовала правильно (см. `.deepseek/instructions/checkpoint.md`).

Запуск из корня репозитория: `python3 .deepseek/scripts/preflight.py`. Код 0 — можно работать,
1 — есть блокеры (что именно, печатается). Только stdlib.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True


def git(root, *args):
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def run(root, script, *args):
    proc = subprocess.run([sys.executable, str(root / ".deepseek/scripts" / script), *args],
                          capture_output=True, text=True, cwd=str(root))
    return proc.stdout


def load_state(root):
    path = root / ".deepseek/state/session.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def check(root, state):
    """Список (уровень, текст): уровень — 'БЛОК' или 'ВНИМАНИЕ'."""
    problems = []
    if not (root / ".claude").is_dir() or not (root / ".deepseek").is_dir():
        return [("БЛОК", "нет .claude или .deepseek — preflight только для репозитория с контуром")]

    # 1. Снимок свежий
    line = next((l for l in run(root, "convert.py", "check").split("\n") if l.startswith("check:")), "")
    if "changed 0, new 0, missing 0" not in line:
        problems.append(("БЛОК", "снимок .deepseek расходится с .claude — `convert.py export --force`"
                                + (" (%s)" % line if line else "")))

    # 2. Сессия начата с checkpoint
    if not state.get("checkpointPasted"):
        problems.append(("БЛОК", "checkpoint не отмечен: вставь `.deepseek/instructions/checkpoint.md` в первое "
                                 "сообщение, затем `preflight.py --confirm-checkpoint`"))

    # 3. Ветка и тип задачи
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    last_path = root / ".deepseek/state/session_state.json"
    last = None
    if last_path.is_file():
        try:
            last = json.loads(last_path.read_text(encoding="utf-8")).get("lastBranch")
        except ValueError:
            last = None
    if state.get("checkpointPasted") and branch and branch != last and not state.get("taskType"):
        problems.append(("БЛОК", "ветка %s ≠ lastBranch %s — уточни тип задачи и запусти "
                                 "`preflight.py --task-type new|extend|bug --confirm-checkpoint`" % (branch, last)))
    if branch in ("master", "main") and state.get("mode") in ("B", "C"):
        problems.append(("ВНИМАНИЕ", "режим %s в ветке %s — нужна ветка `-deepseek` (`sync/POLICY.md`)"
                        % (state.get("mode"), branch)))

    # 4. Чистое дерево
    status = git(root, "status", "--porcelain")
    if status:
        problems.append(("ВНИМАНИЕ", "незакоммиченных изменений: %d — зафиксируй или осознанно оставь"
                        % len(status.split("\n"))))

    # 5. Журнал dsh для контроля токенов
    try:
        report = json.loads(run(root, "token_usage_check_dsh.py", "60") or "{}")
    except ValueError:
        report = {}
    if report.get("error") == "sessions-root not found":
        problems.append(("ВНИМАНИЕ", "контроль токенов не найдёт журнал dsh: --sessions-root или "
                                     "DSH_SESSIONS_ROOT (runtime.md#tokens)"))
    elif report.get("error") == "zstd-session-log":
        problems.append(("ВНИМАНИЕ", "журнал dsh сжат zstd: `pip install zstandard` или compression none "
                                     "(runtime.md#tokens)"))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(prog="preflight.py", description="Старт сессии DeepSeek.")
    parser.add_argument("--repo", default=None)
    parser.add_argument("--confirm-checkpoint", action="store_true",
                        help="отметить, что checkpoint вставлен в первое сообщение")
    parser.add_argument("--task-type", choices=("new", "extend", "bug"), default=None,
                        help="тип задачи при смене ветки")
    parser.add_argument("--mode", choices=("A", "B", "C"), default=None, help="режим работы (POLICY.md)")
    args = parser.parse_args(argv)
    root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[2]
    state = load_state(root)

    if any((args.confirm_checkpoint, args.task_type, args.mode)):
        if args.confirm_checkpoint:
            state["checkpointPasted"] = True
            state["pastedAt"] = datetime.now().astimezone().isoformat(timespec="seconds")
        if args.task_type:
            state["taskType"] = args.task_type
        if args.mode:
            state["mode"] = args.mode
        branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
        if branch:
            state["branch"] = branch
            (root / ".deepseek/state/session_state.json").write_text(
                json.dumps({"lastBranch": branch}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        path = root / ".deepseek/state/session.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    problems = check(root, state)
    for level, text in problems:
        print("%s %s" % ("✗" if level == "БЛОК" else "!", text))
    blockers = [p for p in problems if p[0] == "БЛОК"]
    print("")
    if blockers:
        print("preflight: блокеров %d — сессию не начинать" % len(blockers))
        return 1
    print("preflight: готово к работе" + ("" if not problems else " (предупреждений %d)" % len(problems)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

