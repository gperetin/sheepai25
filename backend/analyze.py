#!/usr/bin/env python3
"""
Analyze phase: Generate summaries of articles and comments using LLM.
"""

import asyncio
import os

import aiosqlite
from dotenv import load_dotenv
from think import LLM, ask
from constants import CATEGORIES

load_dotenv()

DB_PATH = "../data/db.sqlite"
ARTICLE_SUMMARY_PROMPT = """
Summarize the following article in 3-5 sentences. Focus on the key points and main takeaways.
Do not prefix the output with "-" or "This article contains..." or anything else - output just
the article summary and that's it.

Article:
{{ article }}"""

COMMENTS_SUMMARY_PROMPT = """
Here is a dump of HackerNews comments with author names and timestamp. Summarize the comments
in a 3-5 sentence summary. Don't mention any usernames. Ignore the irrelevant or tangential
comments, just summarize the comments related to the article.

Comments:
{{ comments }}
"""

CATEGORIZATION_PROMPT = """
I have a text of an article and a set of predefined categories. I'd like you to analyze the
article text and give me a list of the categories that this article belongs to.
Return just the category slugs, as a comma-delimited list, nothing else.

Here are the categories, in the format: (slug, description)
{{ categories }}

Here is the text of the article:
{{ article }}
"""

async def get_contents_to_analyze(db: aiosqlite.Connection) -> list[tuple[int, str, str]]:
    """
    Get contents that have articles but no analysis yet.

    Args:
        db: Database connection

    Returns:
        List of (content_id, article, comments) tuples
    """
    cursor = await db.execute(
        """
        SELECT c.id, c.article, c.comments
        FROM contents c
        LEFT JOIN analysis a ON a.content_id = c.id
        WHERE c.article IS NOT NULL
          AND c.article != ''
          AND a.id IS NULL
        """
    )
    rows = await cursor.fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


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


async def summarize_comments(llm: LLM, comments: str) -> str:
    summary = await ask(llm, COMMENTS_SUMMARY_PROMPT, comments=comments)
    return summary


async def categorize(llm: LLM, article: str, categories: list) -> str:
    cats_str = "\n".join([f"({t[0]}, {t[1]})" for t in categories])
    categories = await ask(llm, CATEGORIZATION_PROMPT, article=article, categories=cats_str)
    return categories


async def save_analysis(db: aiosqlite.Connection, content_id: int, article_summary: str, comments_summary: str, categories: str) -> None:
    """
    Save the article summary to the analysis table.

    Args:
        db: Database connection
        content_id: ID of the content record
        article_summary: Generated article summary
        comments_summary: Generated comments summary
        categories: Selected categories for the article
    """
    await db.execute(
        """
        INSERT INTO analysis (content_id, article_summary, comments_summary, categories)
        VALUES (?, ?, ?, ?)
        """,
        (content_id, article_summary, comments_summary, categories),
    )
    await db.commit()


async def generate_summaries():
    """
    Main analysis procedure.
    """

    # Extract just the slug and description from categories.
    categories = [(c[0], c[2]) for c in CATEGORIES]

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
        for i, (content_id, article, comments) in enumerate(contents):
            try:
                article_summary, comments_summary, selected_categories = await asyncio.gather(
                    summarize_article(llm, article),
                    summarize_comments(llm, comments),
                    categorize(llm, article, categories)
                )
                await save_analysis(db, content_id, article_summary, comments_summary, selected_categories)
                analyzed_count += 1
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
    asyncio.run(generate_summaries())
