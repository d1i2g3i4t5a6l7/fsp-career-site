from app.config import Settings
from app.llm.balancer import ChannelLimiter
from app.llm.gateway import Channel, Gateway, Journal
from app.llm.providers.gigachat import GigaChatProvider
from app.llm.providers.openai_compat import OpenAICompatProvider
from app.llm.providers.stub import StubProvider


def build_gateway(settings: Settings, journal: Journal | None = None) -> Gateway:
    if settings.llm_mode == "stub":
        stub = Channel("stub", StubProvider(), "stub", ChannelLimiter("stub", 8))
        return Gateway({"stub": stub}, routes={}, fallback="stub", journal=journal)

    channels: dict[str, Channel] = {}
    if settings.gigachat_auth_key:
        channels["gigachat"] = Channel(
            "gigachat",
            GigaChatProvider(
                settings.gigachat_auth_key,
                scope=settings.gigachat_scope,
                auth_url=settings.gigachat_auth_url,
                base_url=settings.gigachat_base_url,
                ca_bundle=settings.gigachat_ca_bundle,
                verify_ssl=settings.gigachat_verify_ssl,
                timeout=settings.llm_timeout_s,
            ),
            settings.gigachat_model,
            ChannelLimiter("gigachat", settings.gigachat_max_concurrency),
        )
    if settings.cloudru_api_key and settings.cloudru_model:
        channels["cloudru"] = Channel(
            "cloudru",
            OpenAICompatProvider(settings.cloudru_base_url, settings.cloudru_api_key, settings.llm_timeout_s),
            settings.cloudru_model,
            ChannelLimiter("cloudru", settings.cloudru_max_concurrency),
        )
    if settings.lightning_base_url and settings.lightning_model:
        channels["lightning"] = Channel(
            "lightning",
            OpenAICompatProvider(settings.lightning_base_url, settings.lightning_api_key, settings.llm_timeout_s),
            settings.lightning_model,
            ChannelLimiter("lightning", settings.lightning_max_concurrency),
        )
    if not channels:
        raise RuntimeError("LLM_MODE=live, но не настроен ни один канал: задайте GIGACHAT_AUTH_KEY или CLOUDRU_* в .env")

    routes = {"assistant": settings.route_assistant, "grader": settings.route_grader, "task_gen": settings.route_task_gen}
    return Gateway(
        channels,
        routes,
        fallback=settings.llm_fallback,
        max_retries=settings.llm_max_retries,
        journal=journal,
    )
