"""Central settings: config/settings.json -> config/settings.local.json -> environment variables (highest wins).

Every tunable value (paths, port, AI provider, model, API key) is read here and nowhere else.
The API key is never logged, never sent to the browser, and only leaves this process in the Authorization header of a model call.
"""
import copy
import json
import os

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(APP_ROOT, "config")

ENV_OVERRIDES = {
    # env var             -> dotted settings path
    "QCC_HOST": "app.host",
    "QCC_PORT": "app.port",
    "QCC_OPEN_BROWSER": "app.open_browser",
    "QCC_HUB_REPO": "paths.hub_repo",
    "QCC_DATA_SOURCE": "paths.data_source",
    "QCC_AI_ENABLED": "ai.enabled",
    "QCC_AI_PROVIDER": "ai.provider",
    "QCC_OPENAI_MODEL": "ai.openai.model",
    "QCC_OPENAI_BASE_URL": "ai.openai.base_url",
    "QCC_AZURE_OPENAI_ENDPOINT": "ai.azure_openai.endpoint",
    "QCC_AZURE_OPENAI_DEPLOYMENT": "ai.azure_openai.deployment",
}


def _merge(base, extra):
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        elif not str(k).startswith("_"):
            base[k] = v
    return base


def _set(d, dotted, value):
    keys = dotted.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    old = d.get(keys[-1])
    if isinstance(old, bool):
        value = str(value).strip().lower() in ("1", "true", "yes", "on")
    elif isinstance(old, int):
        value = int(value)
    d[keys[-1]] = value


def _read(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Settings(object):
    def __init__(self, data, sources):
        self.data, self.sources = data, sources
        self._session_key = None  # optional key entered in the UI; memory only, lost on restart
        # environment keys are read once, at start-up, like every other setting
        self._env_keys = {}
        for prov in ("openai", "azure_openai"):
            name = (data.get("ai", {}).get(prov, {}) or {}).get("api_key_env")
            if name and os.environ.get(name):
                self._env_keys[name] = os.environ[name]

    # ------------------------------------------------------------------ access
    def get(self, dotted, default=None):
        cur = self.data
        for k in dotted.split("."):
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def path(self, dotted):
        """Absolute path for a settings value that is relative to the application folder."""
        p = self.get(dotted)
        return p if os.path.isabs(p) else os.path.normpath(os.path.join(APP_ROOT, p))

    # ------------------------------------------------------------------ AI key resolution
    def provider(self):
        return self.get("ai.provider", "openai")

    def api_key(self):
        """Resolution order: key set in the UI for this session -> environment variable -> settings file. Returns (key, source)."""
        if self._session_key:
            return self._session_key, "session"
        prov = self.get("ai." + self.provider(), {}) or {}
        env_name = prov.get("api_key_env")
        if env_name and self._env_keys.get(env_name):
            return self._env_keys[env_name], "env:" + env_name
        if prov.get("api_key"):
            return prov["api_key"], "settings file"
        return None, None

    def set_session_key(self, key):
        self._session_key = (key or "").strip() or None

    def ai_ready(self):
        key, _ = self.api_key()
        return bool(self.get("ai.enabled")) and bool(key)

    def public_ai_status(self):
        """Safe to send to the browser: never includes the key."""
        key, source = self.api_key()
        prov = self.provider()
        model = self.get("ai.openai.model") if prov == "openai" else self.get("ai.azure_openai.deployment")
        return {
            "enabled": bool(self.get("ai.enabled")),
            "provider": prov,
            "model": model,
            "key_configured": bool(key),
            "key_source": source,
            "key_hint": ("..." + key[-4:]) if key and len(key) > 8 else None,
            "autonomy_level": self.get("ai.guardrails.autonomy_level", "A1"),
            "mode": "model" if (self.get("ai.enabled") and key) else "retrieval-only (no model calls)",
        }


def load():
    data = _read(os.path.join(CONFIG_DIR, "settings.json"))
    data = json.loads(json.dumps(data))
    sources = ["config/settings.json"]
    local = os.path.join(CONFIG_DIR, "settings.local.json")
    if os.path.exists(local):
        _merge(data, _read(local))
        sources.append("config/settings.local.json")
    for env, dotted in ENV_OVERRIDES.items():
        if os.environ.get(env) not in (None, ""):
            _set(data, dotted, os.environ[env])
            sources.append("env:" + env)
    return Settings(copy.deepcopy(data), sources)
