from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "output/content_package.json"
MEDIA = ROOT / "output/media_acquisition_plan.json"
PUBLISHING = ROOT / "output/publishing_package.json"

OUT_DIR = ROOT / "output/assets/previews"
OUT_JSON = ROOT / "output/production_preview.json"
OUT_VIDEO = OUT_DIR / "production-preview.mp4"
OUT_VTT = OUT_DIR / "production-preview.vtt"
OUT_VOICE = OUT_DIR / "production-preview-voice.mp3"

WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION = 45
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "marin"

REGULAR_FONTS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
)
BOLD_FONTS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
)
ACCENTS = (
    (56, 189, 248),
    (34, 211, 238),
    (52, 211, 153),
    (250, 204, 21),
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro não encontrado: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} deve conter um objeto JSON.")
    return payload


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} deve ser um objeto.")
    return value


def sequence(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} deve ser uma lista.")
    return value


def text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} deve ser texto.")
    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        raise ValueError(f"{name} não pode estar vazio.")
    return normalized


def number(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(round(value))
    if isinstance(value, str):
        try:
            return int(round(float(value.strip())))
        except ValueError:
            return default
    return default


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], label: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{label} falhou.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def font(candidates: tuple[Path, ...], size: int) -> ImageFont.FreeTypeFont:
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    raise FileNotFoundError("Fonte de sistema compatível não encontrada.")


def wrap(
    draw: ImageDraw.ImageDraw,
    value: str,
    selected_font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in value.split():
        candidate = word if not current else current + " " + word
        box = draw.textbbox((0, 0), candidate, font=selected_font)
        if current and (box[2] - box[0]) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def fitted(
    draw: ImageDraw.ImageDraw,
    value: str,
    max_width: int,
    max_lines: int,
    max_size: int,
    min_size: int,
    bold: bool,
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    candidates = BOLD_FONTS if bold else REGULAR_FONTS
    for size in range(max_size, min_size - 1, -2):
        selected = font(candidates, size)
        lines = wrap(draw, value, selected, max_width)
        if len(lines) <= max_lines:
            return selected, lines, int(size * 1.25)
    selected = font(candidates, min_size)
    lines = wrap(draw, value, selected, max_width)[:max_lines]
    if lines:
        lines[-1] = lines[-1].rstrip(".,;:!?") + "…"
    return selected, lines, int(min_size * 1.25)


def draw_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    selected_font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    line_height: int,
    fill: tuple[int, int, int],
) -> int:
    current_y = y
    for line in lines:
        draw.text((x, current_y), line, font=selected_font, fill=fill)
        current_y += line_height
    return current_y


def gradient() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = image.load()
    top = (5, 12, 27)
    bottom = (13, 25, 44)
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        color = tuple(
            int(top[i] + (bottom[i] - top[i]) * ratio)
            for i in range(3)
        )
        for x in range(WIDTH):
            pixels[x, y] = color
    return image


def scene_image(
    scene_number: int,
    caption: str,
    narration: str,
    visual: str,
    duration: int,
    output: Path,
) -> None:
    accent = ACCENTS[(scene_number - 1) % len(ACCENTS)]
    image = gradient()

    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((620, 70, 1220, 670), fill=(*accent, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(95))
    image = Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(image)

    small_bold = font(BOLD_FONTS, 34)
    small = font(REGULAR_FONTS, 29)

    draw.rounded_rectangle((56, 58, 610, 124), radius=28, fill=accent)
    draw.text((82, 73), "PRODUCTION PREVIEW", font=small_bold, fill=(3, 10, 20))
    draw.text(
        (56, 164),
        f"CENA {scene_number}  ·  {duration}s",
        font=small_bold,
        fill=accent,
    )

    title_font, title_lines, title_height = fitted(
        draw, caption, 930, 4, 104, 60, True
    )
    title_bottom = draw_lines(
        draw, title_lines, title_font, 56, 260, title_height, (247, 250, 255)
    )

    rule_y = title_bottom + 34
    draw.rounded_rectangle((56, rule_y, 376, rule_y + 12), radius=6, fill=accent)

    body_font, body_lines, body_height = fitted(
        draw, narration, 930, 8, 53, 38, False
    )
    body_bottom = draw_lines(
        draw,
        body_lines,
        body_font,
        56,
        rule_y + 78,
        body_height,
        (217, 226, 240),
    )

    box_top = max(body_bottom + 58, 1320)
    draw.rounded_rectangle(
        (56, box_top, 1024, box_top + 330),
        radius=26,
        fill=(8, 17, 31),
        outline=(42, 58, 82),
        width=3,
    )
    draw.text((88, box_top + 32), "ORIENTAÇÃO VISUAL", font=small_bold, fill=accent)

    visual_font, visual_lines, visual_height = fitted(
        draw, visual, 904, 6, 34, 28, False
    )
    draw_lines(
        draw,
        visual_lines,
        visual_font,
        88,
        box_top + 98,
        visual_height,
        (172, 188, 214),
    )

    draw.text(
        (56, 1784),
        "NOT FOR PUBLICATION",
        font=small_bold,
        fill=(250, 204, 21),
    )
    draw.text(
        (680, 1788),
        "FOOTBALL SHORTS AI",
        font=small,
        fill=(124, 143, 171),
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, "PNG", optimize=True)


def silence(output: Path) -> None:
    run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", "1",
            "-c:a", "libmp3lame",
            "-q:a", "4",
            str(output),
        ],
        "Geração de silêncio",
    )


def tts(value: str, output: Path, model: str, voice: str) -> tuple[str, str | None]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        silence(output)
        return "fallback_silence", "OPENAI_API_KEY não configurada."

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=value[:4096],
            instructions=(
                "Fala em português europeu, pt-PT, com voz energética, "
                "clara e jornalística. Mantém dicção natural, sem sotaque "
                "brasileiro. Não acrescentes palavras."
            ),
            response_format="mp3",
            speed=1.08,
        ) as response:
            response.stream_to_file(output)

        if not output.is_file() or output.stat().st_size <= 0:
            raise RuntimeError("TTS não produziu áudio.")
        return "generated", None
    except Exception as exc:
        silence(output)
        return "fallback_silence", f"{type(exc).__name__}: {str(exc)[:220]}"


def duration(path: Path) -> float:
    result = run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        "Leitura de duração",
    )
    return float(result.stdout.strip())


def atempo(factor: float) -> str:
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("Fator de tempo inválido.")
    parts: list[str] = []
    remaining = factor
    while remaining > 2:
        parts.append("atempo=2.0")
        remaining /= 2
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append(f"atempo={remaining:.6f}")
    return ",".join(parts)


def normalize_audio(source: Path, target: Path, target_seconds: int) -> None:
    source_seconds = max(0.01, duration(source))
    factor = source_seconds / target_seconds
    audio_filter = (
        atempo(factor)
        + f",apad=pad_dur={target_seconds},atrim=duration={target_seconds},"
        + "aresample=44100"
    )
    run(
        [
            "ffmpeg", "-y",
            "-i", str(source),
            "-af", audio_filter,
            "-ac", "2",
            "-ar", "44100",
            "-c:a", "pcm_s16le",
            str(target),
        ],
        "Normalização de narração",
    )


def scene_video(
    image: Path,
    audio: Path,
    output: Path,
    scene_seconds: int,
) -> None:
    fade_out = max(0.1, scene_seconds - 0.35)
    video_filter = (
        "scale=1080:1920,"
        "zoompan=z='min(zoom+0.00045,1.045)':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        "d=1:s=1080x1920:fps=30,"
        "fade=t=in:st=0:d=0.30,"
        f"fade=t=out:st={fade_out:.2f}:d=0.30,"
        "format=yuv420p"
    )
    run(
        [
            "ffmpeg", "-y",
            "-loop", "1",
            "-framerate", str(FPS),
            "-i", str(image),
            "-i", str(audio),
            "-t", str(scene_seconds),
            "-vf", video_filter,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "160k",
            "-movflags", "+faststart",
            "-shortest",
            str(output),
        ],
        "Montagem de cena",
    )


def concat(paths: list[Path], output: Path, kind: str) -> None:
    with tempfile.TemporaryDirectory(prefix="preview-concat-") as tmp:
        listing = Path(tmp) / "concat.txt"
        listing.write_text(
            "\n".join(f"file '{path.resolve()}'" for path in paths) + "\n",
            encoding="utf-8",
        )
        if kind == "video":
            command = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(listing),
                "-c", "copy",
                "-movflags", "+faststart",
                str(output),
            ]
        else:
            command = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(listing),
                "-c:a", "libmp3lame",
                "-q:a", "3",
                str(output),
            ]
        run(command, f"Concatenação {kind}")


def timestamp(seconds: int) -> str:
    return f"00:00:{seconds:02d}.000"


def write_vtt(scenes: list[dict[str, Any]]) -> None:
    lines = ["WEBVTT", ""]
    cursor = 0
    for index, scene in enumerate(scenes, start=1):
        end = cursor + scene["duration_seconds"]
        lines.extend(
            [
                str(index),
                f"{timestamp(cursor)} --> {timestamp(end)}",
                scene["voiceover_text"],
                "",
            ]
        )
        cursor = end
    OUT_VTT.write_text("\n".join(lines), encoding="utf-8")


def validate(
    content: dict[str, Any],
    media: dict[str, Any],
    publishing: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source = mapping(content.get("source_topic"), "content.source_topic")
    scenes = [
        mapping(item, f"content.scenes[{index}]")
        for index, item in enumerate(sequence(content.get("scenes"), "content.scenes"))
    ]

    if len(scenes) != 4:
        raise ValueError("O preview exige exatamente quatro cenas.")
    if sum(number(scene.get("duration_seconds")) for scene in scenes) != DURATION:
        raise ValueError("O preview deve ter 45 segundos.")

    if media.get("publication_execution_enabled") is not False:
        raise ValueError("Media plan ativou publicação.")
    policy = mapping(media.get("policy"), "media.policy")
    if policy.get("unlicensed_media_allowed") is not False:
        raise ValueError("Media não licenciada foi permitida.")

    for index, raw in enumerate(sequence(media.get("scene_plans"), "media.scene_plans")):
        plan = mapping(raw, f"media.scene_plans[{index}]")
        if plan.get("selected_asset") is not None:
            raise ValueError("O preview gráfico não incorpora assets selecionados.")

    readiness = mapping(publishing.get("readiness"), "publishing.readiness")
    if publishing.get("status") != "draft":
        raise ValueError("Publishing deve permanecer draft.")
    if readiness.get("publication_execution_enabled") is not False:
        raise ValueError("Publicação foi ativada.")

    return source, scenes


def build(
    content: dict[str, Any],
    media: dict[str, Any],
    publishing: dict[str, Any],
) -> dict[str, Any]:
    for executable in ("ffmpeg", "ffprobe"):
        if shutil.which(executable) is None:
            raise RuntimeError(f"{executable} não está instalado.")

    source, source_scenes = validate(content, media, publishing)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    model = os.getenv("OPENAI_TTS_MODEL", TTS_MODEL).strip() or TTS_MODEL
    voice = os.getenv("OPENAI_TTS_VOICE", TTS_VOICE).strip() or TTS_VOICE

    manifest: list[dict[str, Any]] = []
    video_paths: list[Path] = []
    voice_paths: list[Path] = []
    statuses: list[str] = []
    errors: list[str] = []

    with tempfile.TemporaryDirectory(prefix="production-preview-") as tmp:
        work = Path(tmp)

        for index, scene in enumerate(source_scenes, start=1):
            seconds = number(scene.get("duration_seconds"))
            caption = text(scene.get("caption_text"), f"scene[{index}].caption")
            narration = text(
                scene.get("voiceover_segment"),
                f"scene[{index}].voiceover",
            )
            visual = text(
                scene.get("visual_instruction"),
                f"scene[{index}].visual",
            )

            image = work / f"scene-{index}.png"
            raw_audio = work / f"scene-{index}-raw.mp3"
            normalized_audio = work / f"scene-{index}.wav"
            video = work / f"scene-{index}.mp4"

            scene_image(index, caption, narration, visual, seconds, image)
            status, error = tts(narration, raw_audio, model, voice)
            normalize_audio(raw_audio, normalized_audio, seconds)
            scene_video(image, normalized_audio, video, seconds)

            statuses.append(status)
            if error:
                errors.append(f"Cena {index}: {error}")
            video_paths.append(video)
            voice_paths.append(raw_audio)
            manifest.append(
                {
                    "scene_number": index,
                    "duration_seconds": seconds,
                    "caption_text": caption,
                    "voiceover_text": narration,
                    "visual_mode": "abstract_governed_graphic",
                    "source_asset_used": False,
                    "tts_status": status,
                }
            )

        concat(video_paths, OUT_VIDEO, "video")
        concat(voice_paths, OUT_VOICE, "audio")

    write_vtt(manifest)

    final_duration = duration(OUT_VIDEO)
    if not 44.5 <= final_duration <= 45.5:
        raise ValueError("Duração final fora da tolerância.")

    if all(item == "generated" for item in statuses):
        tts_status = "generated"
    elif any(item == "generated" for item in statuses):
        tts_status = "partially_generated"
    else:
        tts_status = "fallback_silence"

    payload = {
        "preview_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_content_id": text(
            publishing.get("source_content_id"),
            "publishing.source_content_id",
        ),
        "source_title": text(source.get("title"), "content.source_topic.title"),
        "status": "ready_for_internal_review",
        "purpose": "production_orientation_preview",
        "format": {
            "container": "mp4",
            "video_codec": "h264",
            "audio_codec": "aac",
            "width": WIDTH,
            "height": HEIGHT,
            "aspect_ratio": "9:16",
            "fps": FPS,
            "duration_seconds": DURATION,
        },
        "voice": {
            "provider": "openai",
            "model": model,
            "voice": voice,
            "language": "pt-PT",
            "status": tts_status,
            "errors": errors,
        },
        "artifacts": {
            "video": {
                "output_path": str(OUT_VIDEO.relative_to(ROOT)),
                "public_path": "assets/generated/production-preview.mp4",
                "sha256": sha256(OUT_VIDEO),
                "byte_size": OUT_VIDEO.stat().st_size,
            },
            "captions": {
                "output_path": str(OUT_VTT.relative_to(ROOT)),
                "public_path": "assets/generated/production-preview.vtt",
                "sha256": sha256(OUT_VTT),
                "byte_size": OUT_VTT.stat().st_size,
                "language": "pt-PT",
            },
            "voice": {
                "output_path": str(OUT_VOICE.relative_to(ROOT)),
                "sha256": sha256(OUT_VOICE),
                "byte_size": OUT_VOICE.stat().st_size,
            },
        },
        "scenes": manifest,
        "governance": {
            "internal_review_only": True,
            "not_for_publication": True,
            "publication_execution_enabled": False,
            "browser_api_calls_enabled": False,
            "unlicensed_assets_used": False,
            "selected_source_assets_used": False,
            "synthetic_player_likenesses_generated": False,
            "club_logo_generation_enabled": False,
            "commercial_music_embedded": False,
            "third_party_tiktok_download_allowed": False,
            "watermark_removal_allowed": False,
        },
    }

    save_json(OUT_JSON, payload)
    return payload


def main() -> int:
    print("=" * 70)
    print("FOOTBALL-SHORTS-AI-0031C.5E")
    print("AI PRODUCTION PREVIEW GENERATOR")
    print("INTERNAL REVIEW ONLY")
    print("NOT FOR PUBLICATION")
    print("=" * 70)

    preview = build(
        load_json(CONTENT),
        load_json(MEDIA),
        load_json(PUBLISHING),
    )

    print(f"PRODUCTION_PREVIEW_STATUS={preview['status'].upper()}")
    print("PRODUCTION_PREVIEW_DURATION=45")
    print("PRODUCTION_PREVIEW_FORMAT=1080x1920_9:16")
    print(f"TTS_STATUS={preview['voice']['status'].upper()}")
    print("UNLICENSED_ASSETS_USED=NO")
    print("SYNTHETIC_PLAYER_LIKENESSES=NO")
    print("COMMERCIAL_MUSIC_EMBEDDED=NO")
    print("PUBLICATION_EXECUTION_ENABLED=NO")
    print("PRODUCTION_PREVIEW_BUILD=PASS")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
