#!/usr/bin/env python3
"""Учёт просканированных файлов кода: .claude/docs/source-scan-coverage.md.

Запуск:
  scan_coverage.py <repo>                                  — пересчитать итог
  scan_coverage.py <repo> --mark P [P ...] --by WHO --doc DOC — отметить файлы и пересчитать
  scan_coverage.py <repo> --seed                           — разово отметить файлы из карт файлов доков
P — путь от корня репозитория, уникальный хвост пути (`plain/user/UserBag.ts`) или папка (все файлы в ней).
Правила ведения — в шапке самого source-scan-coverage.md.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

MARKS_START, MARKS_END = "<!-- marks:start -->", "<!-- marks:end -->"
GEN_START, GEN_END = "<!-- generated:start -->", "<!-- generated:end -->"
HIST_START, HIST_END = "<!-- history:start -->", "<!-- history:end -->"
MARKS_HEADER = "| Файл | Документ | Кто отметил | Дата |\n|---|---|---|---|"
SEED_BY = "первичное заполнение"


def is_server(root):
    return (root / "pom.xml").exists()


def code_files(root):
    if is_server(root):
        files = root.glob("*/src/main/java/**/*.java")
    else:
        files = (p for p in (root / "src").rglob("*.ts") if not p.relative_to(root).as_posix().startswith("src/ee/"))
    return sorted(p.relative_to(root).as_posix() for p in files)


def group_of(rel, server):
    parts = rel.split("/")
    if server:
        module = parts[0]
        try:
            i = parts.index("linkedgames") + 2
        except ValueError:
            i = 4
        rest = parts[i:-1]
        return f"{module}: " + ("/".join(rest[:2]) or "(корень)")
    rest = parts[1:-1]
    return "/".join(rest[:2]) or "(корень src)"


def resolve(token, files, server, allow_bare_name):
    token = token.strip().strip("`").rstrip("/").split(":")[0].split("#")[0].strip()
    token = re.sub(r"\(.*$", "", token).strip()
    token = re.sub(r"^(…|\.\.\.|\.)/", "", token)
    if not token:
        return []
    if not server and not token.startswith("src/") and token in {f[4:] for f in files}:
        token = "src/" + token
    if token in files:
        return [token]
    under = [f for f in files if f.startswith(token + "/")]
    if under and "/" in token:
        return under
    if "/" in token:
        tail = [f for f in files if f.endswith("/" + token)]
        if len(tail) == 1:
            return tail
        return [] if tail else [f for f in files if ("/" + token + "/") in f]
    if allow_bare_name:
        ext = ".java" if server else ".ts"
        name = token if token.endswith((".ts", ".java")) else token + ext
        same = [f for f in files if f.rsplit("/", 1)[-1] == name]
        if len(same) == 1:
            return same
    return []


def split_doc(text):
    def section(start, end):
        a, b = text.index(start), text.index(end)
        return text[a + len(start):b]
    return section(MARKS_START, MARKS_END), section(HIST_START, HIST_END)


def parse_marks(block):
    marks = {}
    for line in block.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] in ("Файл", "---") or set(cells[0]) <= {"-"}:
            continue
        marks[cells[0].strip("`")] = {"doc": cells[1], "by": cells[2], "date": cells[3]}
    return marks


def render_marks(marks):
    rows = [f"| `{p}` | {m['doc']} | {m['by']} | {m['date']} |" for p, m in sorted(marks.items())]
    return "\n" + MARKS_HEADER + ("\n" + "\n".join(rows) if rows else "") + "\n"


def seed(root, files, server):
    docs_dir = root / ".claude" / "docs"
    found = {}
    for doc in sorted(docs_dir.glob("*-architecture.md")):
        lines = doc.read_text(encoding="utf-8").splitlines()
        inside = False
        for line in lines:
            low = line.lower()
            if "прямого влияния" in low and (line.startswith("#") or line.startswith("**")):
                inside = True
                continue
            if inside and ("косвенного влияния" in low and (line.startswith("#") or line.startswith("**"))
                           or re.match(r"^#{1,2} ", line)):
                inside = False
            if not inside:
                continue
            for token in re.findall(r"`([^`]+)`", line):
                for piece in re.split(r"[,\s]+", token):
                    for f in resolve(piece, files, server, allow_bare_name=True):
                        found.setdefault(f, doc.name)
    return found


def update_history(block, today, scanned, total, pct):
    lines = [l for l in block.strip().splitlines() if l.strip() and not l.startswith(f"- {today} ")]
    lines.append(f"- {today} — {pct:.1f}% ({scanned}/{total})")
    return "\n" + "\n".join(lines) + "\n"


def render_generated(files, marks, server, today):
    scanned = [f for f in files if f in marks]
    total, done = len(files), len(scanned)
    pct = 100.0 * done / total if total else 0.0
    groups = {}
    for f in files:
        groups.setdefault(group_of(f, server), []).append(f)
    out = [f"\n## Итог {{#total}}\n\nПересчитано {today}: просканировано **{done} из {total}** файлов кода — **{pct:.1f}%**.\n",
           "## По папкам {#by-folder}\n\nСортировка — от наименее покрытых.\n\n| Папка | Файлов | Просканировано | % |\n|---|---|---|---|"]
    stats = []
    for g, fs in groups.items():
        s = sum(1 for f in fs if f in marks)
        stats.append((100.0 * s / len(fs), g, len(fs), s))
    for p, g, n, s in sorted(stats):
        out.append(f"| {g} | {n} | {s} | {p:.0f}% |")
    out.append("\n## Непросканированные файлы {#unscanned}\n")
    for p, g, n, s in sorted(stats):
        rest = [f for f in groups[g] if f not in marks]
        if rest:
            out.append(f"### {g} ({len(rest)})\n")
            out.extend(f"- `{f}`" for f in rest)
            out.append("")
    stale = sorted(set(marks) - set(files))
    out.append("## Отметки на несуществующие файлы {#stale-marks}\n")
    out.append("\n".join(f"- `{f}`" for f in stale) if stale else "Нет.")
    return "\n".join(out) + "\n", done, total, pct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--mark", nargs="+")
    ap.add_argument("--by")
    ap.add_argument("--doc")
    ap.add_argument("--seed", action="store_true")
    args = ap.parse_args()
    if args.mark and not (args.by and args.doc):
        ap.error("--mark требует --by и --doc")

    root = Path(args.repo).resolve()
    server = is_server(root)
    cov = root / ".claude" / "docs" / "source-scan-coverage.md"
    text = cov.read_text(encoding="utf-8")
    marks_block, hist_block = split_doc(text)
    marks = parse_marks(marks_block)
    files = code_files(root)
    today = datetime.date.today().isoformat()

    unresolved = []
    if args.seed:
        for f, doc in seed(root, files, server).items():
            marks.setdefault(f, {"doc": doc, "by": SEED_BY, "date": today})
    for token in args.mark or []:
        hit = resolve(token, files, server, allow_bare_name=False)
        if not hit:
            unresolved.append(token)
        for f in hit:
            marks[f] = {"doc": args.doc, "by": args.by, "date": today}

    generated, done, total, pct = render_generated(files, marks, server, today)
    text = text.replace(text[text.index(MARKS_START):text.index(MARKS_END) + len(MARKS_END)],
                        MARKS_START + render_marks(marks) + MARKS_END)
    text = text.replace(text[text.index(HIST_START):text.index(HIST_END) + len(HIST_END)],
                        HIST_START + update_history(hist_block, today, done, total, pct) + HIST_END)
    text = text.replace(text[text.index(GEN_START):text.index(GEN_END) + len(GEN_END)],
                        GEN_START + generated + GEN_END)
    cov.write_text(text, encoding="utf-8")

    print(f"{pct:.1f}% ({done}/{total})")
    if unresolved:
        print("НЕ РАСПОЗНАНО: " + ", ".join(unresolved))
        sys.exit(1)


if __name__ == "__main__":
    main()
