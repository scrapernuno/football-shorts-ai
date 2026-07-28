"use strict";


const DATA_FILES = {
    dashboard: "data/dashboard_model.json",
    content: "data/content_package.json",
    publishing: "data/publishing_package.json",
    analytics: "data/analytics_package.json",
};


function isObject(value) {
    return (
        value !== null
        &&
        typeof value === "object"
        &&
        !Array.isArray(value)
    );
}


function firstDefined(...values) {
    for (const value of values) {
        if (
            value !== undefined
            &&
            value !== null
            &&
            value !== ""
        ) {
            return value;
        }
    }

    return null;
}


function toNumber(
    value,
    fallback = 0,
) {
    if (
        typeof value === "number"
        &&
        Number.isFinite(value)
    ) {
        return value;
    }

    if (typeof value === "string") {
        const normalized = value
            .replace("%", "")
            .replace(",", ".")
            .trim();

        const parsed = Number(normalized);

        if (Number.isFinite(parsed)) {
            return parsed;
        }
    }

    return fallback;
}


function clamp(
    value,
    minimum,
    maximum,
) {
    return Math.min(
        Math.max(
            value,
            minimum,
        ),
        maximum,
    );
}


function safeText(
    value,
    fallback = "Dados indisponíveis",
) {
    if (
        typeof value === "string"
        &&
        value.trim()
    ) {
        return value.trim();
    }

    if (
        typeof value === "number"
        &&
        Number.isFinite(value)
    ) {
        return String(value);
    }

    return fallback;
}


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatInteger(value) {
    const number = toNumber(
        value,
        NaN,
    );

    if (!Number.isFinite(number)) {
        return "0";
    }

    return new Intl.NumberFormat(
        "pt-PT",
        {
            maximumFractionDigits: 0,
        },
    ).format(number);
}


function formatPercent(value) {
    const number = toNumber(
        value,
        NaN,
    );

    if (!Number.isFinite(number)) {
        return "0%";
    }

    return (
        new Intl.NumberFormat(
            "pt-PT",
            {
                maximumFractionDigits: 1,
            },
        ).format(number)
        +
        "%"
    );
}


function formatSeconds(value) {
    const number = toNumber(
        value,
        0,
    );

    return (
        new Intl.NumberFormat(
            "pt-PT",
            {
                maximumFractionDigits: 1,
            },
        ).format(number)
        +
        "s"
    );
}


function formatDate(value) {
    if (
        typeof value !== "string"
        ||
        !value.trim()
    ) {
        return "Data indisponível";
    }

    const date = new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return value;
    }

    return new Intl.DateTimeFormat(
        "pt-PT",
        {
            dateStyle: "medium",
            timeStyle: "short",
            timeZone: "Europe/Lisbon",
        },
    ).format(date);
}


function setText(
    id,
    value,
) {
    const element =
        document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function setStatus(
    id,
    value,
) {
    const element =
        document.getElementById(id);

    if (!element) {
        return;
    }

    const normalized = safeText(
        value,
        "UNKNOWN",
    ).toUpperCase();

    element.textContent = normalized;

    element.classList.remove(
        "status-success",
        "status-warning",
        "status-neutral",
    );

    if (
        normalized === "READY"
        ||
        normalized === "COMPLETE"
        ||
        normalized === "PUBLISHED"
    ) {
        element.classList.add(
            "status-success"
        );
        return;
    }

    if (
        normalized === "DRAFT"
        ||
        normalized === "SCHEDULED"
        ||
        normalized === "BLOCKED"
    ) {
        element.classList.add(
            "status-warning"
        );
        return;
    }

    element.classList.add(
        "status-neutral"
    );
}


async function fetchJson(
    name,
    url,
) {
    const response = await fetch(
        url,
        {
            cache: "no-store",
        },
    );

    if (!response.ok) {
        throw new Error(
            `${name}: HTTP ${response.status}`
        );
    }

    const payload = await response.json();

    if (!isObject(payload)) {
        throw new Error(
            `${name} não contém um objeto JSON válido.`
        );
    }

    return payload;
}


async function loadProductionStudioData() {
    const entries = await Promise.all(
        Object.entries(DATA_FILES)
            .map(
                async (
                    [name, url],
                ) => {
                    const payload =
                        await fetchJson(
                            name,
                            url,
                        );

                    return [
                        name,
                        payload,
                    ];
                },
            ),
    );

    return Object.fromEntries(
        entries
    );
}


function getDashboardMetrics(
    dashboard,
) {
    const metrics = isObject(
        dashboard.metrics
    )
        ? dashboard.metrics
        : {};

    return {
        viewsLow: firstDefined(
            metrics.predicted_views_low,
            metrics.views_low,
            metrics.low_views,
            dashboard.predicted_views_low,
        ),

        viewsHigh: firstDefined(
            metrics.predicted_views_high,
            metrics.views_high,
            metrics.high_views,
            dashboard.predicted_views_high,
        ),

        confidence: firstDefined(
            metrics.confidence_score,
            metrics.confidence,
            dashboard.confidence_score,
        ),

        commentRate: firstDefined(
            metrics.predicted_comment_rate_percent,
            metrics.comment_rate_percent,
            metrics.comments_percent,
            dashboard.predicted_comment_rate_percent,
        ),
    };
}


function renderHeader(
    dashboard,
) {
    setText(
        "generated-at",
        formatDate(
            dashboard.generated_at
        ),
    );

    setText(
        "channel-name",
        safeText(
            dashboard.channel,
            "Canal não definido",
        ),
    );
}


function renderOverview(
    dashboard,
    content,
    publishing,
) {
    const sourceTopic = isObject(
        content.source_topic
    )
        ? content.source_topic
        : {};

    const publishingMetadata = isObject(
        publishing.metadata
    )
        ? publishing.metadata
        : {};

    const contentPublishing = isObject(
        content.publishing
    )
        ? content.publishing
        : {};

    const voiceover = isObject(
        content.voiceover
    )
        ? content.voiceover
        : {};

    const title = firstDefined(
        sourceTopic.title,
        dashboard.top_title,
    );

    const hook = firstDefined(
        sourceTopic.hook,
        dashboard.top_hook,
    );

    const viralProbability = clamp(
        toNumber(
            firstDefined(
                sourceTopic.viral_probability,
                dashboard.viral_probability,
            ),
            0,
        ),
        0,
        100,
    );

    const platform = firstDefined(
        publishingMetadata.platform,
        contentPublishing.platform,
    );

    const language = firstDefined(
        voiceover.language,
        content.language,
    );

    const publishingReadiness = isObject(
        publishing.readiness
    )
        ? publishing.readiness
        : {};

    const productionStatus = safeText(
        firstDefined(
            publishingReadiness.status,
            publishing.status,
        ),
        "draft",
    );

    setText(
        "top-title",
        safeText(
            title,
            "Título indisponível",
        ),
    );

    setText(
        "top-hook",
        safeText(
            hook,
            "Hook indisponível",
        ),
    );

    setText(
        "viral-probability",
        `${Math.round(viralProbability)}%`,
    );

    setText(
        "winner-priority",
        `#${toNumber(
            sourceTopic.priority,
            1,
        )}`,
    );

    setText(
        "content-platform",
        safeText(
            platform,
            "Plataforma não definida",
        ),
    );

    setText(
        "content-language",
        safeText(
            language,
            "Idioma não definido",
        ),
    );

    const scenes = Array.isArray(
        content.scenes
    )
        ? content.scenes
        : [];

    const totalDuration = scenes.reduce(
        (
            total,
            scene,
        ) => {
            if (!isObject(scene)) {
                return total;
            }

            return (
                total
                +
                toNumber(
                    scene.duration_seconds,
                    0,
                )
            );
        },
        0,
    );

    setText(
        "content-duration",
        totalDuration > 0
            ? `${totalDuration} segundos`
            : "Duração não definida",
    );

    setStatus(
        "overview-production-status",
        productionStatus,    );

    setText(
        "overview-generated-at",
        formatDate(
            dashboard.generated_at
        ),
    );

    const progress =
        document.getElementById(
            "viral-progress"
        );

    if (progress) {
        progress.style.width =
            `${viralProbability}%`;
    }

    const ring =
        document.querySelector(
            ".score-ring"
        );

    if (ring) {
        ring.style.setProperty(
            "--score-angle",
            `${viralProbability * 3.6}deg`,
        );
    }
}


function renderPipelineStatus(
    content,
    publishing,
    analytics,
) {
    const scenes = Array.isArray(
        content.scenes
    )
        ? content.scenes
        : [];

    const publishingReadiness = isObject(
        publishing.readiness
    )
        ? publishing.readiness
        : {};

    const publishingStatus = safeText(
        firstDefined(
            publishingReadiness.status,
            publishing.status,
        ),
        "draft",
    );

    const analyticsStatus = safeText(
        analytics.status,
        "pending",
    );

    setStatus(
        "editorial-status",
        "ready",
    );

    setStatus(
        "production-status",
        "ready",
    );

    setText(
        "production-scene-count",
        (
            scenes.length === 1
                ? "1 cena"
                : `${scenes.length} cenas`
        ),
    );

    setStatus(
        "publishing-status",
        publishingStatus,
    );

    setStatus(
        "analytics-status",
        analyticsStatus,
    );

    setStatus(
        "readiness-editorial",
        "ready",
    );

    setStatus(
        "readiness-content",
        "ready",
    );

    setStatus(
        "readiness-publishing",
        publishingStatus,
    );

    setStatus(
        "readiness-analytics",
        analyticsStatus,
    );

    setStatus(
        "publishing-state-badge",
        publishingStatus,
    );

    setStatus(
        "analytics-state-badge",
        analyticsStatus,
    );
}


function renderPerformanceSummary(
    dashboard,
    content,
) {
    const metrics =
        getDashboardMetrics(
            dashboard
        );

    const low = (
        metrics.viewsLow !== null
        &&
        metrics.viewsLow !== undefined
    )
        ? formatInteger(
            metrics.viewsLow
        )
        : null;

    const high = (
        metrics.viewsHigh !== null
        &&
        metrics.viewsHigh !== undefined
    )
        ? formatInteger(
            metrics.viewsHigh
        )
        : null;

    setText(
        "views-range",
        (
            low !== null
            &&
            high !== null
        )
            ? `${low} – ${high}`
            : "Dados indisponíveis",
    );

    setText(
        "confidence-score",
        (
            metrics.confidence !== null
            &&
            metrics.confidence !== undefined
        )
            ? formatPercent(
                metrics.confidence
            )
            : "Dados indisponíveis",
    );

    setText(
        "comment-rate",
        (
            metrics.commentRate !== null
            &&
            metrics.commentRate !== undefined
        )
            ? formatPercent(
                metrics.commentRate
            )
            : "Dados indisponíveis",
    );

    const scenes = Array.isArray(
        content.scenes
    )
        ? content.scenes
        : [];

    setText(
        "scene-count",
        String(
            scenes.length
        ),
    );
}


function normalizeHookItem(item) {
    if (typeof item === "string") {
        return item;
    }

    if (isObject(item)) {
        return firstDefined(
            item.text,
            item.hook,
            item.value,
            item.title,
        );
    }

    return null;
}


function renderHooks(
    dashboard,
) {
    const hooks = dashboard.hooks;

    let primary = firstDefined(
        dashboard.top_hook,
        dashboard.primary_hook,
    );

    let alternatives = [];

    if (isObject(hooks)) {
        primary = firstDefined(
            hooks.primary,
            hooks.primary_hook,
            hooks.main,
            primary,
        );

        const values = firstDefined(
            hooks.alternatives,
            hooks.alternative_hooks,
            hooks.items,
        );

        if (Array.isArray(values)) {
            alternatives = values;
        }
    }

    if (Array.isArray(hooks)) {
        alternatives = hooks;
    }

    alternatives = alternatives
        .map(normalizeHookItem)
        .filter(Boolean);

    const container =
        document.getElementById(
            "hooks-list"
        );

    if (!container) {
        return;
    }

    const alternativesHtml =
        alternatives
            .map(
                (
                    hook,
                    index,
                ) => `
                    <article class="hook-card">
                        <span class="hook-label">
                            ALTERNATIVA ${index + 1}
                        </span>

                        <p>
                            ${escapeHtml(hook)}
                        </p>
                    </article>
                `,
            )
            .join("");

    container.innerHTML = `
        <article class="hook-card hook-card-primary">
            <span class="hook-label">
                PRIMARY HOOK
            </span>

            <p>
                ${escapeHtml(
                    safeText(
                        primary,
                        "Hook principal indisponível.",
                    ),
                )}
            </p>
        </article>

        ${alternativesHtml}
    `;
}


function renderRanking(
    dashboard,
) {
    const source = Array.isArray(
        dashboard.ranking
    )
        ? dashboard.ranking
        : [];

    const ranking = source
        .filter(isObject)
        .map(
            (
                item,
                index,
            ) => {
                return {
                    priority: toNumber(
                        firstDefined(
                            item.priority,
                            item.position,
                            item.rank,
                        ),
                        index + 1,
                    ),

                    title: safeText(
                        firstDefined(
                            item.title,
                            item.primary_title,
                            item.topic,
                        ),
                        `Tema ${index + 1}`,
                    ),

                    hook: safeText(
                        firstDefined(
                            item.hook,
                            item.primary_hook,
                            item.reason,
                        ),
                        "Sem descrição editorial.",
                    ),

                    viralProbability: clamp(
                        toNumber(
                            firstDefined(
                                item.viral_probability,
                                item.viral_score,
                                item.score,
                            ),
                            0,
                        ),
                        0,
                        100,
                    ),
                };
            },
        )
        .sort(
            (
                left,
                right,
            ) => (
                left.priority
                -
                right.priority
            ),
        );

    setText(
        "ranking-count",
        (
            ranking.length === 1
                ? "1 tema"
                : `${ranking.length} temas`
        ),
    );

    const container =
        document.getElementById(
            "ranking-list"
        );

    if (!container) {
        return;
    }

    if (!ranking.length) {
        container.innerHTML = `
            <p class="empty-state">
                Sem ranking disponível.
            </p>
        `;
        return;
    }

    container.innerHTML =
        ranking
            .map(
                (item) => `
                    <article class="ranking-item">

                        <div class="ranking-number">
                            #${escapeHtml(item.priority)}
                        </div>

                        <div class="ranking-title">
                            <strong>
                                ${escapeHtml(item.title)}
                            </strong>

                            <span>
                                ${escapeHtml(item.hook)}
                            </span>
                        </div>

                        <div class="ranking-bar">
                            <div
                                class="ranking-bar-value"
                                style="width: ${item.viralProbability}%"
                            ></div>
                        </div>

                        <div class="ranking-score">
                            ${Math.round(item.viralProbability)}%
                        </div>

                    </article>
                `,
            )
            .join("");
}


function renderScriptStudio(
    content,
) {
    const script = isObject(
        content.script
    )
        ? content.script
        : {};

    setText(
        "script-hook",
        safeText(
            script.hook,
            "Dados indisponíveis.",
        ),
    );

    setText(
        "script-introduction",
        safeText(
            script.introduction,
            "Dados indisponíveis.",
        ),
    );

    setText(
        "script-development",
        safeText(
            script.development,
            "Dados indisponíveis.",
        ),
    );

    setText(
        "script-climax",
        safeText(
            script.climax,
            "Dados indisponíveis.",
        ),
    );

    setText(
        "script-ending",
        safeText(
            script.ending,
            "Dados indisponíveis.",
        ),
    );

    setText(
        "script-call-to-action",
        safeText(
            script.call_to_action,
            "Dados indisponíveis.",
        ),
    );

    const voiceover = isObject(
        content.voiceover
    )
        ? content.voiceover
        : {};

    const segments = Array.isArray(
        voiceover.segments
    )
        ? voiceover.segments
        : [];

    const language = safeText(
        voiceover.language,
        "pt-PT",
    );

    setText(
        "script-language",
        language,
    );

    setText(
        "voice-language",
        language,
    );

    setText(
        "voice-style",
        safeText(
            voiceover.style,
            "—",
        ),
    );

    setText(
        "voice-segment-count",
        String(
            segments.length
        ),
    );
}


function renderStoryboard(
    content,
) {
    const scenes = Array.isArray(
        content.scenes
    )
        ? content.scenes
        : [];

    const container =
        document.getElementById(
            "storyboard-list"
        );

    const totalDuration = scenes.reduce(
        (
            total,
            scene,
        ) => {
            if (!isObject(scene)) {
                return total;
            }

            return (
                total
                +
                toNumber(
                    scene.duration_seconds,
                    0,
                )
            );
        },
        0,
    );

    setText(
        "storyboard-duration",
        `${totalDuration} segundos`,
    );

    if (!container) {
        return;
    }

    if (!scenes.length) {
        container.innerHTML = `
            <p class="empty-state">
                Sem storyboard disponível.
            </p>
        `;
        return;
    }

    let currentSecond = 0;

    container.innerHTML =
        scenes
            .filter(isObject)
            .map(
                (
                    scene,
                    index,
                ) => {
                    const duration = toNumber(
                        scene.duration_seconds,
                        0,
                    );

                    const startSecond =
                        currentSecond;

                    const endSecond =
                        currentSecond
                        +
                        duration;

                    currentSecond =
                        endSecond;

                    return `
                        <article class="scene-card">

                            <div class="scene-header">

                                <span class="scene-number">
                                    CENA ${escapeHtml(
                                        firstDefined(
                                            scene.scene_number,
                                            index + 1,
                                        ),
                                    )}
                                </span>

                                <span class="scene-time">
                                    ${startSecond}s – ${endSecond}s
                                </span>

                            </div>

                            <h3>
                                ${escapeHtml(
                                    safeText(
                                        scene.caption_text,
                                        `Cena ${index + 1}`,
                                    ),
                                )}
                            </h3>

                            <p>
                                ${escapeHtml(
                                    safeText(
                                        scene.visual_instruction,
                                        "Descrição visual indisponível.",
                                    ),
                                )}
                            </p>

                            <div class="scene-tags">

                                <span>
                                    ${escapeHtml(
                                        safeText(
                                            scene.camera_direction,
                                            "static",
                                        ),
                                    )}
                                </span>

                                <span>
                                    ${duration}s
                                </span>

                                <span>
                                    ${escapeHtml(
                                        safeText(
                                            scene.asset_reference,
                                            "asset pendente",
                                        ),
                                    )}
                                </span>

                            </div>

                            <p class="scene-caption">
                                ${escapeHtml(
                                    safeText(
                                        scene.voiceover_segment,
                                        "Voice-over não definido.",
                                    ),
                                )}
                            </p>

                        </article>
                    `;
                },
            )
            .join("");
}function renderAssets(
    content,
) {
    const scenes = Array.isArray(
        content.scenes
    )
        ? content.scenes
        : [];

    const explicitAssets = Array.isArray(
        content.assets
    )
        ? content.assets
        : [];

    const assets = explicitAssets.length
        ? explicitAssets
        : scenes
            .filter(isObject)
            .map(
                (
                    scene,
                    index,
                ) => ({
                    asset_type: "video",
                    description: firstDefined(
                        scene.visual_instruction,
                        `Asset da cena ${index + 1}`,
                    ),
                    reference: firstDefined(
                        scene.asset_reference,
                        `scene-${index + 1}`,
                    ),
                    scene_number: firstDefined(
                        scene.scene_number,
                        index + 1,
                    ),
                }),
            );

    setText(
        "asset-count",
        (
            assets.length === 1
                ? "1 asset"
                : `${assets.length} assets`
        ),
    );

    const container =
        document.getElementById(
            "assets-list"
        );

    if (!container) {
        return;
    }

    if (!assets.length) {
        container.innerHTML = `
            <p class="empty-state">
                Nenhum asset disponível.
            </p>
        `;
        return;
    }

    container.innerHTML =
        assets
            .map(
                (
                    asset,
                    index,
                ) => `
                    <article class="asset-card">

                        <strong>
                            Cena ${escapeHtml(
                                firstDefined(
                                    asset.scene_number,
                                    index + 1,
                                ),
                            )}
                            ·
                            ${escapeHtml(
                                safeText(
                                    asset.asset_type,
                                    "video",
                                ),
                            )}
                        </strong>

                        <span>
                            ${escapeHtml(
                                safeText(
                                    firstDefined(
                                        asset.description,
                                        asset.visual_instruction,
                                    ),
                                    "Asset por definir.",
                                ),
                            )}
                        </span>

                        <span>
                            Ref:
                            ${escapeHtml(
                                safeText(
                                    firstDefined(
                                        asset.reference,
                                        asset.asset_reference,
                                        asset.search_query,
                                    ),
                                    "sem referência",
                                ),
                            )}
                        </span>

                    </article>
                `,
            )
            .join("");
}


function normalizePublishingChecklistEntry(
    key,
    value,
) {
    const fallbackLabel = key
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            (
                character,
            ) => (
                character.toUpperCase()
            ),
        );

    if (isObject(value)) {
        return {
            key,

            label: safeText(
                value.label,
                fallbackLabel,
            ),

            detail: safeText(
                value.detail,
                "",
            ),

            completed:
                value.completed === true,

            blocking:
                value.blocking !== false,
        };
    }

    return {
        key,
        label: fallbackLabel,
        detail: "",
        completed:
            value === true,
        blocking: true,
    };
}


function getPublishingReadiness(
    publishing,
) {
    const readiness = isObject(
        publishing.readiness
    )
        ? publishing.readiness
        : {};

    const lifecycleStatus = safeText(
        firstDefined(
            readiness.lifecycle_status,
            publishing.status,
        ),
        "draft",
    ).toLowerCase();

    const readinessStatus = safeText(
        firstDefined(
            readiness.status,
            publishing.status,
        ),
        lifecycleStatus,
    ).toLowerCase();

    const blockers = Array.isArray(
        readiness.blockers
    )
        ? readiness.blockers
        : [];

    return {
        lifecycleStatus,

        readinessStatus,

        completionPercent: clamp(
            toNumber(
                readiness.completion_percent,
                0,
            ),
            0,
            100,
        ),

        blockerCount: Math.max(
            0,
            toNumber(
                firstDefined(
                    readiness.blocker_count,
                    blockers.length,
                ),
                blockers.length,
            ),
        ),

        blockers,

        recommendedPublishTime:
            firstDefined(
                readiness.recommended_publish_time,
                (
                    isObject(
                        publishing.metadata
                    )
                        ? (
                            publishing
                            .metadata
                            .recommended_publish_time
                        )
                        : null
                ),
            ),

        scheduledWindow:
            firstDefined(
                readiness.scheduled_window,
                (
                    isObject(
                        publishing.metadata
                    )
                        ? (
                            publishing
                            .metadata
                            .scheduled_window
                        )
                        : null
                ),
            ),
    };
}


function renderPublishing(
    publishing,
) {
    const metadata = isObject(
        publishing.metadata
    )
        ? publishing.metadata
        : {};

    const thumbnail = isObject(
        publishing.thumbnail
    )
        ? publishing.thumbnail
        : {};

    const checklist = isObject(
        publishing.checklist
    )
        ? publishing.checklist
        : {};

    const readiness =
        getPublishingReadiness(
            publishing
        );

    setStatus(
        "publishing-state-badge",
        readiness.readinessStatus,
    );

    setText(
        "publishing-title",
        safeText(
            metadata.title,
            "Dados indisponíveis",
        ),
    );

    setText(
        "publishing-description",
        safeText(
            metadata.description,
            "Dados indisponíveis.",
        ),
    );

    const scheduleParts = [
        safeText(
            readiness.scheduledWindow,
            "",
        ),

        safeText(
            readiness.recommendedPublishTime,
            "",
        ),
    ].filter(Boolean);

    setText(
        "publishing-window",
        scheduleParts.length
            ? scheduleParts.join(" · ")
            : "—",
    );

    setText(
        "thumbnail-text-overlay",
        safeText(
            thumbnail.text_overlay,
            "THUMBNAIL",
        ),
    );

    setText(
        "thumbnail-visual-direction",
        safeText(
            thumbnail.visual_direction,
            "—",
        ),
    );

    setText(
        "thumbnail-emotion-target",
        safeText(
            thumbnail.emotion_target,
            "—",
        ),
    );

    const thumbnailPreview =
        document.querySelector(
            ".thumbnail-preview"
        );

    const thumbnailPublicPath =
        safeText(
            thumbnail.asset_public_path,
            "",
        );

    if (
        thumbnailPreview
        &&
        thumbnailPublicPath
    ) {
        const safeThumbnailPath =
            thumbnailPublicPath
                .replaceAll('"', "")
                .replaceAll("'", "");

        thumbnailPreview.style.backgroundImage = (
            "linear-gradient("
            +
            "180deg, "
            +
            "rgba(4, 10, 22, 0.08), "
            +
            "rgba(4, 10, 22, 0.48)"
            +
            "), "
            +
            `url("${safeThumbnailPath}")`
        );

        thumbnailPreview.style.backgroundSize =
            "cover";

        thumbnailPreview.style.backgroundPosition =
            "center";
    }

    const hashtags = Array.isArray(
        metadata.hashtags
    )
        ? metadata.hashtags
        : [];

    const hashtagsContainer =
        document.getElementById(
            "publishing-hashtags"
        );

    if (hashtagsContainer) {
        hashtagsContainer.innerHTML =
            hashtags.length
                ? hashtags
                    .map(
                        (hashtag) => `
                            <span>
                                ${escapeHtml(hashtag)}
                            </span>
                        `,
                    )
                    .join("")
                : `
                    <span>
                        Sem hashtags
                    </span>
                `;
    }

    const checklistContainer =
        document.getElementById(
            "publishing-checklist-list"
        );

    if (!checklistContainer) {
        return;
    }

    const checklistItems =
        Object.entries(checklist)
            .map(
                (
                    [key, value],
                ) => (
                    normalizePublishingChecklistEntry(
                        key,
                        value,
                    )
                ),
            );

    const summaryItems = [
        {
            label: "Lifecycle",
            value: (
                readiness
                .lifecycleStatus
                .toUpperCase()
            ),
            className: "status-warning",
        },

        {
            label: "Readiness",
            value: (
                readiness
                .readinessStatus
                .toUpperCase()
            ),
            className: (
                readiness.readinessStatus
                === "ready"
                    ? "status-success"
                    : "status-warning"
            ),
        },

        {
            label: "Checklist concluída",
            value: (
                `${Math.round(
                    readiness
                    .completionPercent
                )}%`
            ),
            className: (
                readiness.completionPercent
                === 100
                    ? "status-success"
                    : "status-warning"
            ),
        },

        {
            label: "Ações bloqueantes",
            value: String(
                Math.round(
                    readiness.blockerCount
                )
            ),
            className: (
                readiness.blockerCount
                === 0
                    ? "status-success"
                    : "status-warning"
            ),
        },
    ];

    const summaryHtml =
        summaryItems
            .map(
                (item) => `
                    <article class="readiness-item">

                        <span>
                            ${escapeHtml(item.label)}
                        </span>

                        <strong class="${
                            item.className
                        }">
                            ${escapeHtml(item.value)}
                        </strong>

                    </article>
                `,
            )
            .join("");

    const checklistHtml =
        checklistItems.length
            ? checklistItems
                .map(
                    (item) => {
                        const statusLabel =
                            item.completed
                                ? "DONE"
                                : (
                                    item.blocking
                                        ? "BLOCKED"
                                        : "PENDING"
                                );

                        const statusClass =
                            item.completed
                                ? "status-success"
                                : (
                                    item.blocking
                                        ? "status-warning"
                                        : "status-neutral"
                                );

                        const detail = item.detail
                            ? ` — ${item.detail}`
                            : "";

                        return `
                            <article class="readiness-item">

                                <span>
                                    ${escapeHtml(
                                        item.label
                                        +
                                        detail
                                    )}
                                </span>

                                <strong class="${
                                    statusClass
                                }">
                                    ${statusLabel}
                                </strong>

                            </article>
                        `;
                    },
                )
                .join("")
            : `
                <p class="empty-state">
                    Checklist indisponível.
                </p>
            `;

    checklistContainer.innerHTML = (
        summaryHtml
        +
        checklistHtml
    );
}function renderAnalytics(
    analytics,
) {
    const metrics = isObject(
        analytics.metrics
    )
        ? analytics.metrics
        : {};

    const growthSignals = isObject(
        analytics.growth_signals
    )
        ? analytics.growth_signals
        : {};

    const recommendation = isObject(
        analytics.recommendation
    )
        ? analytics.recommendation
        : {};

    setText(
        "analytics-views",
        formatInteger(
            metrics.views
        ),
    );

    setText(
        "analytics-likes",
        formatInteger(
            metrics.likes
        ),
    );

    setText(
        "analytics-comments",
        formatInteger(
            metrics.comments
        ),
    );

    setText(
        "analytics-shares",
        formatInteger(
            metrics.shares
        ),
    );

    setText(
        "analytics-watch-time",
        formatSeconds(
            metrics.average_watch_time_seconds
        ),
    );

    setText(
        "analytics-retention",
        formatPercent(
            metrics.retention_percent
        ),
    );

    setText(
        "analytics-subscribers",
        formatInteger(
            metrics.subscribers_gained
        ),
    );

    setText(
        "next-topic-direction",
        safeText(
            recommendation.next_topic_direction,
            "—",
        ),
    );

    setText(
        "recommended-improvement",
        safeText(
            recommendation.recommended_improvement,
            "—",
        ),
    );

    setText(
        "recommendation-confidence",
        formatPercent(
            recommendation.confidence_score
        ),
    );

    const growthContainer =
        document.getElementById(
            "growth-signals-list"
        );

    if (!growthContainer) {
        return;
    }

    const signals =
        Object.entries(
            growthSignals
        );

    if (!signals.length) {
        growthContainer.innerHTML = `
            <p class="empty-state">
                Sem sinais disponíveis.
            </p>
        `;
        return;
    }

    growthContainer.innerHTML =
        signals
            .map(
                (
                    [key, value],
                ) => {
                    const label = key
                        .replaceAll("_", " ")
                        .replace(
                            /\b\w/g,
                            (
                                character,
                            ) => (
                                character.toUpperCase()
                            ),
                        );

                    const score = clamp(
                        toNumber(
                            value,
                            0,
                        ),
                        0,
                        100,
                    );

                    return `
                        <article class="growth-signal">

                            <div class="readiness-item">

                                <span>
                                    ${escapeHtml(label)}
                                </span>

                                <strong>
                                    ${Math.round(score)}%
                                </strong>

                            </div>

                            <div class="progress-track">

                                <div
                                    class="progress-value"
                                    style="width: ${score}%"
                                ></div>

                            </div>

                        </article>
                    `;
                },
            )
            .join("");
}


function renderProductionStudio(
    state,
) {
    const {
        dashboard,
        content,
        publishing,
        analytics,
    } = state;

    renderHeader(
        dashboard
    );

    renderOverview(
        dashboard,
        content,
        publishing,
    );

    renderPipelineStatus(
        content,
        publishing,
        analytics,
    );

    renderPerformanceSummary(
        dashboard,
        content,
    );

    renderHooks(
        dashboard
    );

    renderRanking(
        dashboard
    );

    renderScriptStudio(
        content
    );

    renderStoryboard(
        content
    );

    renderAssets(
        content
    );

    renderPublishing(
        publishing
    );

    renderAnalytics(
        analytics
    );
}


function showApplication() {
    const loading =
        document.getElementById(
            "loading-screen"
        );

    const application =
        document.getElementById(
            "application"
        );

    if (loading) {
        loading.classList.add(
            "hidden"
        );
    }

    if (application) {
        application.classList.remove(
            "hidden"
        );
    }
}


function showError(error) {
    showApplication();

    const panel =
        document.getElementById(
            "dashboard-error"
        );

    const message =
        document.getElementById(
            "dashboard-error-message"
        );

    if (panel) {
        panel.classList.remove(
            "hidden"
        );
    }

    if (message) {
        message.textContent =
            error instanceof Error
                ? error.message
                : String(error);
    }

    console.error(
        "Production Studio load error:",
        error,
    );
}


async function startProductionStudio() {
    try {
        const state =
            await loadProductionStudioData();

        renderProductionStudio(
            state
        );

        showApplication();

    } catch (error) {
        showError(error);
    }
}


document.addEventListener(
    "DOMContentLoaded",
    startProductionStudio,
);
