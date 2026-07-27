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



def main() -> int:

    if not SOURCE.exists():

        raise FileNotFoundError(
            f"Dashboard source missing: {SOURCE}"
        )


    TARGET.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    shutil.copyfile(
        SOURCE,
        TARGET,
    )


    payload = json.loads(
        TARGET.read_text(
            encoding="utf-8"
        )
    )


    required = {

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


    missing = (
        required
        -
        payload.keys()
    )


    if missing:

        raise ValueError(
            f"Dashboard model inválido: {missing}"
        )


    print(
        "=" * 70
    )

    print(
        "DASHBOARD SYNC PASS"
    )

    print(
        "=" * 70
    )

    print(
        f"Top Short: {payload['top_title']}"
    )


    return 0



if __name__ == "__main__":

    raise SystemExit(
        main()
    )
