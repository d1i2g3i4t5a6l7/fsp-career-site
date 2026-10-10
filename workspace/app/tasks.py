import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import TaskRow

# Грейды и направления — как на сайте (frontend/public/data.js: GRADES, SPECS)
Grade = Literal["intern", "junior", "middle", "senior"]
GRADE_ORDER: dict[str, int] = {"intern": 1, "junior": 2, "middle": 3, "senior": 4}
SPECIALIZATIONS: dict[str, str] = {
    "backend": "Backend",
    "frontend": "Frontend",
    "mobile": "Mobile",
    "data": "Data / ML",
    "devops": "DevOps",
    "qa": "QA",
    "security": "Инф. безопасность",
}
TaskType = Literal["bug", "design", "feature"]


def normalize_category(value: str) -> str:
    """Направление по id или названию с сайта («data», «Data / ML») → название. Неизвестное — ошибка."""
    key = value.strip().lower()
    for spec_id, label in SPECIALIZATIONS.items():
        if key in (spec_id, label.lower()):
            return label
    raise ValueError(f"неизвестное направление «{value.strip()}», есть: {', '.join(SPECIALIZATIONS.values())}")

# Файл запуска тестов кладёт платформа, а не автор задачи: тесты — unittest в test_*.py.
TEST_RUNNER_PATH = "run_tests.py"
TEST_RUNNER = """import sys
import unittest

suite = unittest.defaultTestLoader.discover(".", pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
if result.testsRun == 0:
    print("Не найдено ни одного теста: нужны файлы test_*.py в корне или в папках с __init__.py", file=sys.stderr)
    sys.exit(1)
sys.exit(0 if result.wasSuccessful() else 1)
"""


def is_test_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.startswith("test_") and name.endswith(".py")


class RunSpec(BaseModel):
    """Как запускать тесты задачи в песочнице."""

    language: str = "python"
    version: str = "*"
    entrypoint: str = TEST_RUNNER_PATH


class Criterion(BaseModel):
    id: str = Field(description="Латиницей в kebab-case, например handles-duplicates")
    text: str = Field(description="Что должно быть в решении или в ходе работы — проверяемо по материалам")
    points: int = Field(ge=1, le=10)
    partial_points: int | None = Field(default=None, ge=0, description="Баллы за «частично»; null — только «да» или «нет»")
    kind: Literal["solution", "process"] = Field(
        default="solution", description="solution — про итоговое решение; process — про работу с ИИ по журналу сессии"
    )
    # Объективное не отдаём LLM: на живом GigaChat один прогон судьи «не увидел» прошедшие тесты
    check: Literal["judge", "tests", "verified"] = Field(
        default="judge",
        description="judge — оценивает судья; tests — засчитывается платформой сама, если автотесты на итоговой версии проходят; "
        "verified — засчитывается платформой по журналу, если кандидат проверял работу ассистента: отклонил его правку, "
        "поправил принятую вручную или запустил тесты после неё",
    )


class GradeThreshold(BaseModel):
    grade: Grade
    # Тест на этот грейд пройден, если итог не ниже порога (баллы из 100) и все обязательные критерии — «да»
    min_score: int = Field(ge=0, le=100, description="Порог в баллах из 100")
    required: list[str] = Field(default_factory=list, description="id критериев, без которых грейд не засчитывается")


class Rubric(BaseModel):
    criteria: list[Criterion] = Field(min_length=1)
    # По порогу на каждый грейд задачи; если грейд один — это порог приёма задачи
    thresholds: list[GradeThreshold] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> "Rubric":
        ids = [c.id for c in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("id критериев должны быть уникальны")
        for c in self.criteria:
            if c.partial_points is not None and c.partial_points > c.points:
                raise ValueError(f"{c.id}: за «частично» не может быть больше, чем за «да»")
        grades = [t.grade for t in self.thresholds]
        if len(grades) != len(set(grades)):
            raise ValueError("на каждый грейд — один порог")
        for t in self.thresholds:
            unknown = set(t.required) - set(ids)
            if unknown:
                raise ValueError(f"порог {t.grade}: нет таких критериев {sorted(unknown)}")
        ordered = sorted(self.thresholds, key=lambda t: GRADE_ORDER[t.grade])
        for lower, higher in zip(ordered, ordered[1:]):
            if higher.min_score < lower.min_score:
                raise ValueError(f"порог {higher.grade} ниже порога {lower.grade}")
        return self

    @property
    def max_points(self) -> int:
        return sum(c.points for c in self.criteria)

    def threshold(self, grade: str) -> GradeThreshold | None:
        return next((t for t in self.thresholds if t.grade == grade), None)


TaskStatus = Literal["review", "published", "rejected"]


class TaskReview(BaseModel):
    """Решение эксперта о задаче: решаема ли она человеком в отведённое время."""

    expert: str
    approved: bool
    comment: str = ""
    at: str


class Task(BaseModel):
    id: str  # он же номер варианта, который видит кандидат
    # review — сгенерирована, ждёт эксперта; published — выдаётся кандидатам; rejected — эксперт отклонил.
    # Задачи-заглушки из папки tasks/ сразу published.
    status: TaskStatus = "published"
    review: TaskReview | None = None
    title: str
    type: TaskType
    # Категории и грейды, которые задаче присвоены: тест на категорию и грейд выдаёт подходящую задачу
    categories: list[str] = Field(min_length=1)
    grades: list[Grade] = Field(min_length=1)
    time_limit_min: int = Field(ge=5, le=180)
    statement: str
    # «Что оценивается» — показывается кандидату рядом с условием
    assessed: list[str] = Field(default_factory=list)
    # Стартовые файлы кандидата
    files: dict[str, str] = Field(default_factory=dict)
    # Эталон: файлы, которые меняет или добавляет решение. Кандидату не показывается.
    reference_files: dict[str, str] = Field(default_factory=dict)
    run: RunSpec | None = None
    # Критерии приёмки и пороги по грейдам. Кандидату во время решения не показываются.
    rubric: Rubric

    @field_validator("categories")
    @classmethod
    def _clean_categories(cls, value: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(normalize_category(c) for c in value if c.strip()))
        if not cleaned:
            raise ValueError("нужна хотя бы одна категория")
        return cleaned

    @model_validator(mode="after")
    def _thresholds_match_grades(self) -> "Task":
        if len(set(self.grades)) != len(self.grades):
            raise ValueError("грейды не должны повторяться")
        if {t.grade for t in self.rubric.thresholds} != set(self.grades):
            raise ValueError(f"пороги должны быть ровно на грейды задачи: {self.grades}")
        if self.run is None and any(c.check == "tests" for c in self.rubric.criteria):
            raise ValueError("критерий с check=tests есть, а автотестов в задаче нет")
        return self

    def has_category(self, category: str) -> bool:
        return category.strip().lower() in {c.lower() for c in self.categories}

    def with_original_tests(self, files: dict[str, str]) -> dict[str, str]:
        """Решение кандидата, но с исходными тестами задачи: «починить» тест вместо кода не выйдет.
        Тесты, которые кандидат добавил в новых файлах, остаются."""
        if self.run is None:
            return dict(files)
        original = {p: c for p, c in self.files.items() if is_test_file(p) or p == self.run.entrypoint}
        return {**files, **original}


class TaskView(BaseModel):
    """То, что кандидат видит о задаче: без файлов (они живут в попытке), рубрики и эталона."""

    id: str
    status: str
    title: str
    type: str
    categories: list[str]
    grades: list[str]
    time_limit_min: int
    statement: str
    assessed: list[str]
    has_tests: bool


def task_view(task: Task) -> TaskView:
    return TaskView(**task.model_dump(include=set(TaskView.model_fields) - {"has_tests"}), has_tests=task.run is not None)


async def load_tasks_from_dir(directory: Path, sessions: async_sessionmaker) -> int:
    """Задачи-заглушки: папка с task.json и подпапками files/ и reference/. Сгенерированные задачи пишутся сразу в БД."""
    count = 0
    async with sessions() as s:
        for meta in sorted(directory.glob("*/task.json")):
            data = json.loads(meta.read_text(encoding="utf-8"))
            for key, sub in (("files", "files"), ("reference_files", "reference")):
                folder = meta.parent / sub
                if folder.is_dir():
                    data[key] = {
                        p.relative_to(folder).as_posix(): p.read_text(encoding="utf-8")
                        for p in sorted(folder.rglob("*"))
                        if p.is_file()
                    }
            task = Task.model_validate(data)
            await s.merge(TaskRow(id=task.id, data=task.model_dump()))
            count += 1
        await s.commit()
    return count
