"""Model client for OpenAI and Azure OpenAI Chat Completions. Standard library only (urllib), so the app keeps the hub's
zero-dependency rule. All parameters come from qcc.settings; nothing is hard-coded here.

The client is the ONLY place in the app that opens an outbound network connection, and only when ai.enabled is true and a key exists.
"""
import json
import time
import urllib.error
import urllib.request


class ModelError(Exception):
    def __init__(self, code, message, status=None):
        Exception.__init__(self, message)
        self.code, self.message, self.status = code, message, status


class ChatClient(object):
    def __init__(self, settings):
        self.s = settings

    def _request(self):
        prov = self.s.provider()
        key, _ = self.s.api_key()
        if not key:
            raise ModelError("E-AI-NO-KEY", "No API key configured (set OPENAI_API_KEY or config/settings.local.json).")
        if prov == "openai":
            c = self.s.get("ai.openai")
            url = c["base_url"].rstrip("/") + "/chat/completions"
            headers = {"Authorization": "Bearer " + key}
            if c.get("organization"):
                headers["OpenAI-Organization"] = c["organization"]
            if c.get("project"):
                headers["OpenAI-Project"] = c["project"]
            model = c["model"]
        elif prov == "azure_openai":
            c = self.s.get("ai.azure_openai")
            url = "%s/openai/deployments/%s/chat/completions?api-version=%s" % (c["endpoint"].rstrip("/"), c["deployment"], c["api_version"])
            headers = {"api-key": key}
            model = c["deployment"]
        else:
            raise ModelError("E-AI-PROVIDER", "Unknown ai.provider: %s" % prov)
        headers["Content-Type"] = "application/json"
        return url, headers, model

    def chat(self, messages):
        """Returns {"text", "model", "usage", "latency_ms"}. Raises ModelError."""
        url, headers, model = self._request()
        g = self.s.get("ai.generation", {})
        body = {"model": model, "messages": messages}
        if g.get("temperature") is not None:
            body["temperature"] = g["temperature"]
        if g.get("max_output_tokens"):
            body[g.get("token_param") or "max_completion_tokens"] = int(g["max_output_tokens"])
        data = json.dumps(body).encode("utf-8")
        retries = int(g.get("max_retries", 1))
        last = None
        for attempt in range(retries + 1):
            t0 = time.time()
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=float(g.get("timeout_seconds", 30))) as resp:
                    out = json.loads(resp.read().decode("utf-8"))
                text = out["choices"][0]["message"].get("content") or ""
                return {"text": text, "model": out.get("model", model), "usage": out.get("usage", {}),
                        "latency_ms": int((time.time() - t0) * 1000)}
            except urllib.error.HTTPError as e:
                detail = ""
                try:
                    detail = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
                except Exception:
                    pass
                last = ModelError("E-AI-HTTP-%d" % e.code, detail or str(e), e.code)
                # a model that refuses 'temperature' or the token parameter: drop optional params once and retry
                if e.code == 400 and ("temperature" in detail or "max_tokens" in detail or "max_completion_tokens" in detail):
                    body.pop("temperature", None)
                    for k in ("max_tokens", "max_completion_tokens"):
                        body.pop(k, None)
                    data = json.dumps(body).encode("utf-8")
                    continue
                if e.code not in (429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = ModelError("E-AI-NETWORK", str(getattr(e, "reason", e)))
            time.sleep(min(2 ** attempt, 4))
        raise last
