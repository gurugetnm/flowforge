"""Action nodes: nodes that do something with the data flowing through."""

import asyncio
import json
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, field_validator

from app.config import get_settings
from app.core.url_guard import BlockedURLError, URLPolicy, assert_url_allowed
from app.nodes.base import (
    Control,
    NodeCategory,
    NodeContext,
    NodeExecutionError,
    NodeExecutor,
    NodeResult,
    Option,
)
from app.nodes.fields import config_field, describe
from app.nodes.registry import register

HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
MAX_TIMEOUT_SECONDS = 60
MAX_REDIRECTS = 3
#: Response bodies larger than this are truncated rather than stored in full.
MAX_RESPONSE_BYTES = 256 * 1024
MAX_DELAY_SECONDS = 60

LOG_LEVELS = ("debug", "info", "warning", "error")


class LogConfig(BaseModel):
    message: str = config_field(
        label="Message",
        control=Control.TEXTAREA,
        default="",
        help_text="Supports expressions, for example: Created user {{ input.id }}.",
        supports_expressions=True,
    )
    level: Literal["debug", "info", "warning", "error"] = config_field(
        label="Level",
        control=Control.SELECT,
        default="info",
        options=tuple(Option(level, level.title()) for level in LOG_LEVELS),
    )


@register
class LogExecutor(NodeExecutor[LogConfig]):
    """Records a message in the run log."""

    node_type = "log"
    name = "Log"
    category = NodeCategory.ACTION
    description = "Writes a message into the execution log."
    config_model = LogConfig
    fields = describe(LogConfig)

    async def execute(self, config: LogConfig, context: NodeContext) -> NodeResult:
        message = str(context.render(config.message))
        context.log(f"[{config.level}] {message}")
        # The input is passed through so a Log node can sit mid-flow.
        return NodeResult.of({**context.input, "message": message})


class DelayConfig(BaseModel):
    seconds: float = config_field(
        label="Delay (seconds)",
        control=Control.NUMBER,
        default=1.0,
        help_text=f"How long to pause before continuing. At most {MAX_DELAY_SECONDS} seconds.",
        ge=0,
        le=MAX_DELAY_SECONDS,
    )


@register
class DelayExecutor(NodeExecutor[DelayConfig]):
    """Pauses the run for a fixed time."""

    node_type = "delay"
    name = "Delay"
    category = NodeCategory.ACTION
    description = "Waits before continuing to the next node."
    config_model = DelayConfig
    fields = describe(DelayConfig)

    async def execute(self, config: DelayConfig, context: NodeContext) -> NodeResult:
        await asyncio.sleep(config.seconds)
        context.log(f"Waited {config.seconds:g}s")
        return NodeResult.of(dict(context.input))


class HttpRequestConfig(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = config_field(
        label="Method",
        control=Control.SELECT,
        default="GET",
        options=tuple(Option(method, method) for method in HTTP_METHODS),
    )
    url: str = config_field(
        label="URL",
        control=Control.TEXT,
        help_text="Must be an http or https URL. Supports expressions.",
        placeholder="https://api.example.com/users/{{ input.id }}",
        supports_expressions=True,
        min_length=1,
    )
    headers: dict[str, str] = config_field(
        label="Headers",
        control=Control.KEY_VALUE,
        default_factory=dict,
        help_text="Values support expressions.",
        supports_expressions=True,
    )
    query: dict[str, str] = config_field(
        label="Query parameters",
        control=Control.KEY_VALUE,
        default_factory=dict,
        supports_expressions=True,
    )
    body: str = config_field(
        label="Request body",
        control=Control.JSON,
        default="",
        help_text="Sent as JSON. Leave empty for no body.",
        supports_expressions=True,
        depends_on="method",
        depends_on_values=("POST", "PUT", "PATCH", "DELETE"),
    )
    timeout_seconds: float = config_field(
        label="Timeout (seconds)",
        control=Control.NUMBER,
        default=10.0,
        gt=0,
        le=MAX_TIMEOUT_SECONDS,
    )

    @field_validator("url")
    @classmethod
    def _looks_like_a_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required.")
        # A URL built from an expression cannot be checked until run time.
        if "{{" in cleaned:
            return cleaned
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("The URL must start with http:// or https://.")
        return cleaned

    @field_validator("body")
    @classmethod
    def _body_must_be_json(cls, value: str) -> str:
        if not value.strip() or "{{" in value:
            return value
        try:
            json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"This is not valid JSON ({error.msg} at line {error.lineno})."
            ) from None
        return value


def _current_policy() -> URLPolicy:
    settings = get_settings()
    return URLPolicy(
        allow_private_networks=settings.http_allow_private_networks,
        allowed_hosts=frozenset(settings.http_allowed_host_list),
    )


@register
class HttpRequestExecutor(NodeExecutor[HttpRequestConfig]):
    """Calls an external HTTP API."""

    node_type = "http_request"
    name = "HTTP Request"
    category = NodeCategory.ACTION
    description = "Calls an HTTP API and makes the response available downstream."
    config_model = HttpRequestConfig
    fields = describe(HttpRequestConfig)

    async def execute(self, config: HttpRequestConfig, context: NodeContext) -> NodeResult:
        url = str(context.render(config.url))
        headers = {str(k): str(v) for k, v in context.render(config.headers).items()}
        params = {str(k): str(v) for k, v in context.render(config.query).items()}
        content = self._build_body(config, context)
        policy = _current_policy()

        try:
            response = await self._send(config, url, headers, params, content, policy)
        except BlockedURLError as error:
            raise NodeExecutionError(str(error)) from error
        except httpx.TimeoutException as error:
            raise NodeExecutionError(
                f"The request timed out after {config.timeout_seconds:g}s."
            ) from error
        except httpx.HTTPError as error:
            raise NodeExecutionError(f"The request failed: {type(error).__name__}.") from error

        body, truncated = self._read_body(response)
        context.log(f"{config.method} {_redact(url)} responded {response.status_code}")

        if response.status_code >= 400:
            raise NodeExecutionError(
                f"The request failed with status {response.status_code}.",
                details={"status_code": response.status_code, "body": body},
            )

        return NodeResult.of(
            {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": body,
                "truncated": truncated,
            }
        )

    async def _send(
        self,
        config: HttpRequestConfig,
        url: str,
        headers: dict[str, str],
        params: dict[str, str],
        content: str | None,
        policy: URLPolicy,
    ) -> httpx.Response:
        """Send the request, checking the policy on every redirect hop.

        Redirects are followed by hand because a permitted public host can
        redirect to a private address, which an automatic follow would obey.
        """
        # `follow_redirects` stays off so each hop can be re-checked.
        async with httpx.AsyncClient(
            timeout=config.timeout_seconds, follow_redirects=False
        ) as client:
            request_url = url
            for hop in range(MAX_REDIRECTS + 1):
                assert_url_allowed(request_url, policy)
                response = await client.request(
                    config.method,
                    request_url,
                    headers=headers,
                    params=params if hop == 0 else None,
                    content=content if hop == 0 else None,
                )
                if not response.is_redirect or response.next_request is None:
                    return response
                request_url = str(response.next_request.url)

        raise NodeExecutionError(f"The request exceeded {MAX_REDIRECTS} redirects.")

    def _build_body(self, config: HttpRequestConfig, context: NodeContext) -> str | None:
        if config.method == "GET" or not config.body.strip():
            return None
        rendered = context.render(config.body)
        if isinstance(rendered, str):
            return rendered
        return json.dumps(rendered)

    def _read_body(self, response: httpx.Response) -> tuple[Any, bool]:
        """Return the parsed body, truncating anything oversized."""
        raw = response.content[: MAX_RESPONSE_BYTES + 1]
        truncated = len(raw) > MAX_RESPONSE_BYTES
        raw = raw[:MAX_RESPONSE_BYTES]

        if not truncated and response.headers.get("content-type", "").startswith(
            ("application/json", "application/problem+json")
        ):
            try:
                return response.json(), False
            except ValueError:
                pass

        return raw.decode("utf-8", errors="replace"), truncated


REDACTED = "***"
SENSITIVE_QUERY_KEYS = frozenset({"token", "access_token", "api_key", "apikey", "key", "secret"})


def _redact(url: str) -> str:
    """Strip credentials and secret-looking query values before logging a URL."""
    parts = urlsplit(url)
    netloc = parts.hostname or ""
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    if parts.username:
        netloc = f"{REDACTED}@{netloc}"

    query = urlencode(
        [
            (key, REDACTED if key.lower() in SENSITIVE_QUERY_KEYS else value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ],
        safe="*",
    )
    return urlunsplit((parts.scheme, netloc, parts.path, query, ""))
