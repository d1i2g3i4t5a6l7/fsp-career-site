"""Выгрузка банка задач из работающего workspace в папку tasks/.

Сгенерированные задачи живут в БД. Выгруженные в tasks/ попадают в репозиторий и загружаются при старте
на любой машине, в том числе у эксперта с чистой базой. При каждом старте задача из папки перезаписывает
свою копию в БД — снять задачу с выдачи надёжнее, удалив её папку. Задачи, у которых папка уже есть,
не трогаются (ручные заглушки остаются в своём формате); --update перезаписывает и их.

    python scripts/export_tasks.py                      # опубликованные задачи с http://localhost:8010
    python scripts/export_tasks.py --status review --url http://localhost:8010

Только стандартная библиотека: запускается без виртуального окружения.
"""

import argparse
import json
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"


def get(url: str):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def existing_folders(out: Path) -> dict[str, Path]:
    """id задачи → папка: задачи-заглушки лежат в папках с другими именами, их не дублируем."""
    folders = {}
    for meta in out.glob("*/task.json"):
        folders[json.loads(meta.read_text(encoding="utf-8"))["id"]] = meta.parent
    return folders


def write_files(folder: Path, files: dict[str, str]) -> None:
    shutil.rmtree(folder, ignore_errors=True)  # файлы, которых больше нет в задаче, не должны остаться
    for path, content in files.items():
        target = (folder / path).resolve()
        if not target.is_relative_to(folder.resolve()):
            raise ValueError(f"Недопустимый путь в задаче: {path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8010")
    parser.add_argument("--status", default="published", choices=["published", "review", "rejected"])
    parser.add_argument("--out", type=Path, default=TASKS_DIR)
    parser.add_argument("--update", action="store_true", help="перезаписать и задачи, которые уже есть в папке")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    folders = existing_folders(args.out)
    exported = 0
    for brief in get(f"{base}/tasks?status={args.status}"):
        if brief["id"] in folders and not args.update:
            print(f"{brief['id']}: уже в {folders[brief['id']]}")
            continue
        task = get(f"{base}/tasks/{urllib.parse.quote(brief['id'])}")
        folder = folders.get(task["id"], args.out / task["id"])
        folder.mkdir(parents=True, exist_ok=True)
        write_files(folder / "files", task.pop("files"))
        write_files(folder / "reference", task.pop("reference_files"))
        (folder / "task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{task['id']} → {folder}")
        exported += 1
    print(f"Выгружено задач: {exported}")


if __name__ == "__main__":
    main()
