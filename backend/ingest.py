#!/usr/bin/env python3
"""
Ingest phase: Fetch HN top stories and their comments from the Firebase API.
"""

import asyncio
import os
import re
from datetime import datetime
from html import unescape

import aiosqlite
import httpx
from dotenv import load_dotenv

from constants import COMMENT_DEPTH, TOP_STORIES_LIMIT

load_dotenv()


async def get_top_story_ids(client: httpx.AsyncClient, limit: int) -> list[int]:
    """
    Fetch top story IDs from HN.

    Args:
        client: HTTP client for making requests
        limit: Maximum number of story IDs to return

    Returns:
        List of HN story IDs
    """
    base_url = os.environ.get("HN_BASE_URL")
    url = f"{base_url}/topstories.json"

    try:
        response = await client.get(url)
        response.raise_for_status()
        story_ids = response.json()
        return story_ids[:limit]
    except Exception as e:
        print(f"Error fetching top stories: {e}")
        return []


async def fetch_item(client: httpx.AsyncClient, hn_id: int) -> dict | None:
    """
    Fetch a single item (story or comment) from HN.

    Args:
        client: HTTP client for making requests
        hn_id: HN item ID

    Returns:
        Item data as dict, or None if fetch failed
    """
    base_url = os.environ.get("HN_BASE_URL")
    url = f"{base_url}/item/{hn_id}.json"

    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Failed to fetch item {hn_id}: {e}")
        return None


async def fetch_comments_recursive(
    client: httpx.AsyncClient,
    comment_ids: list[int],
    current_depth: int,
    max_depth: int,
) -> list[dict]:
    """
    Recursively fetch comments up to a specified depth.

    Args:
        client: HTTP client for making requests
        comment_ids: List of comment IDs to fetch
        current_depth: Current recursion depth
        max_depth: Maximum depth to recurse (0 = no recursion)

    Returns:
        Flattened list of all comment dicts
    """
    if not comment_ids or current_depth > max_depth:
        return []

    comments = []

    # Fetch all comments at this level
    for comment_id in comment_ids:
        comment = await fetch_item(client, comment_id)
        if comment and not comment.get("deleted") and not comment.get("dead"):
            # Store the comment with its depth for formatting
            comment["_depth"] = current_depth
            comments.append(comment)

            # Recursively fetch child comments if we haven't reached max depth
            if current_depth < max_depth and comment.get("kids"):
                child_comments = await fetch_comments_recursive(
                    client, comment["kids"], current_depth + 1, max_depth
                )
                comments.extend(child_comments)

    return comments


def strip_html(text: str) -> str:
    """
    Remove HTML tags and decode HTML entities from text.

    Args:
        text: HTML text

    Returns:
        Plain text
    """
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = unescape(text)
    return text


def format_comments_as_text(comments: list[dict]) -> str:
    """
    Format comment tree as readable text.

    Args:
        comments: List of comment dicts with _depth field

    Returns:
        Formatted text representation of comments
    """
    if not comments:
        return ""

    lines = []
    for comment in comments:
        depth = comment.get("_depth", 0)
        indent = "  " * depth

        author = comment.get("by", "[deleted]")
        timestamp = comment.get("time", 0)
        text = strip_html(comment.get("text", ""))

        # Format timestamp
        dt = datetime.fromtimestamp(timestamp)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        # Add comment header and text
        lines.append(f"{indent}[{author}] at {time_str}:")
        lines.append(f"{indent}{text}")
        lines.append("")  # Blank line between comments

    return "\n".join(lines)


async def process_story(
    client: httpx.AsyncClient, hn_id: int, max_comment_depth: int
) -> dict | None:
    """
    Fetch a story and all its comments.

    Args:
        client: HTTP client for making requests
        hn_id: HN story ID
        max_comment_depth: Maximum depth for comment recursion

    Returns:
        Combined story data with formatted comments, or None if failed
    """
    # Fetch story details
    story = await fetch_item(client, hn_id)

    if not story:
        return None

    # Filter out non-stories
    if story.get("type") != "story":
        return None

    # Fetch comments if the story has any
    comments = []
    if story.get("kids"):
        comments = await fetch_comments_recursive(
            client, story["kids"], 0, max_comment_depth
        )

    # Format comments as text
    comments_text = format_comments_as_text(comments)

    # Build result
    result = {
        "hn_id": hn_id,
        "title": story.get("title"),
        "url": story.get("url"),
        "score": story.get("score"),
        "time": story.get("time"),
        "author": story.get("by"),
        "descendants": story.get("descendants", 0),
        "hnlink": f"https://news.ycombinator.com/item?id={hn_id}",
        "comments_text": comments_text,
    }

    return result


async def insert_story_with_content(db: aiosqlite.Connection, story: dict) -> bool:
    """
    Insert story into links table and comments into contents table.

    Args:
        db: Database connection
        story: Story data dict

    Returns:
        True if inserted successfully, False if skipped (already exists)
    """
    # Check if story already exists
    cursor = await db.execute("SELECT id FROM links WHERE hn_id = ?", (story["hn_id"],))
    existing = await cursor.fetchone()

    if existing:
        return False

    # Insert into links table
    await db.execute(
        """
        INSERT INTO links (hn_id, title, url, score, time, author, descendants, hnlink)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            story["hn_id"],
            story["title"],
            story["url"],
            story["score"],
            story["time"],
            story["author"],
            story["descendants"],
            story["hnlink"],
        ),
    )

    # Get the auto-generated link ID
    cursor = await db.execute("SELECT last_insert_rowid()")
    link_id = (await cursor.fetchone())[0]

    # Insert into contents table (article is None for now, will be fetched in scrape phase)
    await db.execute(
        "INSERT INTO contents (link_id, article, comments) VALUES (?, ?, ?)",
        (link_id, None, story["comments_text"]),
    )

    await db.commit()
    return True


async def main():
    """
    Main ingest procedure.
    """
    print("Starting HN ingest procedure...")

    # Load environment variables
    base_url = os.environ.get("HN_BASE_URL")
    db_path = os.environ.get("DB_PATH")

    if not base_url:
        print("Error: HN_BASE_URL not set in environment")
        return

    if not db_path:
        print("Error: DB_PATH not set in environment")
        return

    print(f"Fetching top {TOP_STORIES_LIMIT} stories from HN...")

    # Create HTTP client
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch top story IDs
        story_ids = await get_top_story_ids(client, TOP_STORIES_LIMIT)

        if not story_ids:
            print("Error: No story IDs fetched")
            return

        print(f"Found {len(story_ids)} story IDs")

        # Process each story
        inserted_count = 0
        skipped_count = 0
        failed_count = 0

        async with aiosqlite.connect(db_path) as db:
            for i, hn_id in enumerate(story_ids):
                print(
                    f"Processing story {i + 1}/{len(story_ids)} "
                    f"(inserted: {inserted_count}, skipped: {skipped_count}, failed: {failed_count})..."
                )

                # Check if story already exists before fetching
                cursor = await db.execute(
                    "SELECT id FROM links WHERE hn_id = ?", (hn_id,)
                )
                existing = await cursor.fetchone()

                if existing:
                    skipped_count += 1
                    continue

                # Fetch story and comments
                story = await process_story(client, hn_id, COMMENT_DEPTH)

                if not story:
                    failed_count += 1
                    continue

                # Insert into database
                inserted = await insert_story_with_content(db, story)

                if inserted:
                    inserted_count += 1
                else:
                    # This shouldn't happen since we checked above, but just in case
                    skipped_count += 1

        # Final report
        print("\n" + "=" * 60)
        print("Ingest complete!")
        print(f"Total stories processed: {len(story_ids)}")
        print(f"Inserted: {inserted_count}")
        print(f"Skipped (already exists): {skipped_count}")
        print(f"Failed: {failed_count}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
