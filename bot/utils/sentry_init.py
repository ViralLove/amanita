import os

def init_sentry():
    try:
        import sentry_sdk
    except ImportError:
        print("[Sentry] sentry_sdk не установлен, пропускаем инициализацию")
        return
    env = os.getenv("AMANITA_API_ENVIRONMENT", "development")
    sentry_dsn = os.getenv("SENTRY_DSN")
    sentry_enabled = os.getenv("SENTRY_ENABLED", "false").lower() == "true" and bool(sentry_dsn)
    if sentry_enabled:
        sentry_sdk.init(
            dsn=sentry_dsn,
            send_default_pii=True,
            traces_sample_rate=0.1,
            environment=env
        )
        print(f"[Sentry] Enabled for environment: {env}")
    else:
        print(f"[Sentry] Disabled for environment: {env}") 