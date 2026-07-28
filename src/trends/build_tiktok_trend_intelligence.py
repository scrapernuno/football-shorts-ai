from __future__ import annotations

import hashlib
import json
import re

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from trends.build_trend_discovery_request import (
    build_and_write_discovery_request,
)
from trends.discover_tiktok_trends import (
    discover_and_write,
)


ROOT = Path(__file__).resolve().parents[2]

CONTENT_PATH = (
    ROOT
    /
    "output"
    /
    "content_package.json"
)

INTAKE_PATH = (
    ROOT
    /
    "config"
    /
    "tiktok_trend_intake.json"
)

RUNTIME_INTAKE_PATH = (
    ROOT
    /
    "output"
    /
    "tiktok_trend_runtime_intake.json"
)

DISCOVERY_RESULTS_PATH = (
    ROOT
    /
    "output"
    /
    "tiktok_trend_discovery_results.json"
)

OUTPUT_PATH = (
    ROOT
    /
    "output"
    /
    "tiktok_trend_intelligence.json"
)


TREND_INTELLIGENCE_VERSION = "1.0"


VIDEO_USAGE_MODES = {
    "reference_only",
    "native_duet",
    "native_stitch",
    "licensed_ugc",
}


SOUND_RIGHTS_CLASSES = {
    "tiktok_commercial_sound",
    "tiktok_native_sound",
    "externally_licensed_music",
    "reference_only",
}


TIKTOK_HOSTS = {
    "tiktok.com",
    "www.tiktok.com",
    "m.tiktok.com",
    "vm.tiktok.com",
    "ads.tiktok.com",
}


def require_mapping(
    value: object,
    field_name: str,
) -> dict[str, Any]:

    if not isinstance(
        value,
        dict,
    ):

        raise ValueError(
            f"{field_name} deve ser "
            "um objeto JSON."
        )

    return value


def require_list(
    value: object,
    field_name: str,
) -> list[Any]:

    if not isinstance(
        value,
        list,
    ):

        raise ValueError(
            f"{field_name} deve ser "
            "uma lista JSON."
        )

    return value


def require_text(
    value: object,
    field_name: str,
) -> str:

    if not isinstance(
        value,
        str,
    ):

        raise ValueError(
            f"{field_name} deve ser texto."
        )

    normalized = value.strip()

    if not normalized:

        raise ValueError(
            f"{field_name} não pode "
            "estar vazio."
        )

    return normalized


def optional_text(
    value: object,
) -> str | None:

    if not isinstance(
        value,
        str,
    ):

        return None

    normalized = value.strip()

    return normalized or None


def load_json(
    path: Path,
) -> dict[str, Any]:

    if not path.is_file():

        raise FileNotFoundError(
            f"Ficheiro em falta: {path}"
        )

    try:

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            f"JSON inválido em {path}: {exc}"
        ) from exc

    return require_mapping(
        payload,
        str(
            path
        ),
    )


def write_json_atomically(
    path: Path,
    payload: dict[str, Any],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        path.parent
        /
        f".{path.name}.tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        +
        "\n",
        encoding="utf-8",
    )

    temporary_path.replace(
        path
    )


def canonical_sha256(
    payload: object,
) -> str:

    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def validate_https_url(
    value: object,
    field_name: str,
) -> str:

    url = require_text(
        value,
        field_name,
    )

    parsed = urlparse(
        url
    )

    if (
        parsed.scheme != "https"
        or
        not parsed.netloc
    ):

        raise ValueError(
            f"{field_name} deve ser "
            "um URL HTTPS."
        )

    return url


def validate_tiktok_url(
    value: object,
    field_name: str,
) -> str:

    url = validate_https_url(
        value,
        field_name,
    )

    parsed = urlparse(
        url
    )

    host = (
        parsed.hostname
        or
        ""
    ).lower()

    if host not in TIKTOK_HOSTS:

        raise ValueError(
            f"{field_name} não pertence "
            "ao TikTok."
        )

    return url


def normalize_identifier(
    value: object,
    field_name: str,
) -> str:

    identifier = require_text(
        value,
        field_name,
    )

    if not re.fullmatch(
        r"[A-Za-z0-9._:-]{1,120}",
        identifier,
    ):

        raise ValueError(
            f"{field_name} contém "
            "caracteres inválidos."
        )

    return identifier


def evaluate_video_candidate(
    raw_candidate: dict[str, Any],
    index: int,
) -> dict[str, Any]:

    prefix = (
        "video_candidates"
        f"[{index}]"
    )

    candidate_id = normalize_identifier(
        raw_candidate.get(
            "candidate_id"
        ),
        f"{prefix}.candidate_id",
    )

    source_url = validate_tiktok_url(
        raw_candidate.get(
            "source_url"
        ),
        f"{prefix}.source_url",
    )

    creator_username = require_text(
        raw_candidate.get(
            "creator_username"
        ),
        f"{prefix}.creator_username",
    )

    caption = require_text(
        raw_candidate.get(
            "caption"
        ),
        f"{prefix}.caption",
    )

    usage_mode = require_text(
        raw_candidate.get(
            "intended_usage_mode"
        ),
        f"{prefix}.intended_usage_mode",
    ).lower()

    if usage_mode not in VIDEO_USAGE_MODES:

        raise ValueError(
            f"{prefix}.intended_usage_mode "
            "não é suportado."
        )

    reuse = require_mapping(
        raw_candidate.get(
            "reuse_availability",
            {},
        ),
        f"{prefix}.reuse_availability",
    )

    duet_enabled = (
        reuse.get(
            "duet_enabled"
        )
        is True
    )

    stitch_enabled = (
        reuse.get(
            "stitch_enabled"
        )
        is True
    )

    embed_allowed = (
        reuse.get(
            "embed_allowed"
        )
        is True
    )

    creator_license_status = (
        optional_text(
            raw_candidate.get(
                "creator_license_status"
            )
        )
        or
        "none"
    ).lower()

    creator_license_reference = (
        optional_text(
            raw_candidate.get(
                "creator_license_reference"
            )
        )
    )

    original_file_received = (
        raw_candidate.get(
            "original_file_received"
        )
        is True
    )

    original_file_reference = (
        optional_text(
            raw_candidate.get(
                "original_file_reference"
            )
        )
    )

    music_review_status = (
        optional_text(
            raw_candidate.get(
                "music_review_status"
            )
        )
        or
        "pending"
    ).lower()

    cross_platform_requested = (
        raw_candidate.get(
            "cross_platform_requested"
        )
        is True
    )

    reasons: list[str] = []

    native_ready = False

    licensed_ugc_ready = False

    rights_status = "reference_only"

    execution_status = "reference_only"

    tiktok_allowed = False

    cross_platform_allowed = False

    if usage_mode == "reference_only":

        execution_status = "reference_only"

        rights_status = "reference_only"

    elif usage_mode == "native_duet":

        tiktok_allowed = duet_enabled

        native_ready = duet_enabled

        execution_status = (
            "native_action_required"
            if duet_enabled
            else
            "blocked"
        )

        rights_status = (
            "platform_native_only"
            if duet_enabled
            else
            "blocked"
        )

        if not duet_enabled:

            reasons.append(
                "Dueto não confirmado como "
                "disponível no vídeo."
            )

    elif usage_mode == "native_stitch":

        tiktok_allowed = stitch_enabled

        native_ready = stitch_enabled

        execution_status = (
            "native_action_required"
            if stitch_enabled
            else
            "blocked"
        )

        rights_status = (
            "platform_native_only"
            if stitch_enabled
            else
            "blocked"
        )

        if not stitch_enabled:

            reasons.append(
                "Costura não confirmada como "
                "disponível no vídeo."
            )

    elif usage_mode == "licensed_ugc":

        license_approved = (
            creator_license_status
            ==
            "approved"
            and
            creator_license_reference
            is not None
        )

        original_ready = (
            original_file_received
            and
            original_file_reference
            is not None
        )

        music_ready = (
            music_review_status
            in {
                "approved",
                "not_applicable",
            }
        )

        licensed_ugc_ready = (
            license_approved
            and
            original_ready
            and
            music_ready
        )

        tiktok_allowed = (
            licensed_ugc_ready
        )

        cross_platform_allowed = (
            licensed_ugc_ready
            and
            cross_platform_requested
        )

        execution_status = (
            "licensed_asset_ready"
            if licensed_ugc_ready
            else
            "blocked"
        )

        rights_status = (
            "licensed"
            if licensed_ugc_ready
            else
            "license_evidence_required"
        )

        if not license_approved:

            reasons.append(
                "Licença do creator não aprovada "
                "ou sem referência."
            )

        if not original_ready:

            reasons.append(
                "Ficheiro original do creator "
                "não foi recebido."
            )

        if not music_ready:

            reasons.append(
                "Direitos de música/áudio "
                "não foram aprovados."
            )

    return {
        "candidate_id":
            candidate_id,

        "source_url":
            source_url,

        "creator_username":
            creator_username,

        "caption":
            caption,

        "observed_at":
            optional_text(
                raw_candidate.get(
                    "observed_at"
                )
            ),

        "trend_status":
            (
                optional_text(
                    raw_candidate.get(
                        "trend_status"
                    )
                )
                or
                "unclassified"
            ),

        "metrics":
            (
                raw_candidate.get(
                    "metrics"
                )
                if isinstance(
                    raw_candidate.get(
                        "metrics"
                    ),
                    dict,
                )
                else
                {}
            ),

        "usage_mode":
            usage_mode,

        "reuse_availability":
            {
                "duet_enabled":
                    duet_enabled,

                "stitch_enabled":
                    stitch_enabled,

                "embed_allowed":
                    embed_allowed,
            },

        "creator_license_status":
            creator_license_status,

        "creator_license_reference":
            creator_license_reference,

        "original_file_received":
            original_file_received,

        "original_file_reference":
            original_file_reference,

        "music_review_status":
            music_review_status,

        "native_ready":
            native_ready,

        "licensed_ugc_ready":
            licensed_ugc_ready,

        "tiktok_allowed":
            tiktok_allowed,

        "cross_platform_allowed":
            cross_platform_allowed,

        "rights_status":
            rights_status,

        "execution_status":
            execution_status,

        "blocking_reasons":
            reasons,

        "third_party_download_allowed":
            False,

        "watermark_removal_allowed":
            False,
    }


def evaluate_sound_candidate(
    raw_candidate: dict[str, Any],
    index: int,
    region: str,
) -> dict[str, Any]:

    prefix = (
        "sound_candidates"
        f"[{index}]"
    )

    sound_id = normalize_identifier(
        raw_candidate.get(
            "sound_id"
        ),
        f"{prefix}.sound_id",
    )

    sound_name = require_text(
        raw_candidate.get(
            "sound_name"
        ),
        f"{prefix}.sound_name",
    )

    source_url = validate_tiktok_url(
        raw_candidate.get(
            "source_url"
        ),
        f"{prefix}.source_url",
    )

    rights_classification = require_text(
        raw_candidate.get(
            "rights_classification"
        ),
        (
            f"{prefix}."
            "rights_classification"
        ),
    ).lower()

    if (
        rights_classification
        not in
        SOUND_RIGHTS_CLASSES
    ):

        raise ValueError(
            f"{prefix}.rights_classification "
            "não é suportado."
        )

    candidate_region = (
        optional_text(
            raw_candidate.get(
                "region"
            )
        )
        or
        region
    )

    commercial_library_confirmed = (
        raw_candidate.get(
            "commercial_library_confirmed"
        )
        is True
    )

    external_license_reference = (
        optional_text(
            raw_candidate.get(
                "external_license_reference"
            )
        )
    )

    allowed_platforms = (
        raw_candidate.get(
            "allowed_platforms"
        )
        if isinstance(
            raw_candidate.get(
                "allowed_platforms"
            ),
            list,
        )
        else
        []
    )

    allowed_platforms = [
        require_text(
            platform,
            (
                f"{prefix}."
                "allowed_platforms[]"
            ),
        ).lower()
        for platform in allowed_platforms
    ]

    status = "reference_only"

    tiktok_allowed = False

    cross_platform_allowed = False

    legal_review_required = False

    blocking_reasons: list[str] = []

    if (
        rights_classification
        ==
        "tiktok_commercial_sound"
    ):

        tiktok_allowed = (
            commercial_library_confirmed
            and
            candidate_region
            ==
            region
        )

        status = (
            "platform_native_ready"
            if tiktok_allowed
            else
            "blocked"
        )

        if not commercial_library_confirmed:

            blocking_reasons.append(
                "Som não confirmado na "
                "Commercial Music Library."
            )

        if candidate_region != region:

            blocking_reasons.append(
                "Território do som não corresponde "
                "ao território da publicação."
            )

    elif (
        rights_classification
        ==
        "tiktok_native_sound"
    ):

        status = "legal_review_required"

        legal_review_required = True

        blocking_reasons.append(
            "Som nativo geral não está "
            "pré-liberado para uso comercial."
        )

    elif (
        rights_classification
        ==
        "externally_licensed_music"
    ):

        licensed = (
            external_license_reference
            is not None
            and
            bool(
                allowed_platforms
            )
        )

        tiktok_allowed = (
            licensed
            and
            "tiktok"
            in
            allowed_platforms
        )

        cross_platform_allowed = (
            licensed
            and
            any(
                platform
                in
                allowed_platforms
                for platform in (
                    "instagram",
                    "youtube",
                )
            )
        )

        status = (
            "licensed"
            if licensed
            else
            "blocked"
        )

        if not licensed:

            blocking_reasons.append(
                "Licença externa ou plataformas "
                "permitidas em falta."
            )

    return {
        "sound_id":
            sound_id,

        "sound_name":
            sound_name,

        "source_url":
            source_url,

        "trend_status":
            (
                optional_text(
                    raw_candidate.get(
                        "trend_status"
                    )
                )
                or
                "unclassified"
            ),

        "rights_classification":
            rights_classification,

        "region":
            candidate_region,

        "commercial_library_confirmed":
            commercial_library_confirmed,

        "external_license_reference":
            external_license_reference,

        "allowed_platforms":
            allowed_platforms,

        "status":
            status,

        "tiktok_allowed":
            tiktok_allowed,

        "cross_platform_allowed":
            cross_platform_allowed,

        "legal_review_required":
            legal_review_required,

        "master_embedded":
            False,

        "blocking_reasons":
            blocking_reasons,
    }


def build_intelligence(
    content: dict[str, Any],
    intake: dict[str, Any],
    discovery_request: dict[str, Any],
) -> dict[str, Any]:

    source_topic = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    title = require_text(
        source_topic.get(
            "title"
        ),
        "content.source_topic.title",
    )

    hook = require_text(
        source_topic.get(
            "hook"
        ),
        "content.source_topic.hook",
    )

    generated_at = require_text(
        content.get(
            "generated_at"
        ),
        "content.generated_at",
    )

    content_identity = canonical_sha256(
        {
            "title":
                title,

            "hook":
                hook,

            "generated_at":
                generated_at,
        }
    )

    region = require_text(
        intake.get(
            "region"
        ),
        "intake.region",
    ).upper()

    request_binding = require_mapping(
        discovery_request.get(
            "topic_binding"
        ),
        "discovery_request.topic_binding",
    )

    if request_binding.get(
        "content_title"
    ) != title:

        raise ValueError(
            "Discovery request não corresponde "
            "ao título vencedor."
        )

    if request_binding.get(
        "content_hook"
    ) != hook:

        raise ValueError(
            "Discovery request não corresponde "
            "ao hook vencedor."
        )

    if request_binding.get(
        "content_generated_at"
    ) != generated_at:

        raise ValueError(
            "Discovery request não corresponde "
            "à geração do Content Package."
        )

    if request_binding.get(
        "content_identity_sha256"
    ) != content_identity:

        raise ValueError(
            "Discovery request contém identidade "
            "de conteúdo inválida."
        )

    if discovery_request.get(
        "region"
    ) != region:

        raise ValueError(
            "Discovery request contém região "
            "diferente do intake."
        )

    raw_video_candidates = require_list(
        intake.get(
            "video_candidates"
        ),
        "intake.video_candidates",
    )

    raw_sound_candidates = require_list(
        intake.get(
            "sound_candidates"
        ),
        "intake.sound_candidates",
    )

    selected_video_id = optional_text(
        intake.get(
            "selected_video_candidate_id"
        )
    )

    selected_sound_id = optional_text(
        intake.get(
            "selected_sound_candidate_id"
        )
    )

    intake_binding = require_mapping(
        intake.get(
            "topic_binding"
        ),
        "intake.topic_binding",
    )

    intake_title = optional_text(
        intake_binding.get(
            "content_title"
        )
    )

    intake_identity = optional_text(
        intake_binding.get(
            "content_identity_sha256"
        )
    )

    if (
        intake_title is None
    ) != (
        intake_identity is None
    ):

        raise ValueError(
            "Topic binding do intake está "
            "parcialmente preenchido."
        )

    intake_has_candidate_material = bool(
        raw_video_candidates
        or
        raw_sound_candidates
        or
        selected_video_id
        or
        selected_sound_id
    )

    if (
        intake_has_candidate_material
        and
        intake_title is None
    ):

        raise ValueError(
            "Intake com candidatos exige binding "
            "à notícia vencedora atual."
        )

    if (
        intake_title is not None
        and
        intake_title != title
    ):

        raise ValueError(
            "Intake pertence a outra notícia."
        )

    if (
        intake_identity is not None
        and
        intake_identity != content_identity
    ):

        raise ValueError(
            "Intake pertence a outra identidade "
            "de conteúdo."
        )

    video_candidates = [
        evaluate_video_candidate(
            require_mapping(
                raw_candidate,
                (
                    "video_candidates"
                    f"[{index}]"
                ),
            ),
            index,
        )
        for index, raw_candidate
        in enumerate(
            raw_video_candidates
        )
    ]

    sound_candidates = [
        evaluate_sound_candidate(
            require_mapping(
                raw_candidate,
                (
                    "sound_candidates"
                    f"[{index}]"
                ),
            ),
            index,
            region,
        )
        for index, raw_candidate
        in enumerate(
            raw_sound_candidates
        )
    ]

    video_ids = [
        candidate[
            "candidate_id"
        ]
        for candidate in video_candidates
    ]

    sound_ids = [
        candidate[
            "sound_id"
        ]
        for candidate in sound_candidates
    ]

    if len(
        video_ids
    ) != len(
        set(
            video_ids
        )
    ):

        raise ValueError(
            "candidate_id de vídeo duplicado."
        )

    if len(
        sound_ids
    ) != len(
        set(
            sound_ids
        )
    ):

        raise ValueError(
            "sound_id duplicado."
        )

    selected_video = next(
        (
            candidate
            for candidate in video_candidates
            if candidate[
                "candidate_id"
            ]
            ==
            selected_video_id
        ),
        None,
    )

    selected_sound = next(
        (
            candidate
            for candidate in sound_candidates
            if candidate[
                "sound_id"
            ]
            ==
            selected_sound_id
        ),
        None,
    )

    if (
        selected_video_id is not None
        and
        selected_video is None
    ):

        raise ValueError(
            "Vídeo selecionado não existe."
        )

    if (
        selected_sound_id is not None
        and
        selected_sound is None
    ):

        raise ValueError(
            "Som selecionado não existe."
        )

    video_ready = (
        selected_video is not None
        and
        (
            selected_video[
                "native_ready"
            ]
            or
            selected_video[
                "licensed_ugc_ready"
            ]
        )
    )

    sound_ready = (
        selected_sound is None
        or
        selected_sound[
            "tiktok_allowed"
        ]
    )

    tiktok_variant_ready = (
        video_ready
        and
        sound_ready
    )

    cross_platform_ugc_ready = (
        selected_video is not None
        and
        selected_video[
            "licensed_ugc_ready"
        ]
        and
        selected_video[
            "cross_platform_allowed"
        ]
    )

    status = (
        "ready_for_manual_native_execution"
        if tiktok_variant_ready
        else
        (
            "review_required"
            if video_candidates
            or
            sound_candidates
            else
            "intake_required"
        )
    )

    return {
        "trend_intelligence_version":
            TREND_INTELLIGENCE_VERSION,

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "source_mode":
            (
                "automatic_topic_binding_with_"
                "governed_web_discovery_and_manual_evidence_overlay"
            ),

        "region":
            region,

        "content":
            {
                "title":
                    title,

                "hook":
                    hook,

                "identity_sha256":
                    content_identity,
            },

        "discovery_request":
            {
                "status":
                    discovery_request.get(
                        "status"
                    ),

                "content_identity_sha256":
                    request_binding.get(
                        "content_identity_sha256"
                    ),

                "search_queries":
                    require_list(
                        discovery_request.get(
                            "search_queries"
                        ),
                        (
                            "discovery_request."
                            "search_queries"
                        ),
                    ),

                "candidate_intake_path":
                    require_mapping(
                        discovery_request.get(
                            "candidate_intake"
                        ),
                        (
                            "discovery_request."
                            "candidate_intake"
                        ),
                    ).get(
                        "path"
                    ),
            },

        "official_capability_boundaries":
            {
                "creative_center_used_for_manual_discovery":
                    True,

                "server_side_web_search_enabled":
                    True,

                "browser_api_calls_enabled":
                    False,

                "direct_tiktok_api_calls_enabled":
                    False,

                "oembed_reference_supported":
                    True,

                "display_api_global_trend_search_available":
                    False,

                "display_api_requires_user_authorization":
                    True,

                "native_duet_or_stitch_platform_bound":
                    True,

                "third_party_download_allowed":
                    False,

                "watermark_removal_allowed":
                    False,
            },

        "video_candidates":
            video_candidates,

        "sound_candidates":
            sound_candidates,

        "selected_video":
            selected_video,

        "selected_sound":
            selected_sound,

        "readiness":
            {
                "video_ready":
                    video_ready,

                "sound_ready":
                    sound_ready,

                "tiktok_variant_ready":
                    tiktok_variant_ready,

                "cross_platform_ugc_ready":
                    cross_platform_ugc_ready,
            },

        "status":
            status,

        "publication_execution_enabled":
            False,
    }


def validate_intelligence(
    payload: dict[str, Any],
) -> None:

    boundaries = require_mapping(
        payload.get(
            "official_capability_boundaries"
        ),
        (
            "intelligence."
            "official_capability_boundaries"
        ),
    )

    if boundaries.get(
        "third_party_download_allowed"
    ) is not False:

        raise ValueError(
            "Download de TikTok de terceiro "
            "deve permanecer bloqueado."
        )

    if boundaries.get(
        "watermark_removal_allowed"
    ) is not False:

        raise ValueError(
            "Remoção de watermark deve "
            "permanecer bloqueada."
        )

    if boundaries.get(
        "display_api_global_trend_search_available"
    ) is not False:

        raise ValueError(
            "Não pode ser declarada pesquisa "
            "global de trends pela Display API."
        )

    if boundaries.get(
        "server_side_web_search_enabled"
    ) is not True:

        raise ValueError(
            "Web search server-side não foi ativada."
        )

    for field_name in (
        "browser_api_calls_enabled",
        "direct_tiktok_api_calls_enabled",
    ):

        if boundaries.get(field_name) is not False:

            raise ValueError(
                f"{field_name} deve permanecer false."
            )

    if payload.get(
        "publication_execution_enabled"
    ) is not False:

        raise ValueError(
            "Publicação deve permanecer "
            "desativada."
        )

    discovery_request = require_mapping(
        payload.get(
            "discovery_request"
        ),
        "intelligence.discovery_request",
    )

    content = require_mapping(
        payload.get(
            "content"
        ),
        "intelligence.content",
    )

    if discovery_request.get(
        "status"
    ) != "discovery_required":

        raise ValueError(
            "Estado do discovery request inválido."
        )

    if discovery_request.get(
        "content_identity_sha256"
    ) != content.get(
        "identity_sha256"
    ):

        raise ValueError(
            "Intelligence não está ligada ao "
            "discovery request atual."
        )

    selected_video = payload.get(
        "selected_video"
    )

    if isinstance(
        selected_video,
        dict,
    ):

        if selected_video.get(
            "usage_mode"
        ) in {
            "native_duet",
            "native_stitch",
        }:

            if selected_video.get(
                "cross_platform_allowed"
            ) is not False:

                raise ValueError(
                    "Remix nativo não pode ser "
                    "exportado para outra plataforma."
                )

        if selected_video.get(
            "watermark_removal_allowed"
        ) is not False:

            raise ValueError(
                "Candidate permitiu remoção "
                "de watermark."
            )

    selected_sound = payload.get(
        "selected_sound"
    )

    if isinstance(
        selected_sound,
        dict,
    ):

        if selected_sound.get(
            "master_embedded"
        ) is not False:

            raise ValueError(
                "Música específica de plataforma "
                "não pode ser embebida no master."
            )


def main() -> int:

    print(
        "="
        *
        70
    )

    print(
        "FOOTBALL-SHORTS-AI-0031C.4D"
    )

    print(
        "TIKTOK TREND INTELLIGENCE"
    )

    print(
        "NATIVE REMIX AND MUSIC GOVERNANCE"
    )

    print(
        "SERVER-SIDE WEB SEARCH - NO DOWNLOAD"
    )

    print(
        "NO PUBLICATION EXECUTION"
    )

    print(
        "="
        *
        70
    )

    discovery_results = discover_and_write()

    content = load_json(
        CONTENT_PATH
    )

    intake = load_json(
        RUNTIME_INTAKE_PATH
    )

    discovery_request = (
        build_and_write_discovery_request(
            content,
            intake,
        )
    )

    intelligence = build_intelligence(
        content,
        intake,
        discovery_request,
    )

    discovery_binding = require_mapping(
        discovery_results.get(
            "topic_binding"
        ),
        "discovery_results.topic_binding",
    )

    if discovery_binding.get(
        "content_identity_sha256"
    ) != intelligence[
        "content"
    ][
        "identity_sha256"
    ]:

        raise ValueError(
            "Resultados de discovery pertencem "
            "a outra notícia."
        )

    intelligence[
        "discovery_execution"
    ] = {
        "provider":
            require_mapping(
                discovery_results.get(
                    "provider"
                ),
                "discovery_results.provider",
            ).get(
                "provider_id"
            ),

        "status":
            require_mapping(
                discovery_results.get(
                    "execution"
                ),
                "discovery_results.execution",
            ).get(
                "status"
            ),

        "result_identity_sha256":
            discovery_results.get(
                "result_identity_sha256"
            ),

        "video_reference_count":
            len(
                require_list(
                    discovery_results.get(
                        "video_candidates"
                    ),
                    (
                        "discovery_results."
                        "video_candidates"
                    ),
                )
            ),

        "sound_reference_count":
            len(
                require_list(
                    discovery_results.get(
                        "sound_candidates"
                    ),
                    (
                        "discovery_results."
                        "sound_candidates"
                    ),
                )
            ),
    }

    intelligence[
        "discovered_hashtags"
    ] = require_list(
        discovery_results.get(
            "hashtags"
        ),
        "discovery_results.hashtags",
    )

    validate_intelligence(
        intelligence
    )

    write_json_atomically(
        OUTPUT_PATH,
        intelligence,
    )

    print(
        "TREND_DISCOVERY_REQUEST=PASS"
    )

    print(
        "TOPIC_BINDING=AUTOMATIC"
    )

    print(
        "GOVERNED_WEB_DISCOVERY=PASS"
    )

    print(
        "TIKTOK_TREND_INTELLIGENCE=PASS"
    )

    print(
        "VIDEO_CANDIDATE_COUNT="
        f"{len(intelligence['video_candidates'])}"
    )

    print(
        "SOUND_CANDIDATE_COUNT="
        f"{len(intelligence['sound_candidates'])}"
    )

    print(
        "STATUS="
        f"{intelligence['status'].upper()}"
    )

    print(
        "THIRD_PARTY_DOWNLOAD_ALLOWED=NO"
    )

    print(
        "WATERMARK_REMOVAL_ALLOWED=NO"
    )

    print(
        "PUBLICATION_EXECUTION_ENABLED=NO"
    )

    print(
        "="
        *
        70
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
