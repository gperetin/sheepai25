#!/usr/bin/env python3
"""
Analyze phase: Generate summaries of articles using LLM.
"""

import asyncio
import os

import aiosqlite
from dotenv import load_dotenv
from think import LLM, ask

load_dotenv()

DB_PATH = "../data/db.sqlite"
ARTICLE_SUMMARY_PROMPT = """
Summarize the following article in 3-5 sentences. Focus on the key points and main takeaways.
Do not prefix the output with "-" or "This article contains..." or anything else - output just
the article summary and that's it.

Article:
{{ article }}"""


async def get_contents_to_analyze(db: aiosqlite.Connection) -> list[tuple[int, str]]:
    """
    Get contents that have articles but no analysis yet.

    Args:
        db: Database connection

    Returns:
        List of (content_id, article) tuples
    """
    cursor = await db.execute(
        """
        SELECT c.id, c.article
        FROM contents c
        LEFT JOIN analysis a ON a.content_id = c.id
        WHERE c.article IS NOT NULL
          AND c.article != ''
          AND a.id IS NULL
        """
    )
    rows = await cursor.fetchall()
    return [(row[0], row[1]) for row in rows]


async def summarize_article(llm: LLM, article: str) -> str:
    """
    Generate a summary of an article using the LLM.

    Args:
        llm: LLM instance
        article: Article content to summarize

    Returns:
        Summary text (3-5 sentences)
    """

    summary = await ask(llm, ARTICLE_SUMMARY_PROMPT, article=article)
    return summary


async def save_analysis(db: aiosqlite.Connection, content_id: int, summary: str) -> None:
    """
    Save the article summary to the analysis table.

    Args:
        db: Database connection
        content_id: ID of the content record
        summary: Generated summary
    """
    await db.execute(
        """
        INSERT INTO analysis (content_id, article_summary)
        VALUES (?, ?)
        """,
        (content_id, summary),
    )
    await db.commit()


async def main():
    """
    Main analysis procedure.
    """
    print("Starting article analysis...")

    llm = LLM.from_url("openai:///gpt-5-nano")

    async with aiosqlite.connect(DB_PATH) as db:
        contents = await get_contents_to_analyze(db)

        if not contents:
            print("No articles to analyze")
            return

        print(f"Found {len(contents)} articles to analyze")

        analyzed_count = 0
        failed_count = 0

        for i, (content_id, article) in enumerate(contents):
            print(f"Analyzing article {i + 1}/{len(contents)}...")

            try:
                summary = await summarize_article(llm, article)
                await save_analysis(db, content_id, summary)
                analyzed_count += 1
                print(f"  Summary: {summary[:100]}...")
            except Exception as e:
                print(f"  Error: {e}")
                failed_count += 1

        print("\n" + "=" * 60)
        print("Analysis complete!")
        print(f"Total articles: {len(contents)}")
        print(f"Analyzed: {analyzed_count}")
        print(f"Failed: {failed_count}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
