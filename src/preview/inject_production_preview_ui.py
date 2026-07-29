from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "dashboard/index.html"
JAVASCRIPT = ROOT / "dashboard/assets/dashboard.js"
CSS = ROOT / "dashboard/assets/dashboard.css"
MARKER = "FOOTBALL-SHORTS-AI-0031C.5E"

HTML_SECTION = '''
            <!-- ================================================== -->
            <!-- FOOTBALL-SHORTS-AI-0031C.5E PRODUCTION PREVIEW -->
            <!-- ================================================== -->

            <section
                id="production-preview"
                class="panel production-preview-panel"
            >
                <div class="section-heading">
                    <div>
                        <p class="eyebrow">INTERNAL VIDEO REVIEW</p>
                        <h2>Pré-visualização de produção</h2>
                    </div>
                    <span
                        id="production-preview-status"
                        class="count-badge"
                    >
                        INTERNAL
                    </span>
                </div>

                <div class="production-preview-grid">
                    <article class="production-preview-video-card">
                        <video
                            id="production-preview-video"
                            controls
                            playsinline
                            preload="metadata"
                            aria-label="Pré-visualização interna do Short"
                        >
                            <track
                                id="production-preview-captions"
                                kind="captions"
                                srclang="pt"
                                label="Português"
                                default
                            >
                        </video>
                    </article>

                    <article class="production-preview-info-card">
                        <div class="production-preview-warning">
                            <strong>PRODUCTION PREVIEW</strong>
                            <span>NOT FOR PUBLICATION</span>
                        </div>

                        <dl class="detail-list">
                            <div>
                                <dt>Duração</dt>
                                <dd id="production-preview-duration">—</dd>
                            </div>
                            <div>
                                <dt>Formato</dt>
                                <dd id="production-preview-format">—</dd>
                            </div>
                            <div>
                                <dt>Voz</dt>
                                <dd id="production-preview-voice">—</dd>
                            </div>
                            <div>
                                <dt>Assets reais usados</dt>
                                <dd id="production-preview-assets">NÃO</dd>
                            </div>
                            <div>
                                <dt>Finalidade</dt>
                                <dd>Orientação e revisão interna</dd>
                            </div>
                        </dl>
                    </article>
                </div>
            </section>

'''

JS_RENDERER = r'''
function renderProductionPreview(
    preview,
) {
    const format = isObject(preview.format)
        ? preview.format
        : {};

    const voice = isObject(preview.voice)
        ? preview.voice
        : {};

    const artifacts = isObject(preview.artifacts)
        ? preview.artifacts
        : {};

    const videoArtifact = isObject(artifacts.video)
        ? artifacts.video
        : {};

    const captionsArtifact = isObject(artifacts.captions)
        ? artifacts.captions
        : {};

    const governance = isObject(preview.governance)
        ? preview.governance
        : {};

    setText(
        "production-preview-status",
        safeText(preview.status, "internal")
            .replaceAll("_", " ")
            .toUpperCase(),
    );

    setText(
        "production-preview-duration",
        `${toNumber(format.duration_seconds, 0)} segundos`,
    );

    setText(
        "production-preview-format",
        (
            `${toNumber(format.width, 1080)} × `
            +
            `${toNumber(format.height, 1920)}`
            +
            " · "
            +
            safeText(format.aspect_ratio, "9:16")
        ),
    );

    setText(
        "production-preview-voice",
        (
            `${safeText(voice.language, "pt-PT")}`
            +
            " · "
            +
            `${safeText(voice.voice, "—")}`
            +
            " · "
            +
            `${safeText(voice.status, "unknown")
                .replaceAll("_", " ")
                .toUpperCase()}`
        ),
    );

    setText(
        "production-preview-assets",
        governance.selected_source_assets_used === true
            ? "SIM"
            : "NÃO",
    );

    const video =
        document.getElementById("production-preview-video");

    const captions =
        document.getElementById("production-preview-captions");

    const videoPath = safeText(videoArtifact.public_path, "");
    const captionsPath = safeText(captionsArtifact.public_path, "");

    if (video && videoPath) {
        video.src = videoPath;
    }

    if (captions && captionsPath) {
        captions.src = captionsPath;
    }

    if (video) {
        video.load();
    }
}


'''

CSS_APPEND = r'''
/* ==========================================================
   FOOTBALL-SHORTS-AI-0031C.5E
   AI PRODUCTION PREVIEW
   ========================================================== */

.production-preview-grid {
    display: grid;
    grid-template-columns:
        minmax(260px, 430px)
        minmax(0, 1fr);
    gap: 22px;
    align-items: start;
    margin-top: 20px;
}

.production-preview-video-card,
.production-preview-info-card {
    min-width: 0;
    padding: 18px;
    border: 1px solid var(--border);
    border-radius: var(--radius-medium);
    background:
        linear-gradient(
            145deg,
            rgba(23, 34, 55, 0.76),
            rgba(10, 16, 27, 0.92)
        );
}

.production-preview-video-card {
    max-width: 430px;
    margin: 0 auto;
}

#production-preview-video {
    width: 100%;
    aspect-ratio: 9 / 16;
    display: block;
    border-radius: 16px;
    background: #050c1b;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.42);
}

.production-preview-warning {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px;
    border: 1px solid rgba(250, 204, 21, 0.28);
    border-radius: 14px;
    background: rgba(250, 204, 21, 0.08);
}

.production-preview-warning span {
    color: var(--warning);
    font-weight: 800;
}

@media (max-width: 840px) {
    .production-preview-grid {
        grid-template-columns: 1fr;
    }

    .production-preview-video-card {
        width: min(100%, 430px);
    }
}
'''


def read(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro em falta: {path}")
    return path.read_text(encoding="utf-8")


def save(path: Path, value: str) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(value, encoding="utf-8")
    temp.replace(path)


def inject_index(value: str) -> str:
    if MARKER in value:
        return value

    nav = '''
            <a href="#storyboard">
                Storyboard
            </a>
'''
    if nav not in value:
        raise ValueError("Navegação Storyboard não encontrada.")

    value = value.replace(
        nav,
        nav + '''
            <a href="#production-preview">
                Preview
            </a>
''',
        1,
    )

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


def inject_js(value: str) -> str:
    if MARKER in value:
        return value

    data_marker = (
        '    platformVariants: "data/platform_variants.json",\n'
        '};'
    )
    if data_marker not in value:
        raise ValueError("DATA_FILES não contém platformVariants.")

    value = value.replace(
        data_marker,
        (
            '    platformVariants: "data/platform_variants.json",\n'
            '    productionPreview: "data/production_preview.json",\n'
            '};'
        ),
        1,
    )

    renderer_marker = "\nfunction renderAssets(\n"
    if renderer_marker not in value:
        raise ValueError("renderAssets não encontrada.")

    value = value.replace(
        renderer_marker,
        "\n// " + MARKER + "\n" + JS_RENDERER + renderer_marker,
        1,
    )

    state_marker = '''
        platformVariants,
    } = state;
'''
    if state_marker not in value:
        raise ValueError("Desestruturação do estado não encontrada.")

    value = value.replace(
        state_marker,
        '''
        platformVariants,
        productionPreview,
    } = state;
''',
        1,
    )

    call_marker = '''
    renderStoryboard(
        content
    );

    renderAssets(
'''
    if call_marker not in value:
        raise ValueError("Chamada renderStoryboard não encontrada.")

    return value.replace(
        call_marker,
        '''
    renderStoryboard(
        content
    );

    renderProductionPreview(
        productionPreview
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
    save(INDEX, inject_index(read(INDEX)))
    save(JAVASCRIPT, inject_js(read(JAVASCRIPT)))
    save(CSS, inject_css(read(CSS)))

    for path in (INDEX, JAVASCRIPT, CSS):
        if MARKER not in read(path):
            raise ValueError(f"Marcador ausente em {path}")

    print("PRODUCTION_PREVIEW_HTML=PASS")
    print("PRODUCTION_PREVIEW_JAVASCRIPT=PASS")
    print("PRODUCTION_PREVIEW_CSS=PASS")
    print("PUBLICATION_EXECUTION_ENABLED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
