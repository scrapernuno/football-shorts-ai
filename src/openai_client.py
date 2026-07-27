from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import openai
from openai import OpenAI


LOGGER = logging.getLogger("football_shorts.openai")

DEFAULT_MODEL = "gpt-5.5"
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_OUTPUT_TOKENS = 7_000


DIGEST_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "generated_at",
        "language",
        "topics",
    ],
    "properties": {
        "generated_at": {
            "type": "string",
            "description": (
                "Data e hora de geração em formato ISO 8601."
            ),
        },
        "language": {
            "type": "string",
            "enum": ["pt-PT"],
        },
        "topics": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "title",
                    "hook",
                    "script",
                    "thumbnail",
                    "hashtags",
                    "viral_score",
                    "urgency",
                    "reason",
                    "source_title",
                    "source_name",
                    "source_url",
                ],
                "properties": {
                    "title": {
                        "type": "string",
                        "minLength": 5,
                        "maxLength": 120,
                    },
                    "hook": {
                        "type": "string",
                        "minLength": 5,
                        "maxLength": 180,
                    },
                    "script": {
                        "type": "string",
                        "minLength": 120,
                        "maxLength": 1_500,
                    },
                    "thumbnail": {
                        "type": "string",
                        "minLength": 2,
                        "maxLength": 60,
                    },
                    "hashtags": {
                        "type": "array",
                        "minItems": 5,
                        "maxItems": 8,
                        "items": {
                            "type": "string",
                            "minLength": 2,
                            "maxLength": 40,
                        },
                    },
                    "viral_score": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "urgency": {
                        "type": "string",
                        "enum": [
                            "LOW",
                            "MEDIUM",
                            "HIGH",
                        ],
                    },
                    "reason": {
                        "type": "string",
                        "minLength": 10,
                        "maxLength": 500,
                    },
                    "source_title": {
                        "type": "string",
                        "minLength": 3,
                        "maxLength": 300,
                    },
                    "source_name": {
                        "type": "string",
                        "minLength": 2,
                        "maxLength": 100,
                    },
                    "source_url": {
                        "type": "string",
                        "minLength": 8,
                        "maxLength": 2_000,
                    },
                },
            },
        },
    },
}


class OpenAIClientError(RuntimeError):
    """Erro base da integração OpenAI."""


class OpenAIConfigurationError(OpenAIClientError):
    """Configuração local inválida ou incompleta."""


class OpenAIResponseError(OpenAIClientError):
    """Resposta vazia, incompleta ou inválida."""


@dataclass(frozen=True)
class OpenAIClientSettings:
    api_key: str
    model: str = DEFAULT_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS

    @classmethod
    def from_environment(cls) -> "OpenAIClientSettings":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()

        if not api_key:
            raise OpenAIConfigurationError(
                "A variável OPENAI_API_KEY não está definida."
            )

        model = (
            os.environ.get("OPENAI_MODEL", DEFAULT_MODEL).strip()
            or DEFAULT_MODEL
        )

        timeout_seconds = _read_float_environment(
            "OPENAI_TIMEOUT_SECONDS",
            DEFAULT_TIMEOUT_SECONDS,
            minimum=10.0,
        )

        max_retries = _read_int_environment(
            "OPENAI_MAX_RETRIES",
            DEFAULT_MAX_RETRIES,
            minimum=0,
            maximum=10,
        )

        max_output_tokens = _read_int_environment(
            "OPENAI_MAX_OUTPUT_TOKENS",
            DEFAULT_MAX_OUTPUT_TOKENS,
            minimum=1_000,
            maximum=30_000,
        )

        return cls(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            max_output_tokens=max_output_tokens,
        )


def _read_int_environment(
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = os.environ.get(name, "").strip()

    if not raw_value:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise OpenAIConfigurationError(
            f"{name} tem de ser um número inteiro."
        ) from exc

    if not minimum <= value <= maximum:
        raise OpenAIConfigurationError(
            f"{name} tem de estar entre {minimum} e {maximum}."
        )

    return value


def _read_float_environment(
    name: str,
    default: float,
    *,
    minimum: float,
) -> float:
    raw_value = os.environ.get(name, "").strip()

    if not raw_value:
        return default

    try:
        value = float(raw_value)
    except ValueError as exc:
        raise OpenAIConfigurationError(
            f"{name} tem de ser um número."
        ) from exc

    if value < minimum:
        raise OpenAIConfigurationError(
            f"{name} tem de ser igual ou superior a {minimum}."
        )

    return value


def create_client(
    settings: OpenAIClientSettings,
) -> OpenAI:
    return OpenAI(
        api_key=settings.api_key,
        timeout=settings.timeout_seconds,
        max_retries=0,
    )


def _calculate_retry_delay(attempt: int) -> float:
    return min(2 ** attempt, 20.0)


def _validate_digest_payload(
    payload: object,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise OpenAIResponseError(
            "A resposta JSON não contém um objeto na raiz."
        )

    generated_at = payload.get("generated_at")
    language = payload.get("language")
    topics = payload.get("topics")

    if not isinstance(generated_at, str) or not generated_at.strip():
        raise OpenAIResponseError(
            "O campo generated_at está ausente ou é inválido."
        )

    if language != "pt-PT":
        raise OpenAIResponseError(
            "O campo language tem de ser pt-PT."
        )

    if not isinstance(topics, list) or len(topics) != 5:
        raise OpenAIResponseError(
            "A resposta tem de incluir exatamente cinco temas."
        )

    required_topic_fields = {
        "title",
        "hook",
        "script",
        "thumbnail",
        "hashtags",
        "viral_score",
        "urgency",
        "reason",
        "source_title",
        "source_name",
        "source_url",
    }

    for index, topic in enumerate(topics, start=1):
        if not isinstance(topic, dict):
            raise OpenAIResponseError(
                f"O tema {index} não é um objeto JSON."
            )

        missing_fields = required_topic_fields - topic.keys()

        if missing_fields:
            raise OpenAIResponseError(
                f"O tema {index} não contém os campos: "
                f"{sorted(missing_fields)}"
            )

        viral_score = topic.get("viral_score")

        if (
            not isinstance(viral_score, int)
            or isinstance(viral_score, bool)
            or not 0 <= viral_score <= 100
        ):
            raise OpenAIResponseError(
                f"O viral_score do tema {index} é inválido."
            )

        if topic.get("urgency") not in {
            "LOW",
            "MEDIUM",
            "HIGH",
        }:
            raise OpenAIResponseError(
                f"A urgência do tema {index} é inválida."
            )

        hashtags = topic.get("hashtags")

        if not isinstance(hashtags, list):
            raise OpenAIResponseError(
                f"As hashtags do tema {index} são inválidas."
            )

        if not 5 <= len(hashtags) <= 8:
            raise OpenAIResponseError(
                f"O tema {index} deve conter entre 5 e 8 hashtags."
            )

    return payload


def _parse_response_json(response_text: str) -> dict[str, Any]:
    clean_text = response_text.strip()

    if not clean_text:
        raise OpenAIResponseError(
            "A OpenAI devolveu uma resposta vazia."
        )

    try:
        payload = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        raise OpenAIResponseError(
            "A OpenAI não devolveu JSON válido. "
            f"Erro na linha {exc.lineno}, coluna {exc.colno}."
        ) from exc

    return _validate_digest_payload(payload)


def generate_json(
    *,
    system_prompt: str,
    user_prompt: str,
    settings: OpenAIClientSettings | None = None,
) -> dict[str, Any]:
    if not system_prompt.strip():
        raise ValueError("system_prompt não pode estar vazio.")

    if not user_prompt.strip():
        raise ValueError("user_prompt não pode estar vazio.")

    resolved_settings = (
        settings
        if settings is not None
        else OpenAIClientSettings.from_environment()
    )

    client = create_client(resolved_settings)

    total_attempts = resolved_settings.max_retries + 1

    for attempt in range(total_attempts):
        current_attempt = attempt + 1

        try:
            LOGGER.info(
                "A chamar a OpenAI: model=%s, tentativa=%s/%s",
                resolved_settings.model,
                current_attempt,
                total_attempts,
            )

            response = client.responses.create(
                model=resolved_settings.model,
                instructions=system_prompt,
                input=user_prompt,
                max_output_tokens=(
                    resolved_settings.max_output_tokens
                ),
                reasoning={
                    "effort": "low",
                },
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "football_shorts_digest",
                        "description": (
                            "Briefing diário estruturado com cinco "
                            "ideias de YouTube Shorts de futebol."
                        ),
                        "strict": True,
                        "schema": DIGEST_JSON_SCHEMA,
                    }
                },
            )

            request_id = getattr(
                response,
                "_request_id",
                "indisponível",
            )

            LOGGER.info(
                "Resposta recebida: request_id=%s, status=%s",
                request_id,
                getattr(response, "status", "desconhecido"),
            )

            if getattr(response, "status", None) == "incomplete":
                incomplete_details = getattr(
                    response,
                    "incomplete_details",
                    None,
                )

                raise OpenAIResponseError(
                    "A resposta da OpenAI ficou incompleta. "
                    f"Detalhes: {incomplete_details}"
                )

            if getattr(response, "status", None) == "failed":
                error = getattr(response, "error", None)

                raise OpenAIResponseError(
                    "A geração falhou na OpenAI. "
                    f"Detalhes: {error}"
                )

            output_text = getattr(response, "output_text", "")

            return _parse_response_json(output_text)

        except openai.AuthenticationError as exc:
            raise OpenAIConfigurationError(
                "A OPENAI_API_KEY foi recusada. "
                "Confirme o segredo configurado no GitHub."
            ) from exc

        except openai.PermissionDeniedError as exc:
            raise OpenAIConfigurationError(
                "A conta ou projeto não tem permissão para usar "
                f"o modelo {resolved_settings.model}."
            ) from exc

        except openai.NotFoundError as exc:
            raise OpenAIConfigurationError(
                f"O modelo {resolved_settings.model} não foi encontrado "
                "ou não está disponível para este projeto."
            ) from exc

        except openai.BadRequestError as exc:
            request_id = getattr(exc, "request_id", None)

            raise OpenAIResponseError(
                "O pedido enviado à OpenAI foi rejeitado. "
                f"request_id={request_id or 'indisponível'}; "
                f"erro={exc}"
            ) from exc

        except openai.RateLimitError as exc:
            if current_attempt >= total_attempts:
                raise OpenAIClientError(
                    "O limite de utilização da OpenAI foi atingido "
                    "e todas as tentativas falharam."
                ) from exc

            delay = _calculate_retry_delay(attempt)

            LOGGER.warning(
                "Rate limit. Nova tentativa dentro de %.1f segundos.",
                delay,
            )

            time.sleep(delay)

        except (
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.InternalServerError,
        ) as exc:
            if current_attempt >= total_attempts:
                raise OpenAIClientError(
                    "A comunicação com a OpenAI falhou depois de "
                    f"{total_attempts} tentativa(s)."
                ) from exc

            delay = _calculate_retry_delay(attempt)

            LOGGER.warning(
                "Erro temporário da OpenAI. "
                "Nova tentativa dentro de %.1f segundos.",
                delay,
            )

            time.sleep(delay)

        except openai.APIStatusError as exc:
            request_id = getattr(exc, "request_id", None)

            if current_attempt >= total_attempts:
                raise OpenAIClientError(
                    "A OpenAI devolveu um erro HTTP. "
                    f"status={exc.status_code}; "
                    f"request_id={request_id or 'indisponível'}"
                ) from exc

            delay = _calculate_retry_delay(attempt)

            LOGGER.warning(
                "Erro HTTP temporário: status=%s, request_id=%s. "
                "Nova tentativa dentro de %.1f segundos.",
                exc.status_code,
                request_id or "indisponível",
                delay,
            )

            time.sleep(delay)

    raise OpenAIClientError(
        "A geração terminou sem resposta e sem erro identificado."
    )


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )
