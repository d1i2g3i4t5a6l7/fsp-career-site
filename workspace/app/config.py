from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./workspace.db"
    # Относительный путь считается от папки сервиса
    tasks_dir: str = "tasks"
    cors_origins: list[str] = ["*"]

    # stub — заглушка без сети, live — реальные каналы из настроек ниже
    llm_mode: Literal["stub", "live"] = "stub"
    # Сценарий → канал. Если канал не настроен (нет ключа или адреса), сценарий уходит в llm_fallback.
    route_assistant: str = "gigachat"
    route_grader: str = "gigachat"
    route_task_gen: str = "gigachat"
    llm_fallback: str = "gigachat"
    llm_timeout_s: float = 120.0
    llm_max_retries: int = 3

    # API Сбера (GigaChat). Ключ авторизации меняется на токен на 30 минут.
    gigachat_auth_key: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_auth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    # Единый адрес с 16.07.2026; клиентам, подключённым раньше, доступен и старый gigachat.devices.sberbank.ru/api/v1
    gigachat_base_url: str = "https://api.giga.chat/v1"
    # GigaChat-3-Ultra в API Сбера есть только у физлиц на freemium
    gigachat_model: str = "GigaChat-3-Ultra"
    # Цепочка НУЦ Минцифры уже лежит в certs/ и подключается всегда; сюда — только дополнительный PEM,
    # например если Минцифры перевыпустит Sub CA раньше, чем обновим файл в репозитории.
    gigachat_ca_bundle: str = ""
    gigachat_verify_ssl: bool = True
    # У физлица API Сбера держит один поток, у юрлица — 10.
    gigachat_max_concurrency: int = 1

    # cloud.ru Evolution Foundation Models, OpenAI-совместимый API.
    # Точные id моделей — GET /v1/models, например ai-sage/GigaChat3.5-432B-A28B-Reasoning (3.5 Ultra)
    # или ai-sage/GigaChat3-10B-A1.8B (размер Lightning).
    cloudru_base_url: str = "https://foundation-models.api.cloud.ru/v1"
    cloudru_api_key: str = ""
    cloudru_model: str = ""
    cloudru_max_concurrency: int = 4

    # GigaChat 3.1 Lightning на своём сервере: vLLM, llama-server или Ollama — любой OpenAI-совместимый адрес
    lightning_base_url: str = ""
    lightning_api_key: str = ""
    lightning_model: str = ""
    lightning_max_concurrency: int = 2

    # local — запуск кода прямо на машине, только для разработки; piston — песочница без сети по API Piston:
    # наш контейнер runner (docker compose) или сам Piston
    sandbox: Literal["local", "piston"] = "local"
    # http://host:port или unix:/путь/к/сокету — так runner без сети слушает общий том
    piston_url: str = "http://localhost:2000"
    sandbox_timeout_s: float = 20.0
    # Пакеты, установленные в песочнице сверх стандартной библиотеки (например, ["numpy", "pandas"]).
    # Попадают в промпт генерации задач: модель пишет код только на них.
    sandbox_packages: list[str] = []

    # Сколько раз модель может исправить черновик задачи после проваленных проверок
    task_gen_fix_attempts: int = 3

    # Страховка от зацикливания модели на инструментах в одном ответе, а не ограничение кандидата:
    # число сообщений ассистенту не ограничено. 25 шагов хватает на сложный запрос
    # (прочитать несколько файлов, несколько правок, тесты).
    assistant_max_steps: int = 25

    # Сколько независимых прогонов судьи на одну попытку; итог по критерию — большинство.
    # 1 — дешевле по токенам, но оценка менее устойчива.
    grader_runs: int = 3
    # Как часто фоновый сторож закрывает попытки с вышедшим временем и запускает проверку
    grading_poll_s: float = 5.0

    # Грейд можно менять раз в 3 месяца
    grade_change_cooldown_days: int = 90
    # Повтор теста на тот же уровень после непройденного; уровень ниже доступен сразу
    same_level_retry_days: int = 30
    # Попытку аннулировал человек (например, из-за ухода со вкладки) — тесты кандидата заморожены
    annul_freeze_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
