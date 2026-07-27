from __future__ import annotations

import json
import shutil
from pathlib import Path


SOURCE = Path(
    "output/dashboard_model.json"
)

TARGET = Path(
    "dashboard/data/dashboard_model.json"
)


REQUIRED_KEYS = {

    "generated_at",

    "channel",

    "top_title",

    "top_hook",

    "viral_probability",

    "metrics",

    "hooks",

    "storyboard",

    "ranking",

}



def load_json(path: Path) -> dict:

    if not path.exists():

        raise FileNotFoundError(
            f"Ficheiro não encontrado: {path}"
        )


    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )



def validate_dashboard_model(
    payload: dict,
) -> None:


    if not isinstance(payload, dict):

        raise ValueError(
            "Dashboard model deve ser um objeto JSON."
        )


    missing = (
        REQUIRED_KEYS
        -
        payload.keys()
    )


    if missing:

        raise ValueError(
            f"Dashboard model incompleto: {sorted(missing)}"
        )


    if not isinstance(
        payload["ranking"],
        list,
    ):

        raise ValueError(
            "ranking deve ser uma lista."
        )


    priorities = [

        item.get("priority")

        for item in payload["ranking"]

    ]


    expected = list(
        range(
            1,
            len(priorities) + 1,
        )
    )


    if priorities != expected:

        raise ValueError(
            "Ranking inválido: prioridades devem ser sequenciais."
        )



def sync_dashboard() -> int:


    print("=" * 70)

    print(
        "FOOTBALL SHORTS AI"
    )

    print(
        "DASHBOARD DATA SYNCHRONIZATION"
    )

    print("=" * 70)


    payload = load_json(
        SOURCE
    )


    validate_dashboard_model(
        payload
    )


    TARGET.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    shutil.copyfile(
        SOURCE,
        TARGET,
    )


    print(
        "DASHBOARD SYNC PASS"
    )

    print(
        f"Source: {SOURCE}"
    )

    print(
        f"Target: {TARGET}"
    )

    print(
        f"Top Short: {payload['top_title']}"
    )

    print(
        f"Ranking items: {len(payload['ranking'])}"
    )

    print("=" * 70)


    return 0



def main() -> int:

    return sync_dashboard()



if __name__ == "__main__":

    raise SystemExit(
        main()
    )
