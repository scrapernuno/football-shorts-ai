"use strict";


const DASHBOARD_MODEL_URL =
    "data/dashboard_model.json";


function isObject(value) {

    return (
        value !== null
        &&
        typeof value === "object"
        &&
        !Array.isArray(value)
    );

}


function firstDefined(
    ...values
) {

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


        const parsed = Number(
            normalized
        );


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

        return null;

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

        return null;

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


function getMetrics(model) {

    const metrics = isObject(
        model.metrics
    )
        ? model.metrics
        : {};


    const analytics = isObject(
        model.analytics
    )
        ? model.analytics
        : {};


    return {

        viewsLow: firstDefined(
            metrics.predicted_views_low,
            metrics.views_low,
            metrics.low_views,
            analytics.predicted_views_low,
            model.predicted_views_low,
        ),


        viewsHigh: firstDefined(
            metrics.predicted_views_high,
            metrics.views_high,
            metrics.high_views,
            analytics.predicted_views_high,
            model.predicted_views_high,
        ),


        confidence: firstDefined(
            metrics.confidence_score,
            metrics.confidence,
            analytics.confidence_score,
            model.confidence_score,
        ),


        commentRate: firstDefined(
            metrics.predicted_comment_rate_percent,
            metrics.comment_rate_percent,
            metrics.comments_percent,
            analytics.predicted_comment_rate_percent,
            model.predicted_comment_rate_percent,
        ),

    };

}


function getHooks(model) {

    const hooks = model.hooks;


    let primary = firstDefined(
        model.top_hook,
        model.primary_hook,
    );


    let alternatives = [];


    if (isObject(hooks)) {

        primary = firstDefined(
            hooks.primary,
            hooks.primary_hook,
            hooks.main,
            primary,
        );


        const candidateAlternatives = firstDefined(
            hooks.alternatives,
            hooks.alternative_hooks,
            hooks.items,
        );


        if (
            Array.isArray(
                candidateAlternatives
            )
        ) {

            alternatives =
                candidateAlternatives;

        }

    }


    if (Array.isArray(hooks)) {

        alternatives = hooks;

    }


    alternatives = alternatives
        .map((item) => {

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

        })
        .filter(Boolean);


    return {
        primary:
            safeText(
                primary,
                "Hook principal indisponível.",
            ),

        alternatives:
            alternatives,
    };

}


function getRanking(model) {

    if (
        !Array.isArray(
            model.ranking
        )
    ) {

        return [];

    }


    return model.ranking
        .filter(isObject)
        .map(
            (
                item,
                index,
            ) => {

                const probability = clamp(
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
                );


                return {

                    priority:
                        toNumber(
                            firstDefined(
                                item.priority,
                                item.position,
                                item.rank,
                            ),
                            index + 1,
                        ),


                    title:
                        safeText(
                            firstDefined(
                                item.title,
                                item.primary_title,
                                item.topic,
                            ),
                            `Tema ${index + 1}`,
                        ),


                    hook:
                        safeText(
                            firstDefined(
                                item.hook,
                                item.primary_hook,
                                item.reason,
                            ),
                            "Sem descrição editorial.",
                        ),


                    viralProbability:
                        probability,

                };

            },
        )
        .sort(
            (
                left,
                right,
            ) => {

                return (
                    left.priority
                    -
                    right.priority
                );

            },
        );

}


function getStoryboard(model) {

    const source = model.storyboard;


    if (Array.isArray(source)) {

        return source;

    }


    if (
        isObject(source)
        &&
        Array.isArray(
            source.scenes
        )
    ) {

        return source.scenes;

    }


    return [];

}


function normalizeScene(
    scene,
    index,
) {

    const startSecond = toNumber(
        firstDefined(
            scene.start_second,
            scene.start,
        ),
        0,
    );


    const endSecond = toNumber(
        firstDefined(
            scene.end_second,
            scene.end,
        ),
        startSecond,
    );


    const asset = isObject(
        scene.asset
    )
        ? scene.asset
        : {};


    return {

        number:
            toNumber(
                firstDefined(
                    scene.scene_number,
                    scene.number,
                ),
                index + 1,
            ),


        startSecond:
            startSecond,


        endSecond:
            endSecond,


        title:
            safeText(
                firstDefined(
                    scene.subtitle,
                    scene.caption_text,
                    scene.title,
                ),
                `Cena ${index + 1}`,
            ),


        description:
            safeText(
                firstDefined(
                    scene.visual_description,
                    scene.visual_instruction,
                    scene.voiceover,
                    scene.description,
                ),
                "Descrição visual indisponível.",
            ),


        voiceover:
            safeText(
                firstDefined(
                    scene.voiceover,
                    scene.voiceover_segment,
                ),
                "Voice-over não definido.",
            ),


        visualType:
            safeText(
                firstDefined(
                    scene.visual_type,
                    asset.asset_type,
                ),
                "video",
            ),


        cameraMovement:
            safeText(
                firstDefined(
                    scene.camera_movement,
                    scene.camera_direction,
                ),
                "static",
            ),


        editingPace:
            safeText(
                scene.editing_pace,
                "medium",
            ),


        transition:
            safeText(
                scene.transition,
                "cut",
            ),


        assetDescription:
            safeText(
                firstDefined(
                    asset.description,
                    asset.fallback_description,
                    scene.asset_reference,
                ),
                "Asset por definir.",
            ),


        assetSource:
            safeText(
                firstDefined(
                    asset.preferred_source,
                    asset.source,
                ),
                "Fonte por confirmar.",
            ),

    };

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


function renderHeader(model) {

    setText(
        "generated-at",
        formatDate(
            model.generated_at
        ),
    );


    setText(
        "channel-name",
        safeText(
            model.channel,
            "Canal não definido",
        ),
    );

}


function renderWinner(model) {

    const probability = clamp(
        toNumber(
            model.viral_probability,
            0,
        ),
        0,
        100,
    );


    setText(
        "top-title",
        safeText(
            model.top_title,
            "Título indisponível",
        ),
    );


    setText(
        "top-hook",
        safeText(
            model.top_hook,
            "Hook indisponível",
        ),
    );


    setText(
        "viral-probability",
        `${Math.round(probability)}%`,
    );


    const progress =
        document.getElementById(
            "viral-progress"
        );


    if (progress) {

        progress.style.width =
            `${probability}%`;

    }


    const ring =
        document.querySelector(
            ".score-ring"
        );


    if (ring) {

        ring.style.setProperty(
            "--score-angle",
            `${probability * 3.6}deg`,
        );

    }

}


function renderMetrics(
    model,
    sceneCount,
) {

    const metrics =
        getMetrics(model);


    const low = formatInteger(
        metrics.viewsLow
    );


    const high = formatInteger(
        metrics.viewsHigh
    );


    const viewsText = (
        low !== null
        &&
        high !== null
    )
        ? `${low} – ${high}`
        : "Dados indisponíveis";


    setText(
        "views-range",
        viewsText,
    );


    setText(
        "confidence-score",
        formatPercent(
            metrics.confidence
        )
        ??
        "Dados indisponíveis",
    );


    setText(
        "comment-rate",
        formatPercent(
            metrics.commentRate
        )
        ??
        "Dados indisponíveis",
    );


    setText(
        "scene-count",
        String(sceneCount),
    );

}


function renderHooks(model) {

    const hooks =
        getHooks(model);


    const container =
        document.getElementById(
            "hooks-list"
        );


    if (!container) {

        return;

    }


    const alternatives =
        hooks.alternatives
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
                ${escapeHtml(hooks.primary)}
            </p>
        </article>

        ${alternatives}
    `;

}


function renderRanking(model) {

    const ranking =
        getRanking(model);


    const container =
        document.getElementById(
            "ranking-list"
        );


    setText(
        "ranking-count",
        (
            ranking.length === 1
                ? "1 tema"
                : `${ranking.length} temas`
        ),
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


function renderStoryboard(model) {

    const rawScenes =
        getStoryboard(model);


    const scenes =
        rawScenes
            .filter(isObject)
            .map(normalizeScene);


    const container =
        document.getElementById(
            "storyboard-list"
        );


    const duration = scenes.reduce(
        (
            highest,
            scene,
        ) => {

            return Math.max(
                highest,
                scene.endSecond,
            );

        },
        0,
    );


    setText(
        "storyboard-duration",
        `${duration} segundos`,
    );


    if (!container) {

        return scenes;

    }


    if (!scenes.length) {

        container.innerHTML = `
            <p class="empty-state">
                Sem storyboard disponível.
            </p>
        `;

        return scenes;

    }


    container.innerHTML =
        scenes
            .map(
                (scene) => `
                    <article class="scene-card">

                        <div class="scene-header">

                            <span class="scene-number">
                                CENA ${scene.number}
                            </span>

                            <span class="scene-time">
                                ${scene.startSecond}s – ${scene.endSecond}s
                            </span>

                        </div>

                        <h3>
                            ${escapeHtml(scene.title)}
                        </h3>

                        <p>
                            ${escapeHtml(scene.description)}
                        </p>

                        <div class="scene-tags">

                            <span>
                                ${escapeHtml(scene.visualType)}
                            </span>

                            <span>
                                ${escapeHtml(scene.cameraMovement)}
                            </span>

                            <span>
                                ${escapeHtml(scene.editingPace)}
                            </span>

                            <span>
                                ${escapeHtml(scene.transition)}
                            </span>

                        </div>

                        <p class="scene-caption">
                            ${escapeHtml(scene.voiceover)}
                        </p>

                    </article>
                `,
            )
            .join("");


    return scenes;

}


function renderAssets(scenes) {

    const container =
        document.getElementById(
            "assets-list"
        );


    if (!container) {

        return;

    }


    if (!scenes.length) {

        container.innerHTML = `
            <p class="empty-state">
                Nenhum asset disponível.
            </p>
        `;

        return;

    }


    container.innerHTML =
        scenes
            .map(
                (scene) => `
                    <article class="asset-card">

                        <strong>
                            Cena ${scene.number} ·
                            ${escapeHtml(scene.assetDescription)}
                        </strong>

                        <span>
                            ${escapeHtml(scene.assetSource)}
                        </span>

                    </article>
                `,
            )
            .join("");

}


function renderDashboard(model) {

    if (!isObject(model)) {

        throw new Error(
            "O dashboard_model.json não contém "
            +
            "um objeto JSON válido."
        );

    }


    renderHeader(model);

    renderWinner(model);

    renderHooks(model);

    renderRanking(model);


    const scenes =
        renderStoryboard(model);


    renderMetrics(
        model,
        scenes.length,
    );


    renderAssets(scenes);

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
        "Dashboard load error:",
        error,
    );

}


async function loadDashboard() {

    try {

        const response = await fetch(
            DASHBOARD_MODEL_URL,
            {
                cache: "no-store",
            },
        );


        if (!response.ok) {

            throw new Error(
                "Não foi possível carregar "
                +
                `dashboard_model.json: HTTP ${response.status}.`
            );

        }


        const model =
            await response.json();


        renderDashboard(model);

        showApplication();

    } catch (error) {

        showError(error);

    }

}


document.addEventListener(
    "DOMContentLoaded",
    loadDashboard,
);
