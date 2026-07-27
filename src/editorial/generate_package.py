def asset(
    description: str,
    query: str,
) -> dict:

    return {

        "asset_type": "VIDEO",

        "description": description,

        "copyright_note": (
            "Utilizar apenas material autorizado, "
            "licenciado ou permitido para publicação."
        ),

        "fallback_description": description,

        "preferred_source": (
            "Official club channels, "
            "league channels and licensed footage providers"
        ),

        "search_queries": [

            query,

            description,

        ],

    }
