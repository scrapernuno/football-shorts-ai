from __future__ import annotations

import re
from dataclasses import replace
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from knowledge.contracts import ExternalKnowledgePackage, KnowledgeFact, KnowledgeSource


_WHITESPACE = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^\w]+", flags=re.UNICODE)
_TRACKING_QUERY_PREFIXES = ("utm_",)
_TRACKING_QUERY_KEYS = {"gclid", "fbclid", "mc_cid", "mc_eid"}


def _normalized_text(value: str) -> str:
    collapsed = _WHITESPACE.sub(" ", str(value).strip()).casefold()
    return _NON_WORD.sub(" ", collapsed).strip()


def canonical_source_key(source: KnowledgeSource) -> str:
    """Return a deterministic identity key without performing network access."""

    if source.url:
        parsed = urlsplit(source.url.strip())
        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.casefold() not in _TRACKING_QUERY_KEYS
            and not key.casefold().startswith(_TRACKING_QUERY_PREFIXES)
        ]
        normalized_url = urlunsplit(
            (
                parsed.scheme.casefold(),
                parsed.netloc.casefold(),
                parsed.path.rstrip("/") or "/",
                urlencode(sorted(filtered_query)),
                "",
            )
        )
        return f"url:{normalized_url}"

    return "metadata:" + "|".join(
        (
            _normalized_text(source.provider),
            _normalized_text(source.title),
            source.source_type,
        )
    )


def canonical_fact_key(fact: KnowledgeFact) -> str:
    """Return a conservative exact-semantic key for one governed claim."""

    return _normalized_text(fact.claim)


def deduplicate_package(package: ExternalKnowledgePackage) -> ExternalKnowledgePackage:
    """Deduplicate sources and claims while preserving all evidence references.

    The first occurrence is canonical because orchestration input is already ordered by
    provider priority. Duplicate facts are merged by unioning their canonical source IDs.
    """

    canonical_sources: list[KnowledgeSource] = []
    source_key_to_id: dict[str, str] = {}
    source_id_map: dict[str, str] = {}

    for source in package.sources:
        key = canonical_source_key(source)
        canonical_id = source_key_to_id.get(key)
        if canonical_id is None:
            canonical_id = source.source_id
            source_key_to_id[key] = canonical_id
            canonical_sources.append(source)
        source_id_map[source.source_id] = canonical_id

    canonical_facts: list[KnowledgeFact] = []
    fact_key_to_index: dict[str, int] = {}

    for fact in package.facts:
        canonical_source_ids = tuple(
            dict.fromkeys(source_id_map[source_id] for source_id in fact.source_ids)
        )
        normalized_fact = replace(fact, source_ids=canonical_source_ids)
        key = canonical_fact_key(normalized_fact)
        existing_index = fact_key_to_index.get(key)
        if existing_index is None:
            fact_key_to_index[key] = len(canonical_facts)
            canonical_facts.append(normalized_fact)
            continue

        existing = canonical_facts[existing_index]
        merged_source_ids = tuple(
            dict.fromkeys((*existing.source_ids, *normalized_fact.source_ids))
        )
        canonical_facts[existing_index] = replace(
            existing,
            source_ids=merged_source_ids,
            verification_status=_strongest_status(
                existing.verification_status,
                normalized_fact.verification_status,
            ),
        )

    return ExternalKnowledgePackage(
        topic=package.topic,
        sources=tuple(canonical_sources),
        facts=tuple(canonical_facts),
        provider_mode=package.provider_mode,
    )


def _strongest_status(*statuses: str) -> str:
    ranking = {
        "unsupported": 0,
        "partially_supported": 1,
        "supported": 2,
    }
    return max(statuses, key=lambda status: ranking[status])
