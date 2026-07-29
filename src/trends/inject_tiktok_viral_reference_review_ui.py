from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "dashboard" / "index.html"
JAVASCRIPT = ROOT / "dashboard" / "assets" / "dashboard.js"
CSS = ROOT / "dashboard" / "assets" / "dashboard.css"
MARKER = "FOOTBALL-SHORTS-AI-0031C.5G"


HTML_SECTION = '''
            <!-- ================================================== -->
            <!-- FOOTBALL-SHORTS-AI-0031C.5G TIKTOK VIRAL REVIEW -->
            <!-- ================================================== -->

            <section
                id="tiktok-viral-review"
                class="panel tiktok-viral-review-panel"
            >
                <div class="section-heading">
                    <div>
                        <p class="eyebrow">
                            INTERNAL VIDEO REVIEW
                        </p>

                        <h2>
                            TikTok Viral References
                        </h2>
                    </div>

                    <span
                        id="tiktok-viral-review-status"
                        class="count-badge"
                    >
                        VERIFYING
                    </span>
                </div>

                <p class="tiktok-viral-review-note">
                    Apenas referências com tendência e viralidade verificadas.
                    Player oficial TikTok, carregado apenas por ação do utilizador.
                    Sem download, sem cópia local e sem publicação automática.
                </p>

                <div
                    id="tiktok-viral-reference-list"
                    class="tiktok-viral-reference-list"
                >
                    <p class="empty-state">
                        Sem referências virais verificadas.
                    </p>
                </div>
            </section>

'''


JS_RENDERER = r'''
const TIKTOK_REVIEW_PLAYER_WINDOWS =
    new Map();


function normalizeTikTokPlayerUrl(
    value,
) {
    const url = safeText(
        value,
        "",
    );

    if (
        !url.startsWith(
            "https://www.tiktok.com/player/v1/"
        )
    ) {
        return "";
    }

    return url;
}


function sendTikTokPlayerMessage(
    iframe,
    type,
    value = null,
) {
    if (
        !iframe
        ||
        !iframe.contentWindow
    ) {
        return;
    }

    iframe.contentWindow.postMessage(
        {
            type,
            value,
            "x-tiktok-player": true,
        },
        "https://www.tiktok.com",
    );
}


function handleTikTokReviewPlayerMessage(
    event,
) {
    if (
        event.origin
        !==
        "https://www.tiktok.com"
        ||
        !isObject(
            event.data
        )
        ||
        event.data[
            "x-tiktok-player"
        ]
        !==
        true
    ) {
        return;
    }

    const windowConfig =
        TIKTOK_REVIEW_PLAYER_WINDOWS.get(
            event.source
        );

    if (!windowConfig) {
        return;
    }

    if (
        event.data.type
        ===
        "onPlayerReady"
    ) {
        sendTikTokPlayerMessage(
            windowConfig.iframe,
            "seekTo",
            windowConfig.startSeconds,
        );
        return;
    }

    if (
        event.data.type
        !==
        "onCurrentTime"
        ||
        !isObject(
            event.data.value
        )
    ) {
        return;
    }

    const currentTime = toNumber(
        event.data.value.currentTime,
        -1,
    );

    if (
        currentTime
        >=
        windowConfig.endSeconds
    ) {
        sendTikTokPlayerMessage(
            windowConfig.iframe,
            "pause",
        );

        sendTikTokPlayerMessage(
            windowConfig.iframe,
            "seekTo",
            windowConfig.startSeconds,
        );
    }
}


window.addEventListener(
    "message",
    handleTikTokReviewPlayerMessage,
);


function activateTikTokReferenceButton(
    button,
) {
    const playerUrl =
        normalizeTikTokPlayerUrl(
            button.dataset.playerUrl
        );

    const targetId = safeText(
        button.dataset.targetId,
        "",
    );

    const startSeconds = Math.max(
        0,
        toNumber(
            button.dataset.startSeconds,
            0,
        ),
    );

    const durationSeconds = Math.max(
        2,
        Math.min(
            3,
            toNumber(
                button.dataset.durationSeconds,
                3,
            ),
        ),
    );

    const target =
        document.getElementById(
            targetId
        );

    if (
        !playerUrl
        ||
        !target
    ) {
        return;
    }

    let iframe = target.querySelector(
        "iframe"
    );

    if (!iframe) {
        iframe = document.createElement(
            "iframe"
        );

        iframe.src = playerUrl;
        iframe.title = (
            "Player oficial TikTok "
            +
            "para referência viral"
        );
        iframe.loading = "lazy";
        iframe.referrerPolicy =
            "strict-origin-when-cross-origin";
        iframe.allow = (
            "fullscreen; encrypted-media; "
            +
            "picture-in-picture"
        );
        iframe.setAttribute(
            "allowfullscreen",
            "",
        );

        target.replaceChildren(
            iframe
        );

        const windowConfig = {
            iframe,
            startSeconds,
            endSeconds:
                startSeconds
                +
                durationSeconds,
        };

        iframe.addEventListener(
            "load",
            () => {
                if (
                    iframe.contentWindow
                ) {
                    TIKTOK_REVIEW_PLAYER_WINDOWS.set(
                        iframe.contentWindow,
                        windowConfig,
                    );

                    sendTikTokPlayerMessage(
                        iframe,
                        "seekTo",
                        startSeconds,
                    );
                }
            },
            {
                once: true,
            },
        );

        button.textContent =
            `Reproduzir ${durationSeconds}s`;

        button.dataset.playerLoaded =
            "true";

        return;
    }

    sendTikTokPlayerMessage(
        iframe,
        "seekTo",
        startSeconds,
    );

    sendTikTokPlayerMessage(
        iframe,
        "play",
    );
}


function renderTikTokViralReferenceReview(
    review,
) {
    const container =
        document.getElementById(
            "tiktok-viral-reference-list"
        );

    if (!container) {
        return;
    }

    const status = safeText(
        review.status,
        "no_verified_viral_references",
    );

    setText(
        "tiktok-viral-review-status",
        status
            .replaceAll(
                "_",
                " ",
            )
            .toUpperCase(),
    );

    const references =
        Array.isArray(
            review.selected_references
        )
            ? review.selected_references
            : [];

    if (!references.length) {
        container.innerHTML = `
            <article class="tiktok-viral-empty-state">
                <strong>
                    SEM REFERÊNCIA VIRAL VERIFICADA
                </strong>

                <span>
                    O sistema não encontrou um vídeo com
                    sinais oficiais suficientes de tendência
                    e viralidade para este tema.
                </span>

                <span>
                    Nenhum candidato não verificado foi
                    apresentado como viral.
                </span>
            </article>
        `;
        return;
    }

    container.innerHTML =
        references
            .map(
                (
                    reference,
                    index,
                ) => {
                    const trendSignal = isObject(
                        reference.trend_signal
                    )
                        ? reference.trend_signal
                        : {};

                    const viralSignal = isObject(
                        reference.viral_signal
                    )
                        ? reference.viral_signal
                        : {};

                    const embed = isObject(
                        reference.embed
                    )
                        ? reference.embed
                        : {};

                    const windowPayload = isObject(
                        embed.reference_window
                    )
                        ? embed.reference_window
                        : {};

                    const rights = isObject(
                        reference.rights
                    )
                        ? reference.rights
                        : {};

                    const targetId = (
                        "tiktok-reference-player-"
                        +
                        index
                    );

                    const playerUrl =
                        normalizeTikTokPlayerUrl(
                            embed.player_url
                        );

                    const startSeconds = Math.max(
                        0,
                        toNumber(
                            windowPayload.start_seconds,
                            0,
                        ),
                    );

                    const durationSeconds = Math.max(
                        2,
                        Math.min(
                            3,
                            toNumber(
                                windowPayload.duration_seconds,
                                3,
                            ),
                        ),
                    );

                    return `
                        <article class="tiktok-viral-reference-card">

                            <div class="tiktok-viral-reference-heading">
                                <div>
                                    <span class="rank-badge">
                                        #${escapeHtml(
                                            firstDefined(
                                                reference.rank,
                                                index + 1,
                                            )
                                        )}
                                    </span>

                                    <strong>
                                        ${escapeHtml(
                                            safeText(
                                                reference.creator_username,
                                                "Creator TikTok",
                                            ),
                                        )}
                                    </strong>
                                </div>

                                <span class="tiktok-viral-score">
                                    ${Math.round(
                                        toNumber(
                                            reference.total_score,
                                            0,
                                        )
                                    )}%
                                </span>
                            </div>

                            <p>
                                ${escapeHtml(
                                    safeText(
                                        reference.caption,
                                        "Referência TikTok.",
                                    ),
                                )}
                            </p>

                            <div class="tiktok-viral-signal-grid">
                                <span>
                                    TREND
                                    ·
                                    ${escapeHtml(
                                        safeText(
                                            trendSignal.status,
                                            "insufficient",
                                        ).toUpperCase(),
                                    )}
                                    ·
                                    ${Math.round(
                                        toNumber(
                                            trendSignal.confidence_score,
                                            0,
                                        )
                                    )}%
                                </span>

                                <span>
                                    VIRAL
                                    ·
                                    ${escapeHtml(
                                        safeText(
                                            viralSignal.status,
                                            "insufficient",
                                        ).toUpperCase(),
                                    )}
                                    ·
                                    ${Math.round(
                                        toNumber(
                                            viralSignal.confidence_score,
                                            0,
                                        )
                                    )}%
                                </span>
                            </div>

                            <span>
                                ${escapeHtml(
                                    safeText(
                                        trendSignal.evidence,
                                        "Evidência de tendência indisponível.",
                                    ),
                                )}
                            </span>

                            <span>
                                ${escapeHtml(
                                    safeText(
                                        viralSignal.evidence,
                                        "Evidência de viralidade indisponível.",
                                    ),
                                )}
                            </span>

                            <div
                                id="${escapeHtml(targetId)}"
                                class="tiktok-reference-player"
                            >
                                <span>
                                    Player oficial ainda não carregado.
                                </span>
                            </div>

                            <div class="tiktok-reference-actions">
                                <button
                                    type="button"
                                    class="tiktok-reference-load"
                                    data-player-url="${escapeHtml(playerUrl)}"
                                    data-target-id="${escapeHtml(targetId)}"
                                    data-start-seconds="${escapeHtml(startSeconds)}"
                                    data-duration-seconds="${escapeHtml(durationSeconds)}"
                                    data-player-loaded="false"
                                >
                                    Carregar janela de ${escapeHtml(durationSeconds)}s
                                </button>

                                <a
                                    href="${escapeHtml(
                                        safeText(
                                            reference.source_url,
                                            "#",
                                        ),
                                    )}"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    Abrir no TikTok
                                </a>
                            </div>

                            <div class="tiktok-reference-rights">
                                <span>
                                    Direitos:
                                    ${escapeHtml(
                                        safeText(
                                            rights.status,
                                            "reference_only",
                                        )
                                        .replaceAll(
                                            "_",
                                            " ",
                                        )
                                        .toUpperCase(),
                                    )}
                                </span>

                                <span>
                                    Download:
                                    ${rights.automatic_download_allowed === true
                                        ? "ALLOWED"
                                        : "BLOCKED"}
                                </span>

                                <span>
                                    Uso no master:
                                    ${rights.reuse_in_master_allowed === true
                                        ? "ALLOWED"
                                        : "BLOCKED"}
                                </span>
                            </div>

                        </article>
                    `;
                },
            )
            .join("");

    container
        .querySelectorAll(
            ".tiktok-reference-load"
        )
        .forEach(
            (button) => {
                button.addEventListener(
                    "click",
                    () => {
                        activateTikTokReferenceButton(
                            button
                        );
                    },
                );
            },
        );
}


'''


CSS_APPEND = r'''
/* ==========================================================
   FOOTBALL-SHORTS-AI-0031C.5G
   TIKTOK VIRAL REFERENCE REVIEW
   ========================================================== */

.tiktok-viral-review-note {
    margin: 8px 0 20px;
    color: var(--muted);
    line-height: 1.6;
}

.tiktok-viral-reference-list {
    display: grid;
    grid-template-columns:
        repeat(
            3,
            minmax(0, 1fr)
        );
    gap: 18px;
}

.tiktok-viral-reference-card,
.tiktok-viral-empty-state {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 13px;
    padding: 18px;
    border: 1px solid var(--border);
    border-radius: var(--radius-medium);
    background:
        linear-gradient(
            145deg,
            rgba(23, 34, 55, 0.78),
            rgba(10, 16, 27, 0.94)
        );
}

.tiktok-viral-reference-heading,
.tiktok-reference-actions,
.tiktok-reference-rights,
.tiktok-viral-signal-grid {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
}

.tiktok-viral-reference-heading {
    justify-content: space-between;
}

.tiktok-viral-reference-heading > div {
    display: flex;
    align-items: center;
    gap: 10px;
}

.tiktok-viral-score {
    padding: 7px 10px;
    border: 1px solid rgba(52, 211, 153, 0.32);
    border-radius: 999px;
    color: var(--success);
    background: rgba(52, 211, 153, 0.08);
    font-weight: 800;
}

.tiktok-viral-signal-grid span {
    padding: 7px 10px;
    border-radius: 999px;
    background: rgba(56, 189, 248, 0.09);
    color: var(--text);
    font-size: 0.76rem;
    font-weight: 800;
}

.tiktok-reference-player {
    position: relative;
    width: 100%;
    aspect-ratio: 9 / 16;
    overflow: hidden;
    display: grid;
    place-items: center;
    border: 1px solid rgba(56, 189, 248, 0.22);
    border-radius: 16px;
    background: #050c1b;
    color: var(--muted);
    text-align: center;
}

.tiktok-reference-player iframe {
    width: 100%;
    height: 100%;
    border: 0;
}

.tiktok-reference-actions button,
.tiktok-reference-actions a {
    min-height: 40px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 9px 13px;
    border: 1px solid rgba(56, 189, 248, 0.32);
    border-radius: 10px;
    color: var(--text);
    background: rgba(56, 189, 248, 0.08);
    text-decoration: none;
    font: inherit;
    font-weight: 750;
    cursor: pointer;
}

.tiktok-reference-actions button:hover,
.tiktok-reference-actions a:hover {
    background: rgba(56, 189, 248, 0.16);
}

.tiktok-reference-rights {
    padding-top: 12px;
    border-top: 1px solid var(--border);
    color: var(--muted);
    font-size: 0.76rem;
}

.tiktok-viral-empty-state {
    grid-column: 1 / -1;
}

.tiktok-viral-empty-state strong {
    color: var(--warning);
}

@media (max-width: 1120px) {
    .tiktok-viral-reference-list {
        grid-template-columns:
            repeat(
                2,
                minmax(0, 1fr)
            );
    }
}

@media (max-width: 720px) {
    .tiktok-viral-reference-list {
        grid-template-columns: 1fr;
    }
}
'''


def read(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro em falta: {path}")
    return path.read_text(encoding="utf-8")


def save(path: Path, value: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def inject_index(value: str) -> str:
    if MARKER in value:
        return value

    asset_marker = '''
            <!-- ================================================== -->
            <!-- ASSET PLANNER -->
'''

    if asset_marker not in value:
        raise ValueError("Marcador Asset Planner não encontrado.")

    return value.replace(
        asset_marker,
        HTML_SECTION + asset_marker,
        1,
    )


def inject_javascript(value: str) -> str:
    legacy_autoplay_permission = (
        '        iframe.allow = (\n'
        '            "fullscreen; autoplay; "\n'
        '            +\n'
        '            "encrypted-media; picture-in-picture"\n'
        '        );'
    )

    governed_permission = (
        '        iframe.allow = (\n'
        '            "fullscreen; encrypted-media; "\n'
        '            +\n'
        '            "picture-in-picture"\n'
        '        );'
    )

    if legacy_autoplay_permission in value:
        value = value.replace(
            legacy_autoplay_permission,
            governed_permission,
            1,
        )

    if MARKER in value:
        if "fullscreen; autoplay;" in value:
            raise ValueError(
                "Permissão autoplay TikTok não foi removida."
            )
        return value

    data_marker = (
        '    productionPreview: "data/production_preview.json",\n'
        '};'
    )

    if data_marker not in value:
        raise ValueError("DATA_FILES não contém productionPreview.")

    value = value.replace(
        data_marker,
        (
            '    productionPreview: "data/production_preview.json",\n'
            '    tiktokViralReview: '
            '"data/tiktok_viral_reference_review.json",\n'
            '};'
        ),
        1,
    )

    renderer_marker = "\nfunction renderAssets(\n"

    if renderer_marker not in value:
        raise ValueError("Função renderAssets não encontrada.")

    value = value.replace(
        renderer_marker,
        "\n// " + MARKER + "\n" + JS_RENDERER + renderer_marker,
        1,
    )

    state_marker = '''
        productionPreview,
    } = state;
'''

    if state_marker not in value:
        raise ValueError("Estado productionPreview não encontrado.")

    value = value.replace(
        state_marker,
        '''
        productionPreview,
        tiktokViralReview,
    } = state;
''',
        1,
    )

    call_marker = '''
    renderProductionPreview(
        productionPreview
    );

    renderAssets(
'''

    if call_marker not in value:
        raise ValueError("Chamada renderProductionPreview não encontrada.")

    return value.replace(
        call_marker,
        '''
    renderProductionPreview(
        productionPreview
    );

    renderTikTokViralReferenceReview(
        tiktokViralReview
    );

    renderAssets(
''',
        1,
    )


def inject_css(value: str) -> str:
    if MARKER in value:
        return value
    return value.rstrip() + "\n\n" + CSS_APPEND.strip() + "\n"


def main() -> int:
    print("=" * 70)
    print("FOOTBALL-SHORTS-AI-0031C.5G")
    print("TIKTOK VIRAL REVIEW UI INJECTION")
    print("=" * 70)

    save(INDEX, inject_index(read(INDEX)))
    save(JAVASCRIPT, inject_javascript(read(JAVASCRIPT)))
    save(CSS, inject_css(read(CSS)))

    required_markers = {
        INDEX: MARKER,
        JAVASCRIPT: MARKER,
        CSS: MARKER,
    }

    missing = [
        str(path)
        for path, marker in required_markers.items()
        if marker not in read(path)
    ]

    if missing:
        raise ValueError(
            "Marcador TikTok Viral Review ausente em: "
            + ", ".join(missing)
        )

    javascript_source = read(JAVASCRIPT)

    if "fullscreen; autoplay;" in javascript_source:
        raise ValueError(
            "dashboard.js ainda concede autoplay ao iframe TikTok."
        )

    if "fullscreen; encrypted-media; " not in javascript_source:
        raise ValueError(
            "Permissão governada do iframe TikTok não foi encontrada."
        )

    print("TIKTOK_LEGACY_AUTOPLAY_PERMISSION_RECOVERY=PASS")
    print("TIKTOK_VIRAL_REVIEW_HTML=PASS")
    print("TIKTOK_VIRAL_REVIEW_JAVASCRIPT=PASS")
    print("TIKTOK_VIRAL_REVIEW_CSS=PASS")
    print("OFFICIAL_TIKTOK_PLAYER_ONLY=YES")
    print("LAZY_USER_INITIATED_PLAYER_LOAD=YES")
    print("THIRD_PARTY_DOWNLOAD_ALLOWED=NO")
    print("PUBLICATION_EXECUTION_ENABLED=NO")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
