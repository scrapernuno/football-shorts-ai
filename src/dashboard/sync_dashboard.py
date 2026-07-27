from __future__ import annotations

import json
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



def load_json(
    path: Path,
) -> dict:

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


    if not isinstance(
        payload,
        dict,
    ):

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


    if len(payload["ranking"]) == 0:

        raise ValueError(
            "Ranking vazio."
        )



def normalize_ranking(
    payload: dict,
) -> None:


    ranking = payload["ranking"]


    for item in ranking:

        if not isinstance(
            item,
            dict,
        ):

            raise ValueError(
                "Ranking item inválido."
            )


        if "title" not in item:

            raise ValueError(
                "Ranking item sem title."
            )


    ranking.sort(
        key=lambda item: item.get(
            "viral_probability",
            0,
        ),
        reverse=True,
    )


    for index, item in enumerate(
        ranking,
        start=1,
    ):

        item["priority"] = index


    payload["ranking"] = ranking



def save_dashboard(
    payload: dict,
) -> None:


    TARGET.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    TARGET.write_text(

        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),

        encoding="utf-8",
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


    normalize_ranking(
        payload
    )


    save_dashboard(
        payload
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
