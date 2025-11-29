#!/usr/bin/env python3
"""
Matcher phase: Match article categories to user preferences and calculate relevance scores.

This module:
1. Iterates over users and their selected categories
2. Finds articles with matching categories
3. Stores matched categories in user_articles
4. Calculates relevance scores using LLM
"""

import asyncio
import json
import os

import aiosqlite
from dotenv import load_dotenv
from think import LLM, LLMQuery

load_dotenv()

DB_PATH = os.environ.get("DB_PATH", "../data/db.sqlite")


class RelevanceScore(LLMQuery):
    """Determine how relevant an article is to a user based on their description.

    USER DESCRIPTION (what the user is interested in):
    {{ user_description }}

    ARTICLE SUMMARY:
    {{ article_summary }}

    Based on the user's interests and the article summary, provide a relevance score.

    Score guidelines:
    - 0.0 = Completely irrelevant, no connection to user interests
    - 1.0-2.0 = Tangentially related, might be of minor interest
    - 2.5-3.5 = Moderately relevant, covers topics the user cares about
    - 4.0-4.5 = Highly relevant, directly addresses user interests
    - 5.0 = Perfect match, exactly what the user is looking for

    Return only the numerical score.
    """

    relevance: float


async def get_users_with_categories(db: aiosqlite.Connection) -> list[dict]:
    """
    Fetch all users that have categories set.

    Returns:
        List of user dicts with id, categories, and custom_description
    """
    cursor = await db.execute(
        """
        SELECT id, categories, custom_description
        FROM users
        WHERE categories IS NOT NULL AND categories != ''
        """
    )
    rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "categories": [c.strip() for c in row[1].split(",") if c.strip()],
            "custom_description": row[2] or "",
        }
        for row in rows
    ]


async def get_articles_with_categories(db: aiosqlite.Connection) -> list[dict]:
    """
    Fetch all articles that have categories and summaries.

    Returns:
        List of article dicts with link_id, categories, and article_summary
    """
    cursor = await db.execute(
        """
        SELECT c.link_id, a.id, a.categories, a.article_summary
        FROM analysis a
        JOIN contents c ON a.content_id = c.id
        WHERE a.categories IS NOT NULL AND a.categories != ''
        """
    )
    rows = await cursor.fetchall()

    return [
        {
            "link_id": row[0],
            "article_id": row[1],
            "categories": [c.strip() for c in row[2].split(",") if c.strip()],
            "article_summary": row[3] or "",
        }
        for row in rows
    ]


async def get_user_articles_without_match(
    db: aiosqlite.Connection, user_id: int
) -> list[dict]:
    """
    Fetch user_articles entries that don't have matched_categories yet.

    Args:
        db: Database connection
        user_id: User ID to filter by

    Returns:
        List of user_article dicts
    """
    cursor = await db.execute(
        """
        SELECT ua.id, ua.article_id
        FROM user_articles ua
        WHERE ua.user_id = ?
          AND (ua.matched_categories IS NULL OR ua.matched_categories = '')
        """,
        (user_id,),
    )
    rows = await cursor.fetchall()

    return [{"id": row[0], "article_id": row[1]} for row in rows]


# async def get_all_articles(db: aiosqlite.Connection) -> list[dict]:
#     cursor = await db.execute(
#         """
#         SELECT article_id
#         FROM user_articles ua
#         WHERE ua.user_id = ?
#           AND (ua.matched_categories IS NULL OR ua.matched_categories = '')
#         """,
#         (user_id,),
#     )
#     rows = await cursor.fetchall()
#
#     return [{"id": row[0], "article_id": row[1]} for row in rows]


async def insert_user_article(
    db: aiosqlite.Connection,
    user_id: int,
    article_id: int,
    matched_categories: list[str],
    relevance_score: float | None = None,
) -> None:
    """
    Insert a new user_article record into the database.

    Args:
        db: Database connection
        user_id: User ID
        article_id: Article ID (link_id)
        matched_categories: List of matched category slugs
        relevance_score: Relevance score (0-5)
    """
    import time

    matched_json = json.dumps(matched_categories)
    created_at = int(time.time())

    await db.execute(
        """
        INSERT INTO user_articles (user_id, article_id, matched_categories, relevance_score, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, article_id) DO UPDATE SET
            matched_categories = excluded.matched_categories,
            relevance_score = excluded.relevance_score
        """,
        (user_id, article_id, matched_json, relevance_score, created_at),
    )
    await db.commit()


async def calculate_relevance(
    llm: LLM, user_description: str, article_summary: str
) -> float | None:
    """
    Calculate relevance score using LLM.

    Args:
        llm: LLM instance
        user_description: User's custom description of interests
        article_summary: Article summary

    Returns:
        Relevance score (0-5) or None if calculation failed
    """
    if not user_description or not article_summary:
        return None

    try:
        result = await RelevanceScore.run(
            llm,
            user_description=user_description,
            article_summary=article_summary,
        )
        # Clamp the score to 0-5 range
        return max(0.0, min(5.0, result.relevance))
    except Exception as e:
        print(f"Error calculating relevance: {e}")
        return None


async def main():
    """Main matching procedure."""
    print("Starting category matching and relevance scoring...")

    # Initialize LLM
    llm = LLM.from_url("openai:///gpt-5-mini")

    async with aiosqlite.connect(DB_PATH) as db:
        users = await get_users_with_categories(db)
        print(f"Found {len(users)} users with categories")

        if not users:
            print("No users with categories. Done!")
            return

        # Get all articles with categories (cache for efficiency)
        articles = await get_articles_with_categories(db)
        print(f"Found {len(articles)} articles with categories")

        # Create a lookup by link_id
        articles_by_link_id = {a["link_id"]: a for a in articles}

        # Process each user
        total_matched = 0
        total_scored = 0

        for user in users:
            user_id = user["id"]
            user_categories = set(user["categories"])
            user_description = user["custom_description"]

            print(f"\nProcessing user {user_id}...")
            print(f"  User categories: {user_categories}")

            # Get user_articles that need matching
            # user_articles = await get_user_articles_without_match(db, user_id)
            # print(f"  Found {len(user_articles)} articles to process")

            print("user categories ", user_categories)

            for a in articles:
                article_id = a["link_id"]
                article = articles_by_link_id.get(article_id)

                if not article:
                    continue

                article_categories = set(article["categories"])
                print("user categories ", user_categories)
                print("article categories ", article_categories)

                matched = list(user_categories & article_categories)

                if not matched:
                    # No matching categories, store empty match
                    await insert_user_article(db, user_id, article_id, [])
                    continue

                total_matched += 1

                # Calculate relevance score if user has a description
                relevance_score = None
                if user_description and article["article_summary"]:
                    relevance_score = await calculate_relevance(
                        llm, user_description, article["article_summary"]
                    )
                    if relevance_score is not None:
                        total_scored += 1
                        print(
                            f"  Article {article_id}: matched={matched}, "
                            f"relevance={relevance_score:.1f}"
                        )

                await insert_user_article(
                    db, user_id, article_id, matched, relevance_score
                )

        # Final report
        print("\n" + "=" * 60)
        print("Matching complete!")
        print(f"Total users processed: {len(users)}")
        print(f"Articles with category matches: {total_matched}")
        print(f"Articles with relevance scores: {total_scored}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
