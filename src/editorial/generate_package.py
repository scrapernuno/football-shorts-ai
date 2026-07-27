def normalize_storyboard() -> dict:

    return {

        "estimated_duration_seconds": 45,

        "required_clip_count": 5,

        "scenes": [

            {
                "scene_number": 1,
                "start_second": 0,
                "end_second": 3,

                "asset": asset(
                    "Opening football clip",
                    "football viral opening moment",
                ),

                "camera_movement": "Fast zoom",
                "editing_pace": "Very fast",
                "sound_effect": "Impact hit",

                "subtitle": (
                    "Atenção: algo incrível aconteceu"
                ),

                "subtitle_style": "Bold dynamic",

                "visual_description": (
                    "Momento inicial mais forte do tema"
                ),

                "visual_type": "video",

                "voiceover": (
                    "Hook inicial para prender o espectador"
                ),

                "transition": "Fast cut",
            },


            {
                "scene_number": 2,
                "start_second": 3,
                "end_second": 15,

                "asset": asset(
                    "Player team footage",
                    "football player team footage",
                ),

                "camera_movement": "Tracking movement",
                "editing_pace": "Fast",
                "sound_effect": "Crowd reaction",

                "subtitle": (
                    "O contexto desta história"
                ),

                "subtitle_style": "Modern captions",

                "visual_description": (
                    "Clips que explicam a situação"
                ),

                "visual_type": "video",

                "voiceover": (
                    "Explicação rápida do acontecimento"
                ),

                "transition": "Dynamic cut",
            },


            {
                "scene_number": 3,
                "start_second": 15,
                "end_second": 30,

                "asset": asset(
                    "Main highlight clip",
                    "football main highlight action",
                ),

                "camera_movement": "Slow motion",
                "editing_pace": "Dynamic",
                "sound_effect": "Cinematic impact",

                "subtitle": (
                    "O momento decisivo"
                ),

                "subtitle_style": "High contrast",

                "visual_description": (
                    "A jogada ou momento principal"
                ),

                "visual_type": "video",

                "voiceover": (
                    "A parte que mudou tudo"
                ),

                "transition": "Speed ramp",
            },


            {
                "scene_number": 4,
                "start_second": 30,
                "end_second": 40,

                "asset": asset(
                    "Reaction statistics footage",
                    "football fans reaction statistics",
                ),

                "camera_movement": "Pan and zoom",
                "editing_pace": "Medium",
                "sound_effect": "Trending sound",

                "subtitle": (
                    "A reação dos fãs"
                ),

                "subtitle_style": "Social media style",

                "visual_description": (
                    "Reações, comentários e dados"
                ),

                "visual_type": "video",

                "voiceover": (
                    "Porque este momento está a gerar debate"
                ),

                "transition": "Zoom",
            },


            {
                "scene_number": 5,
                "start_second": 40,
                "end_second": 45,

                "asset": asset(
                    "Final football celebration video",
                    "football final celebration",
                ),

                "camera_movement": "Slow zoom out",
                "editing_pace": "Slow finish",
                "sound_effect": "Outro sound",

                "subtitle": (
                    "Qual é a tua opinião?"
                ),

                "subtitle_style": "Call to action",

                "visual_description": (
                    "Fecho do Short com chamada à interação"
                ),

                "visual_type": "video",

                "voiceover": (
                    "Comenta e segue para mais histórias"
                ),

                "transition": "Fade out",
            },

        ],

    }
