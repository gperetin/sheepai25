#!/usr/bin/env python3
"""
Score phase: Analyze articles and comments to produce sentiment scores.

Uses the think library to interface with OpenAI and produce structured scores
for controversial, trustworthy, and sentiment analysis.
"""

import asyncio
import json
import os

import aiosqlite
from dotenv import load_dotenv
from think import LLM, LLMQuery

load_dotenv()

DB_PATH = os.environ.get("DB_PATH", "../data/db.sqlite")


class ArticleScores(LLMQuery):
    """Analyze the following article and its Hacker News comments to produce scores.

    ARTICLE:
    {{ article }}

    COMMENTS:
    {{ comments }}

    Based on the article content and comments, provide the following scores (0-5, floats allowed):

    1. controversial: How controversial is the discussion in the comments?
       - 0 = No controversy, everyone agrees
       - 2-3 = Some differing opinions, mild disagreement
       - 5 = Heated arguments, strong opposing viewpoints

    2. trustworthy: How trustworthy does the article appear based on the comments?
       - 0 = Comments indicate major factual errors, unreliable source
       - 2-3 = Some concerns raised but generally acceptable
       - 5 = Comments confirm accuracy, highly trusted source

    3. sentiment: What is the overall sentiment/attitude of the article?
       - 0 = Very negative, pessimistic, critical
       - 2-3 = Neutral, balanced
       - 5 = Very positive, optimistic, enthusiastic
    """

    controversial: float
    trustworthy: float
    sentiment: float


async def get_unscored_contents(db: aiosqlite.Connection) -> list[dict]:
    """
    Fetch content entries that don't have scores yet.

    Args:
        db: Database connection

    Returns:
        List of content dicts with article and comments
    """
    cursor = await db.execute(
        """
        SELECT c.id, c.link_id, c.article, c.comments, l.title
        FROM contents c
        JOIN links l ON c.link_id = l.id
        LEFT JOIN analysis a ON c.id = a.content_id
        WHERE c.article IS NOT NULL
          AND (a.id IS NULL OR a.scores IS NULL)
        """
    )
    rows = await cursor.fetchall()

    return [
        {
            "id": row[0],
            "link_id": row[1],
            "article": row[2],
            "comments": row[3],
            "title": row[4],
        }
        for row in rows
    ]


async def save_scores(
    db: aiosqlite.Connection,
    content_id: int,
    scores: ArticleScores,
) -> None:
    """
    Save scores to the analysis table.

    Args:
        db: Database connection
        content_id: ID of the content entry
        scores: ArticleScores instance with the scores
    """
    scores_json = json.dumps({
        "controversial": scores.controversial,
        "trustworthy": scores.trustworthy,
        "sentiment": scores.sentiment,
    })

    # Check if analysis row exists
    cursor = await db.execute(
        "SELECT id FROM analysis WHERE content_id = ?", (content_id,)
    )
    existing = await cursor.fetchone()

    if existing:
        await db.execute(
            "UPDATE analysis SET scores = ? WHERE content_id = ?",
            (scores_json, content_id),
        )
    else:
        await db.execute(
            "INSERT INTO analysis (content_id, scores) VALUES (?, ?)",
            (content_id, scores_json),
        )

    await db.commit()


def truncate_text(text: str, max_chars: int = 15000) -> str:
    """Truncate text to a maximum number of characters."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


async def score_content(llm: LLM, content: dict) -> ArticleScores | None:
    """
    Score a single content entry using the LLM.

    Args:
        llm: LLM instance
        content: Content dict with article and comments

    Returns:
        ArticleScores instance or None if scoring failed
    """
    article = truncate_text(content["article"])
    comments = truncate_text(content["comments"])

    if not article:
        return None

    try:
        scores = await ArticleScores.run(
            llm,
            article=article,
            comments=comments if comments else "(No comments)",
        )
        return scores
    except Exception as e:
        print(f"Error scoring content {content['id']}: {e}")
        return None


async def main():
    """Main scoring procedure."""
    print("Starting scoring procedure...")

    # Initialize LLM
    llm = LLM.from_url("openai:///gpt-5-mini")

    async with aiosqlite.connect(DB_PATH) as db:
        # Get unscored content
        contents = await get_unscored_contents(db)
        print(f"Found {len(contents)} entries to score")

        if not contents:
            print("No entries to score. Done!")
            return

        # Process each entry
        scored_count = 0
        failed_count = 0

        for i, content in enumerate(contents):
            print(
                f"Scoring {i + 1}/{len(contents)}: {content['title'][:50]}... "
                f"(scored: {scored_count}, failed: {failed_count})"
            )

            scores = await score_content(llm, content)

            if scores:
                await save_scores(db, content["id"], scores)
                print(
                    f"  -> controversial: {scores.controversial:.1f}, "
                    f"trustworthy: {scores.trustworthy:.1f}, "
                    f"sentiment: {scores.sentiment:.1f}"
                )
                scored_count += 1
            else:
                failed_count += 1

        # Final report
        print("\n" + "=" * 60)
        print("Scoring complete!")
        print(f"Total entries processed: {len(contents)}")
        print(f"Scored: {scored_count}")
        print(f"Failed: {failed_count}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
