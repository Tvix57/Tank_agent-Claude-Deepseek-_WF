#!/usr/bin/env python3
"""Пересоздаёт симлинки рабочих каталогов на WF-папку (инструкции живут вне контейнера).

Запуск: `python3 tools/link_workspaces.py --workdir <папка с client/ и server/>`. Ссылки абсолютные,
на `<container-root>/<Project>/...` (по умолчанию `/wf`): на хосте они висят, в контейнере работают.
Обычные файлы перед заменой копируются в `<workdir>/.wf-backup/repo-files-<дата>/`.

Исключения инструкций из гита проекта дописываются в локальный `.git/info/exclude` проекта (только
недостающие пути — фактическое игнорирование проверяется через `git check-ignore`). Отслеживаемый
`.gitignore` проекта скрипт не трогает: репозиторий проекта не должен знать про инфраструктуру
агентов. Плата — exclude не коммитится, после переклона каталога скрипт запускают снова.
Только stdlib.
"""

import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

PROJECTS = {"client": "Client", "server": "Server"}
ITEMS = ("CLAUDE.md", "AGENTS.md", ".claude", ".deepseek")

IGNORE_HEADER = ("# инструкции — симлинки на WF-папку вне контейнера "
                 "(блок дописан tools/link_workspaces.py)")


def git_dir(project_dir):
    """Возвращает каталог `.git` проекта (учитывает worktree/submodule, где `.git` — файл)."""
    dot = project_dir / ".git"
    if dot.is_dir():
        return dot
    if dot.is_file():
        text = dot.read_text(encoding="utf-8").strip()
        if text.startswith("gitdir:"):
            return (project_dir / text.split(":", 1)[1].strip()).resolve()
    return None


def is_ignored(project_dir, item):
    """Спрашивает у самого гита, игнорируется ли путь — с учётом всех источников исключений."""
    try:
        result = subprocess.run(["git", "-C", str(project_dir), "check-ignore", "-q", item],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return False
    return result.returncode == 0


def ensure_excluded(project_dir):
    """Дописывает в `.git/info/exclude` только те пути инструкций, которые гит пока не игнорирует.

    Файл не коммитится: проект не знает про инфраструктуру агентов, а исключения живут только
    в этой копии рабочего каталога — после переклона скрипт запускают снова (см. README).
    """
    info = git_dir(project_dir)
    if info is None:
        print("пропуск исключений (не git-репозиторий): %s" % project_dir)
        return
    missing = [item for item in ITEMS if not is_ignored(project_dir, item)]
    if not missing:
        print("исключения уже действуют: %s" % project_dir)
        return
    target = info / "info" / "exclude"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = target.read_text(encoding="utf-8") if target.is_file() else ""
    block = "\n".join([IGNORE_HEADER] + [entry(item) for item in missing])
    updated = (text.rstrip("\n") + "\n\n" + block + "\n") if text.strip() else block + "\n"
    target.write_text(updated, encoding="utf-8")
    print("исключения записаны (%s): %s" % (", ".join(missing), target))


def entry(item):
    """Правило exclude для пути: корень проекта, чтобы не глушить одноимённые файлы подкаталогов."""
    return "/" + item


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workdir", required=True, help="папка с рабочими каталогами client/ и server/")
    parser.add_argument("--wf", default=None, help="корень WF-папки (по умолчанию — два уровня выше скрипта)")
    parser.add_argument("--container-root", default="/wf", help="точка монтирования WF-папки в контейнере")
    args = parser.parse_args(argv)

    wf = Path(args.wf).expanduser().resolve() if args.wf else Path(__file__).resolve().parent.parent
    workdir = Path(args.workdir).expanduser().resolve()
    container_root = Path(args.container_root)
    backup_root = workdir / ".wf-backup" / ("repo-files-%s" % datetime.date.today().isoformat())

    failed = 0
    for project, wf_name in PROJECTS.items():
        project_dir, source_dir = workdir / project, wf / wf_name
        if not project_dir.is_dir() or not source_dir.is_dir():
            print("пропуск: %s или %s нет" % (project_dir, source_dir))
            continue
        backup_dir = backup_root / project
        backup_dir.mkdir(parents=True, exist_ok=True)
        for item in ITEMS:
            source = source_dir / item
            link = project_dir / item
            expected = container_root / wf_name / item
            if not source.exists():
                print("нет источника: %s" % source)
                failed += 1
                continue
            if link.is_symlink():
                if Path(os.readlink(link)) == expected:
                    print("уже ссылка: %s" % link)
                    continue
                link.unlink()
            elif link.is_file():
                shutil.copy2(link, backup_dir / item)
                link.unlink()
                print("в бэкап: %s" % (backup_dir / item))
            elif link.is_dir():
                print("ПРОПУСК (каталог, не ссылка): %s" % link)
                failed += 1
                continue
            link.symlink_to(container_root / wf_name / item)
            print("ссылка: %s -> %s" % (link, os.readlink(link)))

        ensure_excluded(project_dir)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
