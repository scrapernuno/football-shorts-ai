from collect_news import collect_all_news
from score_news import score_news
from select_topics import select_unique_topics
from build_prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)

news = collect_all_news()
ranked = score_news(news)
topics = select_unique_topics(ranked)

print("=" * 80)
print("SYSTEM PROMPT")
print("=" * 80)
print()
print(SYSTEM_PROMPT)

print()
print("=" * 80)
print("USER PROMPT")
print("=" * 80)
print()
print(build_user_prompt(topics))
