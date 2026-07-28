from __future__ import annotations

import hashlib
import json
import re
import struct
import unicodedata
import zlib

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[2]

CONTENT_SOURCE = (
    ROOT
    / "output"
    / "content_package.json"
)

DASHBOARD_SOURCE = (
    ROOT
    / "output"
    / "dashboard_model.json"
)

EVIDENCE_OUTPUT = (
    ROOT
    / "output"
    / "publishing_evidence.json"
)

OUTPUT_THUMBNAIL_DIRECTORY = (
    ROOT
    / "output"
    / "assets"
    / "thumbnails"
)

PUBLIC_THUMBNAIL_DIRECTORY = (
    ROOT
    / "dashboard"
    / "assets"
    / "generated"
)


EVIDENCE_VERSION = "1.0"

THUMBNAIL_WIDTH = 1280

THUMBNAIL_HEIGHT = 720

THUMBNAIL_MIME_TYPE = "image/png"


FONT: dict[str, tuple[str, ...]] = {
    "A": (
        "01110",
        "10001",
        "10001",
        "11111",
        "10001",
        "10001",
        "10001",
    ),
    "B": (
        "11110",
        "10001",
        "10001",
        "11110",
        "10001",
        "10001",
        "11110",
    ),
    "C": (
        "01111",
        "10000",
        "10000",
        "10000",
        "10000",
        "10000",
        "01111",
    ),
    "D": (
        "11110",
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "11110",
    ),
    "E": (
        "11111",
        "10000",
        "10000",
        "11110",
        "10000",
        "10000",
        "11111",
    ),
    "F": (
        "11111",
        "10000",
        "10000",
        "11110",
        "10000",
        "10000",
        "10000",
    ),
    "G": (
        "01111",
        "10000",
        "10000",
        "10111",
        "10001",
        "10001",
        "01111",
    ),
    "H": (
        "10001",
        "10001",
        "10001",
        "11111",
        "10001",
        "10001",
        "10001",
    ),
    "I": (
        "11111",
        "00100",
        "00100",
        "00100",
        "00100",
        "00100",
        "11111",
    ),
    "J": (
        "00111",
        "00010",
        "00010",
        "00010",
        "10010",
        "10010",
        "01100",
    ),
    "K": (
        "10001",
        "10010",
        "10100",
        "11000",
        "10100",
        "10010",
        "10001",
    ),
    "L": (
        "10000",
        "10000",
        "10000",
        "10000",
        "10000",
        "10000",
        "11111",
    ),
    "M": (
        "10001",
        "11011",
        "10101",
        "10101",
        "10001",
        "10001",
        "10001",
    ),
    "N": (
        "10001",
        "11001",
        "10101",
        "10011",
        "10001",
        "10001",
        "10001",
    ),
    "O": (
        "01110",
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "01110",
    ),
    "P": (
        "11110",
        "10001",
        "10001",
        "11110",
        "10000",
        "10000",
        "10000",
    ),
    "Q": (
        "01110",
        "10001",
        "10001",
        "10001",
        "10101",
        "10010",
        "01101",
    ),
    "R": (
        "11110",
        "10001",
        "10001",
        "11110",
        "10100",
        "10010",
        "10001",
    ),
    "S": (
        "01111",
        "10000",
        "10000",
        "01110",
        "00001",
        "00001",
        "11110",
    ),
    "T": (
        "11111",
        "00100",
        "00100",
        "00100",
        "00100",
        "00100",
        "00100",
    ),
    "U": (
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "01110",
    ),
    "V": (
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "01010",
        "00100",
    ),
    "W": (
        "10001",
        "10001",
        "10001",
        "10101",
        "10101",
        "11011",
        "10001",
    ),
    "X": (
        "10001",
        "10001",
        "01010",
        "00100",
        "01010",
        "10001",
        "10001",
    ),
    "Y": (
        "10001",
        "10001",
        "01010",
        "00100",
        "00100",
        "00100",
        "00100",
    ),
    "Z": (
        "11111",
        "00001",
        "00010",
        "00100",
        "01000",
        "10000",
        "11111",
    ),
    "0": (
        "01110",
        "10001",
        "10011",
        "10101",
        "11001",
        "10001",
        "01110",
    ),
    "1": (
        "00100",
        "01100",
        "00100",
        "00100",
        "00100",
        "00100",
        "01110",
    ),
    "2": (
        "01110",
        "10001",
        "00001",
        "00010",
        "00100",
        "01000",
        "11111",
    ),
    "3": (
        "11110",
        "00001",
        "00001",
        "01110",
        "00001",
        "00001",
        "11110",
    ),
    "4": (
        "00010",
        "00110",
        "01010",
        "10010",
        "11111",
        "00010",
        "00010",
    ),
    "5": (
        "11111",
        "10000",
        "10000",
        "11110",
        "00001",
        "00001",
        "11110",
    ),
    "6": (
        "01110",
        "10000",
        "10000",
        "11110",
        "10001",
        "10001",
        "01110",
    ),
    "7": (
        "11111",
        "00001",
        "00010",
        "00100",
        "01000",
        "01000",
        "01000",
    ),
    "8": (
        "01110",
        "10001",
        "10001",
        "01110",
        "10001",
        "10001",
        "01110",
    ),
    "9": (
        "01110",
        "10001",
        "10001",
        "01111",
        "00001",
        "00001",
        "01110",
    ),
    "%": (
        "11001",
        "11010",
        "00100",
        "01000",
        "10110",
        "00110",
        "00000",
    ),
    "#": (
        "01010",
        "11111",
        "01010",
        "01010",
        "11111",
        "01010",
        "00000",
    ),
    "-": (
        "00000",
        "00000",
        "00000",
        "11111",
        "00000",
        "00000",
        "00000",
    ),
    "?": (
        "01110",
        "10001",
        "00001",
        "00010",
        "00100",
        "00000",
        "00100",
    ),
    "!": (
        "00100",
        "00100",
        "00100",
        "00100",
        "00100",
        "00000",
        "00100",
    ),
    ".": (
        "00000",
        "00000",
        "00000",
        "00000",
        "00000",
        "00110",
        "00110",
    ),
    ":": (
        "00000",
        "00110",
        "00110",
        "00000",
        "00110",
        "00110",
        "00000",
    ),
    "/": (
        "00001",
        "00010",
        "00100",
        "01000",
        "10000",
        "00000",
        "00000",
    ),
    "'": (
        "00100",
        "00100",
        "00000",
        "00000",
        "00000",
        "00000",
        "00000",
    ),
    " ": (
        "00000",
        "00000",
        "00000",
        "00000",
        "00000",
        "00000",
        "00000",
    ),
}


def load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Ficheiro não encontrado: {path}"
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

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            f"{path} deve conter um objeto JSON."
        )

    return payload


def require_mapping(
    value: object,
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"{field_name} deve ser um objeto JSON."
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
            f"{field_name} deve ser uma lista JSON."
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
            f"{field_name} não pode estar vazio."
        )

    return normalized


def slugify(
    value: str,
) -> str:
    normalized = (
        unicodedata.normalize(
            "NFKD",
            value,
        )
        .encode(
            "ascii",
            "ignore",
        )
        .decode(
            "ascii"
        )
        .lower()
    )

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        normalized,
    ).strip("-")

    return (
        slug
        or
        "football-short"
    )


def normalize_display_text(
    value: str,
) -> str:
    normalized = (
        unicodedata.normalize(
            "NFKD",
            value,
        )
        .encode(
            "ascii",
            "ignore",
        )
        .decode(
            "ascii"
        )
        .upper()
    )

    return "".join(
        character
        if character in FONT
        else " "
        for character in normalized
    )


def canonical_json_bytes(
    payload: dict[str, Any],
) -> bytes:
    return json.dumps(
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


def sha256_bytes(
    payload: bytes,
) -> str:
    return hashlib.sha256(
        payload
    ).hexdigest()


def sha256_file(
    path: Path,
) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def identity_payload(
    content: dict[str, Any],
) -> dict[str, Any]:
    source_topic = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    return {
        "title":
            require_text(
                source_topic.get(
                    "title"
                ),
                "content.source_topic.title",
            ),

        "hook":
            require_text(
                source_topic.get(
                    "hook"
                ),
                "content.source_topic.hook",
            ),

        "priority":
            source_topic.get(
                "priority"
            ),

        "viral_probability":
            source_topic.get(
                "viral_probability"
            ),

        "generated_at":
            content.get(
                "generated_at"
            ),
    }


def png_chunk(
    chunk_type: bytes,
    data: bytes,
) -> bytes:
    return (
        struct.pack(
            ">I",
            len(data),
        )
        +
        chunk_type
        +
        data
        +
        struct.pack(
            ">I",
            zlib.crc32(
                chunk_type
                +
                data
            )
            &
            0xFFFFFFFF,
        )
    )


def set_pixel(
    pixels: bytearray,
    *,
    width: int,
    height: int,
    x: int,
    y: int,
    color: tuple[
        int,
        int,
        int,
    ],
) -> None:
    if (
        x < 0
        or
        y < 0
        or
        x >= width
        or
        y >= height
    ):
        return

    index = (
        (
            y
            *
            width
        )
        +
        x
    ) * 3

    pixels[
        index
        :
        index + 3
    ] = bytes(
        color
    )


def fill_rectangle(
    pixels: bytearray,
    *,
    width: int,
    height: int,
    x: int,
    y: int,
    rectangle_width: int,
    rectangle_height: int,
    color: tuple[
        int,
        int,
        int,
    ],
) -> None:
    start_x = max(
        0,
        x,
    )

    start_y = max(
        0,
        y,
    )

    end_x = min(
        width,
        x
        +
        rectangle_width,
    )

    end_y = min(
        height,
        y
        +
        rectangle_height,
    )

    if (
        start_x >= end_x
        or
        start_y >= end_y
    ):
        return

    row = bytes(
        color
    ) * (
        end_x
        -
        start_x
    )

    for current_y in range(
        start_y,
        end_y,
    ):
        start = (
            (
                current_y
                *
                width
            )
            +
            start_x
        ) * 3

        pixels[
            start
            :
            start
            +
            len(
                row
            )
        ] = row


def fill_circle(
    pixels: bytearray,
    *,
    width: int,
    height: int,
    center_x: int,
    center_y: int,
    radius: int,
    color: tuple[
        int,
        int,
        int,
    ],
) -> None:
    radius_squared = (
        radius
        *
        radius
    )

    for y in range(
        center_y
        -
        radius,
        center_y
        +
        radius
        +
        1,
    ):
        for x in range(
            center_x
            -
            radius,
            center_x
            +
            radius
            +
            1,
        ):
            dx = (
                x
                -
                center_x
            )

            dy = (
                y
                -
                center_y
            )

            if (
                dx
                *
                dx
                +
                dy
                *
                dy
                <=
                radius_squared
            ):
                set_pixel(
                    pixels,
                    width=width,
                    height=height,
                    x=x,
                    y=y,
                    color=color,
                )


def draw_character(
    pixels: bytearray,
    *,
    width: int,
    height: int,
    character: str,
    x: int,
    y: int,
    scale: int,
    color: tuple[
        int,
        int,
        int,
    ],
) -> None:
    glyph = FONT.get(
        character,
        FONT[" "],
    )

    for row_index, row in enumerate(
        glyph
    ):
        for column_index, value in enumerate(
            row
        ):
            if value != "1":
                continue

            fill_rectangle(
                pixels,
                width=width,
                height=height,
                x=(
                    x
                    +
                    column_index
                    *
                    scale
                ),
                y=(
                    y
                    +
                    row_index
                    *
                    scale
                ),
                rectangle_width=scale,
                rectangle_height=scale,
                color=color,
            )


def draw_text(
    pixels: bytearray,
    *,
    width: int,
    height: int,
    text: str,
    x: int,
    y: int,
    scale: int,
    color: tuple[
        int,
        int,
        int,
    ],
) -> None:
    cursor = x

    for character in text:
        draw_character(
            pixels,
            width=width,
            height=height,
            character=character,
            x=cursor,
            y=y,
            scale=scale,
            color=color,
        )

        cursor += (
            6
            *
            scale
        )


def wrap_text(
    text: str,
    *,
    maximum_characters: int,
    maximum_lines: int,
) -> list[str]:
    words = [
        word
        for word in text.split()
        if word
    ]

    lines: list[str] = []

    current = ""

    for word in words:
        candidate = (
            word
            if not current
            else
            current
            +
            " "
            +
            word
        )

        if (
            len(
                candidate
            )
            <=
            maximum_characters
        ):
            current = candidate
            continue

        if current:
            lines.append(
                current
            )

        current = word

        if (
            len(
                lines
            )
            >=
            maximum_lines
        ):
            break

    if (
        current
        and
        len(
            lines
        )
        <
        maximum_lines
    ):
        lines.append(
            current
        )

    if not lines:
        lines = [
            "FOOTBALL SHORT"
        ]

    return lines[
        :maximum_lines
    ]


def create_thumbnail_png(
    *,
    title: str,
    viral_probability: int,
    identity_sha256: str,
) -> bytes:
    width = THUMBNAIL_WIDTH

    height = THUMBNAIL_HEIGHT

    pixels = bytearray(
        width
        *
        height
        *
        3
    )

    seed = int(
        identity_sha256[
            :8
        ],
        16,
    )

    for y in range(
        height
    ):
        vertical = (
            y
            /
            max(
                1,
                height
                -
                1,
            )
        )

        red = int(
            5
            +
            8
            *
            vertical
        )

        green = int(
            12
            +
            16
            *
            vertical
        )

        blue = int(
            27
            +
            24
            *
            vertical
        )

        row = bytes(
            (
                red,
                green,
                blue,
            )
        ) * width

        start = (
            y
            *
            width
            *
            3
        )

        pixels[
            start
            :
            start
            +
            len(
                row
            )
        ] = row

    accent_color = (
        34
        +
        seed
        %
        20,
        226,
        170,
    )

    secondary_color = (
        55,
        205,
        255,
    )

    fill_rectangle(
        pixels,
        width=width,
        height=height,
        x=0,
        y=0,
        rectangle_width=24,
        rectangle_height=height,
        color=accent_color,
    )

    fill_rectangle(
        pixels,
        width=width,
        height=height,
        x=70,
        y=90,
        rectangle_width=8,
        rectangle_height=500,
        color=secondary_color,
    )

    fill_circle(
        pixels,
        width=width,
        height=height,
        center_x=1090,
        center_y=200,
        radius=150,
        color=(
            12,
            44,
            67,
        ),
    )

    fill_circle(
        pixels,
        width=width,
        height=height,
        center_x=1090,
        center_y=200,
        radius=125,
        color=(
            6,
            18,
            35,
        ),
    )

    fill_rectangle(
        pixels,
        width=width,
        height=height,
        x=82,
        y=545,
        rectangle_width=820,
        rectangle_height=8,
        color=accent_color,
    )

    draw_text(
        pixels,
        width=width,
        height=height,
        text=(
            "FOOTBALL SHORTS AI"
        ),
        x=100,
        y=78,
        scale=4,
        color=secondary_color,
    )

    normalized_title = normalize_display_text(
        title
    )

    lines = wrap_text(
        normalized_title,
        maximum_characters=19,
        maximum_lines=3,
    )

    title_y = 180

    for line in lines:
        draw_text(
            pixels,
            width=width,
            height=height,
            text=line,
            x=100,
            y=title_y,
            scale=9,
            color=(
                245,
                249,
                255,
            ),
        )

        title_y += 90

    draw_text(
        pixels,
        width=width,
        height=height,
        text=(
            f"{max(0, min(100, viral_probability))}%"
        ),
        x=1000,
        y=165,
        scale=10,
        color=accent_color,
    )

    draw_text(
        pixels,
        width=width,
        height=height,
        text="VIRAL",
        x=1025,
        y=280,
        scale=5,
        color=secondary_color,
    )

    draw_text(
        pixels,
        width=width,
        height=height,
        text="@DINAMEGAZ2014",
        x=100,
        y=610,
        scale=4,
        color=(
            170,
            188,
            214,
        ),
    )

    raw = bytearray()

    row_size = (
        width
        *
        3
    )

    for y in range(
        height
    ):
        raw.append(
            0
        )

        start = (
            y
            *
            row_size
        )

        raw.extend(
            pixels[
                start
                :
                start
                +
                row_size
            ]
        )

    signature = (
        b"\x89PNG\r\n\x1a\n"
    )

    header = struct.pack(
        ">IIBBBBB",
        width,
        height,
        8,
        2,
        0,
        0,
        0,
    )

    return (
        signature
        +
        png_chunk(
            b"IHDR",
            header,
        )
        +
        png_chunk(
            b"IDAT",
            zlib.compress(
                bytes(
                    raw
                ),
                level=9,
            ),
        )
        +
        png_chunk(
            b"IEND",
            b"",
        )
    )


def write_bytes_atomically(
    path: Path,
    payload: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        path.with_suffix(
            path.suffix
            +
            ".tmp"
        )
    )

    temporary_path.write_bytes(
        payload
    )

    temporary_path.replace(
        path
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
        path.with_suffix(
            path.suffix
            +
            ".tmp"
        )
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


def build_rights_review(
    content: dict[str, Any],
) -> dict[str, Any]:
    scenes = require_list(
        content.get(
            "scenes"
        ),
        "content.scenes",
    )

    items: list[
        dict[str, Any]
    ] = []

    for index, raw_scene in enumerate(
        scenes,
        start=1,
    ):
        scene = require_mapping(
            raw_scene,
            (
                "content.scenes"
                f"[{index - 1}]"
            ),
        )

        scene_number = scene.get(
            "scene_number",
            index,
        )

        asset_reference = require_text(
            scene.get(
                "asset_reference"
            ),
            (
                "content.scenes"
                f"[{index - 1}]"
                ".asset_reference"
            ),
        )

        items.append(
            {
                "scene_number":
                    scene_number,

                "asset_reference":
                    asset_reference,

                "review_status":
                    "unreviewed",

                "source_reference":
                    None,

                "license_reference":
                    None,

                "reviewed_by":
                    None,

                "reviewed_at":
                    None,
            }
        )

    approved_items = sum(
        1
        for item in items
        if item[
            "review_status"
        ]
        ==
        "approved"
    )

    return {
        "status":
            (
                "approved"
                if items
                and
                approved_items
                ==
                len(
                    items
                )
                else
                "pending"
            ),

        "total_items":
            len(
                items
            ),

        "approved_items":
            approved_items,

        "items":
            items,

        "approval_evidence_reference":
            None,
    }


def build_final_approval(
    *,
    content_id: str,
    identity_sha256: str,
) -> dict[str, Any]:
    return {
        "status":
            "pending",

        "approved":
            False,

        "content_id":
            content_id,

        "content_identity_sha256":
            identity_sha256,

        "approved_by":
            None,

        "approved_at":
            None,

        "evidence_reference":
            None,
    }


def validate_evidence(
    payload: dict[str, Any],
) -> None:
    required = {
        "evidence_version",
        "generated_at",
        "content_identity",
        "thumbnail",
        "rights_review",
        "final_approval",
        "publication_execution_enabled",
    }

    missing = (
        required
        -
        payload.keys()
    )

    if missing:
        raise ValueError(
            "Publishing Evidence incompleto: "
            f"{sorted(missing)}"
        )

    identity = require_mapping(
        payload.get(
            "content_identity"
        ),
        "evidence.content_identity",
    )

    require_text(
        identity.get(
            "content_id"
        ),
        "evidence.content_identity.content_id",
    )

    require_text(
        identity.get(
            "sha256"
        ),
        "evidence.content_identity.sha256",
    )

    thumbnail = require_mapping(
        payload.get(
            "thumbnail"
        ),
        "evidence.thumbnail",
    )

    if thumbnail.get(
        "status"
    ) != "ready":
        raise ValueError(
            "A thumbnail produzida deve "
            "ficar ready."
        )

    output_path = ROOT / require_text(
        thumbnail.get(
            "artifact_path"
        ),
        "evidence.thumbnail.artifact_path",
    )

    public_path = ROOT / "dashboard" / require_text(
        thumbnail.get(
            "public_path"
        ),
        "evidence.thumbnail.public_path",
    )

    for path in (
        output_path,
        public_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(
                f"Thumbnail em falta: {path}"
            )

    expected_hash = require_text(
        thumbnail.get(
            "sha256"
        ),
        "evidence.thumbnail.sha256",
    )

    for path in (
        output_path,
        public_path,
    ):
        observed_hash = sha256_file(
            path
        )

        if observed_hash != expected_hash:
            raise ValueError(
                "Hash da thumbnail inconsistente: "
                f"{path}"
            )

    if thumbnail.get(
        "width"
    ) != THUMBNAIL_WIDTH:
        raise ValueError(
            "Largura de thumbnail inválida."
        )

    if thumbnail.get(
        "height"
    ) != THUMBNAIL_HEIGHT:
        raise ValueError(
            "Altura de thumbnail inválida."
        )

    rights_review = require_mapping(
        payload.get(
            "rights_review"
        ),
        "evidence.rights_review",
    )

    if rights_review.get(
        "status"
    ) not in {
        "pending",
        "approved",
    }:
        raise ValueError(
            "rights_review.status inválido."
        )

    final_approval = require_mapping(
        payload.get(
            "final_approval"
        ),
        "evidence.final_approval",
    )

    if final_approval.get(
        "status"
    ) not in {
        "pending",
        "approved",
    }:
        raise ValueError(
            "final_approval.status inválido."
        )

    if payload.get(
        "publication_execution_enabled"
    ) is not False:
        raise ValueError(
            "A publicação deve permanecer "
            "desativada."
        )


def main() -> int:
    print("=" * 70)

    print(
        "FOOTBALL-SHORTS-AI-0031C.3"
    )

    print(
        "THUMBNAIL ASSET AND "
        "APPROVAL EVIDENCE CONTRACT"
    )

    print(
        "NO PUBLICATION EXECUTION"
    )

    print("=" * 70)

    content = load_json(
        CONTENT_SOURCE
    )

    dashboard = load_json(
        DASHBOARD_SOURCE
    )

    identity_source = identity_payload(
        content
    )

    title = require_text(
        identity_source.get(
            "title"
        ),
        "identity.title",
    )

    content_id = slugify(
        title
    )

    identity_sha256 = sha256_bytes(
        canonical_json_bytes(
            identity_source
        )
    )

    viral_probability = dashboard.get(
        "viral_probability",
        identity_source.get(
            "viral_probability",
            0,
        ),
    )

    if (
        not isinstance(
            viral_probability,
            int,
        )
        or
        isinstance(
            viral_probability,
            bool,
        )
    ):
        viral_probability = 0

    thumbnail_bytes = create_thumbnail_png(
        title=title,
        viral_probability=viral_probability,
        identity_sha256=identity_sha256,
    )

    filename = (
        content_id
        +
        "-thumbnail.png"
    )

    output_thumbnail = (
        OUTPUT_THUMBNAIL_DIRECTORY
        /
        filename
    )

    public_thumbnail = (
        PUBLIC_THUMBNAIL_DIRECTORY
        /
        filename
    )

    write_bytes_atomically(
        output_thumbnail,
        thumbnail_bytes,
    )

    write_bytes_atomically(
        public_thumbnail,
        thumbnail_bytes,
    )

    thumbnail_sha256 = sha256_bytes(
        thumbnail_bytes
    )

    evidence = {
        "evidence_version":
            EVIDENCE_VERSION,

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "content_identity":
            {
                "content_id":
                    content_id,

                "title":
                    title,

                "sha256":
                    identity_sha256,

                "source_generated_at":
                    identity_source.get(
                        "generated_at"
                    ),
            },

        "thumbnail":
            {
                "status":
                    "ready",

                "artifact_path":
                    str(
                        output_thumbnail.relative_to(
                            ROOT
                        )
                    ),

                "public_path":
                    str(
                        public_thumbnail.relative_to(
                            ROOT
                            /
                            "dashboard"
                        )
                    ),

                "sha256":
                    thumbnail_sha256,

                "width":
                    THUMBNAIL_WIDTH,

                "height":
                    THUMBNAIL_HEIGHT,

                "mime_type":
                    THUMBNAIL_MIME_TYPE,

                "byte_size":
                    len(
                        thumbnail_bytes
                    ),

                "generator":
                    (
                        "football-shorts-ai/"
                        "deterministic-png-v1"
                    ),
            },

        "rights_review":
            build_rights_review(
                content
            ),

        "final_approval":
            build_final_approval(
                content_id=content_id,
                identity_sha256=identity_sha256,
            ),

        "publication_execution_enabled":
            False,
    }

    write_json_atomically(
        EVIDENCE_OUTPUT,
        evidence,
    )

    validate_evidence(
        evidence
    )

    print(
        "PUBLISHING_EVIDENCE_BUILD=PASS"
    )

    print(
        f"CONTENT_ID={content_id}"
    )

    print(
        "THUMBNAIL_STATUS=READY"
    )

    print(
        f"THUMBNAIL_SHA256="
        f"{thumbnail_sha256}"
    )

    print(
        f"THUMBNAIL_SIZE="
        f"{THUMBNAIL_WIDTH}x"
        f"{THUMBNAIL_HEIGHT}"
    )

    print(
        "RIGHTS_REVIEW_STATUS="
        f"{evidence['rights_review']['status'].upper()}"
    )

    print(
        "FINAL_APPROVAL_STATUS="
        f"{evidence['final_approval']['status'].upper()}"
    )

    print(
        "PUBLICATION_EXECUTION_ENABLED=NO"
    )

    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
