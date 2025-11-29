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


class ConfidenceScore(LLMQuery):
    """Compare the original article content with a generated summary to assess accuracy.

    ORIGINAL ARTICLE:
    {{ article }}

    GENERATED SUMMARY:
    {{ summary }}

    Evaluate how well the summary represents the original article content.
    Provide a confidence score from 0 to 5 (floats allowed):

    - 0 = The summary contains significant hallucinations or fabricated information not present in the article
    - 1 = The summary has major inaccuracies or misrepresents key points from the article
    - 2 = The summary has some inaccuracies or omits important information
    - 3 = The summary is mostly accurate but may have minor omissions or imprecisions
    - 4 = The summary accurately captures the main points with only trivial issues
    - 5 = The summary faithfully and accurately represents the article content

    Focus on factual accuracy: Does the summary make claims that are not supported by the article?
    """

    confidence: float


async def get_unscored_contents(db: aiosqlite.Connection) -> list[dict]:
    """
    Fetch content entries that don't have scores yet.

    Args:
        db: Database connection

    Returns:
        List of content dicts with article, comments, and article_summary
    """
    cursor = await db.execute(
        """
        SELECT c.id, c.link_id, c.article, c.comments, l.title, a.article_summary
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
            "article_summary": row[5],
        }
        for row in rows
    ]


async def save_scores(
    db: aiosqlite.Connection,
    content_id: int,
    scores: ArticleScores,
    confidence: float | None = None,
) -> None:
    """
    Save scores to the analysis table.

    Args:
        db: Database connection
        content_id: ID of the content entry
        scores: ArticleScores instance with the scores
        confidence: Confidence score for the summary (0-5)
    """
    scores_dict = {
        "controversial": scores.controversial,
        "trustworthy": scores.trustworthy,
        "sentiment": scores.sentiment,
    }
    if confidence is not None:
        scores_dict["confidence"] = confidence

    scores_json = json.dumps(scores_dict)

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


async def compute_confidence(llm: LLM, content: dict) -> float | None:
    """
    Compute confidence score by comparing article content with its summary.

    Args:
        llm: LLM instance (Anthropic Claude)
        content: Content dict with article and article_summary

    Returns:
        Confidence score (0-5) or None if computation failed
    """
    article = truncate_text(content["article"])
    summary = content.get("article_summary")

    if not article or not summary:
        return None

    try:
        result = await ConfidenceScore.run(
            llm,
            article=article,
            summary=summary,
        )
        return result.confidence
    except Exception as e:
        print(f"Error computing confidence for content {content['id']}: {e}")
        return None


async def main():
    """Main scoring procedure."""
    print("Starting scoring procedure...")

    # Initialize LLMs
    openai_llm = LLM.from_url("openai:///gpt-5-mini")
    anthropic_llm = LLM.from_url("anthropic:///claude-sonnet-4-20250514")

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

            scores = await score_content(openai_llm, content)

            if scores:
                # Compute confidence score using Anthropic Claude
                confidence = await compute_confidence(anthropic_llm, content)

                await save_scores(db, content["id"], scores, confidence)
                confidence_str = f"{confidence:.1f}" if confidence is not None else "N/A"
                print(
                    f"  -> controversial: {scores.controversial:.1f}, "
                    f"trustworthy: {scores.trustworthy:.1f}, "
                    f"sentiment: {scores.sentiment:.1f}, "
                    f"confidence: {confidence_str}"
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
