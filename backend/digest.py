#!/usr/bin/env python3
"""
Email Digest Script - Send personalized article digests to users

This script queries all active users, finds their unsent articles (is_sent=0),
and sends a personalized HTML email digest to each user. After successful email
delivery, it marks the articles as sent (is_sent=1).

Usage:
    uv run python digest.py
"""

import json
import sqlite3
from os import environ
from logging import getLogger, basicConfig, INFO
from typing import List, Dict, Any
from collections import defaultdict

from dotenv import load_dotenv
import mail

# Load environment variables
load_dotenv()

# Configure logging
basicConfig(level=INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = getLogger(__name__)

# Get configuration from environment
DB_PATH = environ.get("DB_PATH", "../data/db.sqlite")
APP_BASE_URL = environ.get("APP_BASE_URL", "http://localhost:3000")


def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def get_users_with_unsent_articles() -> Dict[int, Dict[str, Any]]:
    """
    Fetch all active users who have unsent articles.

    Returns:
        Dictionary mapping user_id to user data (email, categories, etc.)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT u.id, u.email, u.categories, u.custom_description
        FROM users u
        JOIN user_articles ua ON u.id = ua.user_id
        WHERE u.is_active = 1 AND ua.is_sent = 0
        ORDER BY u.id
    """

    cursor.execute(query)
    users = {}
    for row in cursor.fetchall():
        users[row["id"]] = {
            "email": row["email"],
            "categories": row["categories"],
            "custom_description": row["custom_description"],
        }

    conn.close()
    log.info(f"Found {len(users)} users with unsent articles")
    return users


def get_unsent_articles_for_user(user_id: int) -> List[Dict[str, Any]]:
    """
    Fetch all unsent articles for a specific user with article details.

    Args:
        user_id: The user's ID

    Returns:
        List of article dictionaries with full details
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            ua.id as user_article_id,
            l.id as article_id,
            l.title,
            l.url,
            l.hnlink,
            a.article_summary,
            a.comments_summary,
            ua.relevance_score,
            ua.matched_categories
        FROM user_articles ua
        JOIN links l ON ua.article_id = l.id
        LEFT JOIN contents c ON l.id = c.link_id
        LEFT JOIN analysis a ON c.id = a.content_id
        WHERE ua.user_id = ? AND ua.is_sent = 0
            AND ua.matched_categories IS NOT NULL
            AND ua.matched_categories != '[]'
        ORDER BY ua.relevance_score DESC
    """

    cursor.execute(query, (user_id,))
    articles = [dict(row) for row in cursor.fetchall()]

    conn.close()
    log.info(f"Found {len(articles)} unsent articles for user {user_id}")
    return articles


def generate_html_email(user_email: str, articles: List[Dict[str, Any]]) -> str:
    """
    Generate HTML email content for the digest.

    Args:
        user_email: User's email address
        articles: List of article dictionaries

    Returns:
        HTML string for the email body
    """
    # Build article cards HTML
    article_cards = []
    for article in articles:
        title = article.get("title", "Untitled Article")
        url = article.get("url", "#")
        hnlink = article.get("hnlink", "#")
        article_id = article.get("article_id", 0)
        relevance_score = article.get("relevance_score", 0)
        matched_categories = article.get("matched_categories", "")
        summary = article.get("article_summary", "")

        # Format relevance score
        score_display = f"{relevance_score:.1f}" if relevance_score else "N/A"

        # Format matched categories as tags
        categories_html = ""
        if matched_categories:
            try:
                categories = json.loads(matched_categories)
                category_tags = []
                for cat in categories[:3]:  # Show max 3 categories
                    cat_display = cat.strip().replace("-", " ").title()
                    category_tags.append(
                        f'<span style="display: inline-block; background-color: #e8f4f8; color: #0066cc; '
                        f"padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 4px; "
                        f'margin-bottom: 4px;">{cat_display}</span>'
                    )
                categories_html = "".join(category_tags)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, skip categories display
                pass

        # Truncate summary if too long
        if summary and len(summary) > 300:
            summary = summary[:297] + "..."

        # Build the article card
        article_link = f"{APP_BASE_URL}/article/{article_id}"

        card_html = f"""
        <div style="background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px;
                    padding: 20px; margin-bottom: 20px;">
            <div style="margin-bottom: 8px;">
                <span style="background-color: #ff6b35; color: white; padding: 4px 10px;
                             border-radius: 4px; font-size: 12px; font-weight: bold;">
                    Score: {score_display}
                </span>
            </div>

            <h2 style="margin: 12px 0; font-size: 20px; line-height: 1.4;">
                <a href="{article_link}" style="color: #1a1a1a; text-decoration: none;">
                    {title}
                </a>
            </h2>

            {f'<div style="margin: 12px 0;">{categories_html}</div>' if categories_html else ''}

            {f'<p style="color: #4a4a4a; line-height: 1.6; margin: 12px 0;">{summary}</p>' if summary else ''}

            <div style="margin-top: 12px;">
                <a href="{article_link}"
                   style="color: #0066cc; text-decoration: none; font-weight: 500; margin-right: 16px;">
                    Read Article &rarr;
                </a>
            </div>
        </div>
        """
        article_cards.append(card_html)

    articles_html = "".join(article_cards)

    # Complete email HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Personalized Article Digest</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header -->
            <div style="background-color: #1a1a1a; color: white; padding: 30px 20px;
                        border-radius: 8px 8px 0 0; text-align: center;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 600;">
                    Your Personalized Article Digest
                </h1>
                <p style="margin: 10px 0 0; font-size: 16px; opacity: 0.9;">
                    {len(articles)} new article{"s" if len(articles) != 1 else ""} selected for you
                </p>
            </div>

            <!-- Content -->
            <div style="background-color: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px;">
                <p style="color: #4a4a4a; line-height: 1.6; margin-top: 0;">
                    Hi! Here are your latest personalized articles based on your interests.
                </p>

                {articles_html}

                <!-- Footer -->
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;
                            text-align: center; color: #666666; font-size: 14px;">
                    <p style="margin: 0 0 10px;">
                        This digest was sent to {user_email}
                    </p>
                    <p style="margin: 0;">
                        <a href="{APP_BASE_URL}/profile"
                           style="color: #0066cc; text-decoration: none;">
                            Manage your preferences
                        </a>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def mark_articles_as_sent(user_article_ids: List[int]) -> None:
    """
    Mark articles as sent in the database.

    Args:
        user_article_ids: List of user_article IDs to mark as sent
    """
    if not user_article_ids:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # Create placeholders for SQL IN clause
    placeholders = ",".join("?" * len(user_article_ids))
    query = f"UPDATE user_articles SET is_sent = 1 WHERE id IN ({placeholders})"

    cursor.execute(query, user_article_ids)
    conn.commit()
    conn.close()

    log.info(f"Marked {len(user_article_ids)} articles as sent")


def mark_empty_categories_as_sent(user_id: int) -> None:
    """
    Mark articles with NULL or empty matched_categories as sent without including them in digest.

    Args:
        user_id: The user's ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        UPDATE user_articles
        SET is_sent = 1
        WHERE user_id = ? AND is_sent = 0
            AND (matched_categories IS NULL OR matched_categories = '[]')
    """

    cursor.execute(query, (user_id,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()

    if rows_affected > 0:
        log.info(f"Marked {rows_affected} articles with empty categories as sent for user {user_id}")


def send_digest_to_user(
    user_id: int, user_data: Dict[str, Any], articles: List[Dict[str, Any]]
) -> bool:
    """
    Send digest email to a single user.

    Args:
        user_id: User's ID
        user_data: User information (email, categories, etc.)
        articles: List of articles to include in digest

    Returns:
        True if email was sent successfully, False otherwise
    """
    email = user_data["email"]

    try:
        # Generate HTML content
        html_content = generate_html_email(email, articles)

        # Prepare subject
        article_count = len(articles)
        subject = f"Your Daily Digest: {article_count} New Article{'s' if article_count != 1 else ''}"

        # Send email
        mail.send(recipient=email, subject=subject, content=html_content)

        # Mark articles as sent
        user_article_ids = [article["user_article_id"] for article in articles]
        mark_articles_as_sent(user_article_ids)

        # Mark articles with NULL or empty matched_categories as sent
        mark_empty_categories_as_sent(user_id)

        log.info(f"Successfully sent digest to {email} with {article_count} articles")
        return True

    except Exception as e:
        log.error(f"Failed to send digest to {email}: {e}", exc_info=True)
        return False


def main():
    """Main function to run the digest script."""
    log.info("Starting email digest script")

    # Get users with unsent articles
    users = get_users_with_unsent_articles()

    if not users:
        log.info("No users with unsent articles found. Exiting.")
        return

    # Process each user
    success_count = 0
    failure_count = 0

    for user_id, user_data in users.items():
        # Get unsent articles for this user
        articles = get_unsent_articles_for_user(user_id)

        if not articles:
            log.warning(
                f"No articles found for user {user_id} (email: {user_data['email']})"
            )
            continue

        # Send digest
        if send_digest_to_user(user_id, user_data, articles):
            success_count += 1
        else:
            failure_count += 1

    # Summary
    log.info(
        f"Digest script completed. Success: {success_count}, Failures: {failure_count}"
    )


if __name__ == "__main__":
    main()
