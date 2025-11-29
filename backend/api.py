import os
import uuid
import random
import time
import json
from datetime import datetime
from typing import Optional, List
from urllib.parse import urlparse

import aiosqlite
import bcrypt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from think import LLM, Chat

from constants import CATEGORIES

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="FTL News API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_PATH = os.getenv("DB_PATH", "data.db")


# ============================================================================
# Pydantic Models
# ============================================================================


# Auth Models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str


# Profile Models
class ProfileResponse(BaseModel):
    topics: List[str]
    customDescription: str


class ProfileUpdateRequest(BaseModel):
    topics: List[str]
    customDescription: str = ""


# Article Models
class ArticleResponse(BaseModel):
    id: str
    title: str
    domain: str
    hnScore: int
    hnComments: int
    relevanceScore: float
    trustworthinessScore: float
    controversyScore: float
    confidenceScore: float
    summary: str
    commentsSummary: str
    articleUrl: str
    hnUrl: str


# Chat Models
class ChatMessage(BaseModel):
    id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: int


class ChatMessageRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


# Category Models
class CategoryResponse(BaseModel):
    slug: str
    title: str
    description: str


# ============================================================================
# Database Helpers
# ============================================================================


async def get_db_connection():
    """Create and return a database connection."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


async def get_all_articles():
    """Fetch all articles with their content and analysis."""
    conn = await get_db_connection()
    try:
        query = """
            SELECT
                l.id,
                l.hn_id,
                l.title,
                l.url,
                l.score,
                l.descendants,
                l.hnlink,
                c.article,
                c.comments,
                a.article_summary,
                a.comments_summary,
                a.scores
            FROM links l
            LEFT JOIN contents c ON l.id = c.link_id
            LEFT JOIN analysis a ON c.id = a.content_id
            ORDER BY l.score DESC
        """
        async with conn.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_article_by_id(article_id: str):
    """Fetch a single article by ID."""
    conn = await get_db_connection()
    try:
        query = """
            SELECT
                l.id,
                l.hn_id,
                l.title,
                l.url,
                l.score,
                l.descendants,
                l.hnlink,
                c.article,
                c.comments,
                a.article_summary,
                a.comments_summary,
                a.scores
            FROM links l
            LEFT JOIN contents c ON l.id = c.link_id
            LEFT JOIN analysis a ON c.id = a.content_id
            WHERE l.id = ?
        """
        async with conn.execute(query, (article_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
    finally:
        await conn.close()


# ============================================================================
# Authentication Helpers
# ============================================================================


def generate_token() -> str:
    """Generate a unique bearer token."""
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency to validate bearer token and return user data."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid authorization header format"
        )

    token = authorization.replace("Bearer ", "")

    # Find user by token in database
    conn = await get_db_connection()
    try:
        query = "SELECT id, email, categories, custom_description, is_active FROM users WHERE token = ?"
        async with conn.execute(query, (token,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="Invalid or expired token")

            user = dict(row)
            if not user["is_active"]:
                raise HTTPException(status_code=401, detail="Account is inactive")

            return user
    finally:
        await conn.close()


# ============================================================================
# Article Helpers
# ============================================================================


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    if not url:
        return "news.ycombinator.com"
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else "news.ycombinator.com"
    except:
        return "news.ycombinator.com"


def parse_scores_from_json(scores_json: Optional[str]) -> dict:
    """Parse scores from JSON field and return individual score values."""
    # Default scores (all 0.0)
    default_scores = {
        "controversial": 0.0,
        "trustworthy": 0.0,
        "sentiment": 0.0,
        "confidence": 0.0,
    }

    # If no scores data, return defaults
    if not scores_json:
        return default_scores

    try:
        scores_data = json.loads(scores_json)
        # Use .get() with default 0.0 for missing keys
        return {
            "controversial": scores_data.get("controversial", 0.0),
            "trustworthy": scores_data.get("trustworthy", 0.0),
            "sentiment": scores_data.get("sentiment", 0.0),
            "confidence": scores_data.get("confidence", 0.0),
        }
    except (json.JSONDecodeError, AttributeError, TypeError):
        # If JSON parsing fails, return defaults
        return default_scores


def get_real_scores(scores_json: Optional[str], relevance_score: Optional[float]) -> dict:
    """Get real scores from database analysis."""
    # Parse scores from JSON field
    parsed_scores = parse_scores_from_json(scores_json)

    # Map database fields to API response format
    # Use relevance_score from user_articles table (user-specific matching)
    # Use trustworthy, controversial, and confidence from analysis scores JSON
    return {
        "relevanceScore": round(relevance_score or 0.0, 1),
        "trustworthinessScore": round(parsed_scores["trustworthy"], 1),
        "controversyScore": round(parsed_scores["controversial"], 1),
        "confidenceScore": round(parsed_scores["confidence"], 1),
    }


def map_article_to_response(
    article_data: dict, user_topics: List[str]
) -> ArticleResponse:
    """Map database article to API response format."""
    # Get real scores from database
    scores = get_real_scores(
        article_data.get("scores"), article_data.get("relevance_score")
    )

    # Use analysis summaries if available, otherwise provide placeholder
    article_summary = (
        article_data.get("article_summary") or "Article summary not yet available."
    )
    comments_summary = (
        article_data.get("comments_summary") or "Comments summary not yet available."
    )

    return ArticleResponse(
        id=str(article_data["id"]),
        title=article_data["title"],
        domain=extract_domain(article_data["url"]),
        hnScore=article_data["score"] or 0,
        hnComments=article_data["descendants"] or 0,
        relevanceScore=scores["relevanceScore"],
        trustworthinessScore=scores["trustworthinessScore"],
        controversyScore=scores["controversyScore"],
        confidenceScore=scores["confidenceScore"],
        summary=article_summary,
        commentsSummary=comments_summary,
        articleUrl=article_data["url"] or article_data["hnlink"],
        hnUrl=article_data["hnlink"]
        or f"https://news.ycombinator.com/item?id={article_data['id']}",
    )


def filter_articles_by_topics(articles: List[dict], topics: List[str]) -> List[dict]:
    """Filter articles based on user's selected topics (simple keyword matching)."""
    if not topics:
        return articles

    # Get keywords from selected categories
    category_keywords = set()
    for slug, cat_title, cat_desc in CATEGORIES:
        if slug in topics:
            keywords = cat_title.lower().split() + cat_desc.lower().split()
            category_keywords.update([k.strip(",.()") for k in keywords if len(k) > 3])

    # Filter articles that contain any of the keywords
    filtered = []
    for article in articles:
        title_lower = article["title"].lower()
        if any(keyword in title_lower for keyword in category_keywords):
            filtered.append(article)

    # If no articles match, return top scored articles anyway (fallback)
    return filtered if filtered else articles[:20]


# ============================================================================
# Authentication Endpoints
# ============================================================================


@app.post("/api/auth/register", status_code=201)
async def register(request: RegisterRequest) -> LoginResponse:
    """Register a new user account."""
    conn = await get_db_connection()
    try:
        # Check if email already exists
        async with conn.execute(
            "SELECT id FROM users WHERE email = ?", (request.email,)
        ) as cursor:
            if await cursor.fetchone():
                raise HTTPException(status_code=409, detail="Email already registered")

        # Generate token and hash password
        token = generate_token()
        password_hash = hash_password(request.password)
        current_time = int(time.time())

        # Insert new user
        await conn.execute(
            """
            INSERT INTO users (email, password_hash, token, is_active, is_email_verified,
                             categories, custom_description, created_at, updated_at)
            VALUES (?, ?, ?, 1, 1, '', '', ?, ?)
            """,
            (request.email, password_hash, token, current_time, current_time),
        )
        await conn.commit()

        return LoginResponse(token=token)
    finally:
        await conn.close()


@app.post("/api/auth/login")
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate user and return bearer token."""
    conn = await get_db_connection()
    try:
        # Find user by email
        async with conn.execute(
            "SELECT id, password_hash, is_active FROM users WHERE email = ?",
            (request.email,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user = dict(row)

        # Check if account is active
        if not user["is_active"]:
            raise HTTPException(status_code=401, detail="Account is inactive")

        # Verify password
        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Generate new token
        token = generate_token()
        current_time = int(time.time())

        # Update user's token
        await conn.execute(
            "UPDATE users SET token = ?, updated_at = ? WHERE id = ?",
            (token, current_time, user["id"]),
        )
        await conn.commit()

        return LoginResponse(token=token)
    finally:
        await conn.close()


# ============================================================================
# Profile Endpoints
# ============================================================================


@app.get("/api/profile/")
async def get_profile(
    current_user: dict = Depends(get_current_user),
) -> ProfileResponse:
    """Fetch user profile and preferences."""
    # Parse categories from comma-separated string
    topics = [t.strip() for t in current_user["categories"].split(",") if t.strip()]

    return ProfileResponse(
        topics=topics,
        customDescription=current_user["custom_description"] or "",
    )


@app.post("/api/profile/")
async def update_profile(
    request: ProfileUpdateRequest, current_user: dict = Depends(get_current_user)
):
    """Update user profile and preferences."""
    if not request.topics:
        raise HTTPException(status_code=400, detail="At least one topic is required")

    # Validate topics against available categories
    valid_slugs = {slug for slug, _, _ in CATEGORIES}
    invalid_topics = [t for t in request.topics if t not in valid_slugs]
    if invalid_topics:
        raise HTTPException(
            status_code=400, detail=f"Invalid topics: {', '.join(invalid_topics)}"
        )

    # Update user profile in database
    conn = await get_db_connection()
    try:
        # Convert topics list to comma-separated string
        categories_str = ",".join(request.topics)
        current_time = int(time.time())

        await conn.execute(
            "UPDATE users SET categories = ?, custom_description = ?, updated_at = ? WHERE id = ?",
            (
                categories_str,
                request.customDescription,
                current_time,
                current_user["id"],
            ),
        )
        await conn.commit()

        return {"message": "Profile updated successfully"}
    finally:
        await conn.close()


# ============================================================================
# Categories Endpoint
# ============================================================================


@app.get("/api/categories/")
async def get_categories() -> List[CategoryResponse]:
    """Fetch all available categories."""
    return [
        CategoryResponse(slug=slug, title=title, description=description)
        for slug, title, description in CATEGORIES
    ]


# ============================================================================
# Articles Endpoints
# ============================================================================


@app.get("/api/articles/")
async def get_articles(
    current_user: dict = Depends(get_current_user),
) -> List[ArticleResponse]:
    """Fetch all articles personalized for the user."""
    # Parse user's topics from categories field
    user_topics = [
        t.strip() for t in current_user["categories"].split(",") if t.strip()
    ]

    # Fetch articles that are available to this user from user_articles table
    conn = await get_db_connection()
    try:
        query = """
            SELECT
                l.id,
                l.hn_id,
                l.title,
                l.url,
                l.score,
                l.descendants,
                l.hnlink,
                c.article,
                c.comments,
                a.article_summary,
                a.comments_summary,
                a.scores,
                ua.is_read,
                ua.relevance_score
            FROM user_articles ua
            JOIN links l ON ua.article_id = l.id
            LEFT JOIN contents c ON l.id = c.link_id
            LEFT JOIN analysis a ON c.id = a.content_id
            WHERE ua.user_id = ?
                AND ua.matched_categories IS NOT NULL
                AND ua.matched_categories != '[]'
            ORDER BY l.score DESC
        """
        async with conn.execute(query, (current_user["id"],)) as cursor:
            rows = await cursor.fetchall()
            articles = [dict(row) for row in rows]
    finally:
        await conn.close()

    # Map to response format
    return [map_article_to_response(article, user_topics) for article in articles]


@app.get("/api/articles/{article_id}/")
async def get_article(
    article_id: str, current_user: dict = Depends(get_current_user)
) -> ArticleResponse:
    """Fetch detailed information for a specific article."""
    # Parse user's topics from categories field
    user_topics = [
        t.strip() for t in current_user["categories"].split(",") if t.strip()
    ]

    conn = await get_db_connection()
    try:
        # Check if user has access to this article via user_articles
        query = """
            SELECT
                l.id,
                l.hn_id,
                l.title,
                l.url,
                l.score,
                l.descendants,
                l.hnlink,
                c.article,
                c.comments,
                a.article_summary,
                a.comments_summary,
                a.scores,
                ua.id as user_article_id,
                ua.is_read,
                ua.relevance_score
            FROM user_articles ua
            JOIN links l ON ua.article_id = l.id
            LEFT JOIN contents c ON l.id = c.link_id
            LEFT JOIN analysis a ON c.id = a.content_id
            WHERE ua.user_id = ? AND l.id = ?
                AND ua.matched_categories IS NOT NULL
                AND ua.matched_categories != '[]'
        """
        async with conn.execute(query, (current_user["id"], article_id)) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404, detail="Article not found or not accessible"
            )

        article = dict(row)

        # Mark article as read if not already read
        if not article["is_read"]:
            await conn.execute(
                "UPDATE user_articles SET is_read = 1 WHERE id = ?",
                (article["user_article_id"],),
            )
            await conn.commit()

        return map_article_to_response(article, user_topics)
    finally:
        await conn.close()


# ============================================================================
# Chat Helpers
# ============================================================================


def truncate_article(article_text: str, paragraphs: int = 5) -> str:
    """Truncate article to first N paragraphs."""
    if not article_text:
        return ""

    # Split by double newlines (paragraphs) or single newlines if no paragraphs
    paragraphs_list = [p.strip() for p in article_text.split("\n\n") if p.strip()]

    if len(paragraphs_list) < 2:
        # Try splitting by single newlines
        paragraphs_list = [p.strip() for p in article_text.split("\n") if p.strip()]

    # Take first N paragraphs
    selected = paragraphs_list[:paragraphs]
    truncated = "\n\n".join(selected)

    # Add ellipsis if we truncated
    if len(paragraphs_list) > paragraphs:
        truncated += "\n\n[Article continues...]"

    return truncated


def build_system_prompt(
    article_title: str,
    article_summary: str,
    article_text: str,
    comments_summary: str,
    user_categories: str,
    user_custom_description: str,
) -> str:
    """Build the system prompt for the chatbot."""
    # Parse categories
    categories = [c.strip() for c in user_categories.split(",") if c.strip()]
    category_names = []
    for slug in categories:
        for cat_slug, cat_title, _ in CATEGORIES:
            if cat_slug == slug:
                category_names.append(cat_title)
                break

    # Build the prompt
    prompt = f"""You are a helpful AI assistant helping users understand and discuss HackerNews articles.

ARTICLE INFORMATION:
Title: {article_title}
Summary: {article_summary}

{truncate_article(article_text, paragraphs=5)}

DISCUSSION CONTEXT:
The HackerNews community discussed this article. Here's a summary of the key points from the comments:
{comments_summary}

USER CONTEXT:
The user is interested in the following topics: {', '.join(category_names) if category_names else 'general technology'}"""

    if user_custom_description:
        prompt += f"\nUser's specific interests: {user_custom_description}"

    prompt += """

Your role is to:
1. Help the user understand the article and its implications
2. Answer questions about the article content and related topics
3. Provide context from the HackerNews discussion when relevant
4. Relate the topic to the user's interests when appropriate
5. Be concise in your answers.

Keep responses focused and relevant. If the user asks about something not covered in the article, you can use your general knowledge but always clarify what comes from the article vs. your general knowledge."""

    return prompt


# ============================================================================
# Chat Endpoints
# ============================================================================


@app.get("/api/articles/{article_id}/chat/")
async def get_chat_history(
    article_id: str, current_user: dict = Depends(get_current_user)
) -> List[ChatMessage]:
    """Fetch chat history for a specific article."""
    conn = await get_db_connection()
    try:
        # Get user_article_id for this user and article
        async with conn.execute(
            "SELECT id FROM user_articles WHERE user_id = ? AND article_id = ?",
            (current_user["id"], article_id),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404, detail="Article not found or not accessible"
            )

        user_article_id = row["id"]

        # Fetch all messages for this user_article
        query = """
            SELECT id, role, content, timestamp
            FROM messages
            WHERE user_article_id = ?
            ORDER BY timestamp ASC
        """
        async with conn.execute(query, (user_article_id,)) as cursor:
            rows = await cursor.fetchall()
            messages = [
                ChatMessage(
                    id=str(row["id"]),
                    role=row["role"],
                    content=row["content"],
                    timestamp=row["timestamp"],
                )
                for row in rows
            ]

        return messages
    finally:
        await conn.close()


@app.post("/api/articles/{article_id}/chat/send")
async def send_chat_message(
    article_id: str,
    request: ChatMessageRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Send a chat message and receive AI response."""
    conn = await get_db_connection()
    try:
        # Get user_article_id and full article context
        query = """
            SELECT
                ua.id as user_article_id,
                l.title,
                c.article,
                a.article_summary,
                a.comments_summary
            FROM user_articles ua
            JOIN links l ON ua.article_id = l.id
            LEFT JOIN contents c ON l.id = c.link_id
            LEFT JOIN analysis a ON c.id = a.content_id
            WHERE ua.user_id = ? AND ua.article_id = ?
        """
        async with conn.execute(query, (current_user["id"], article_id)) as cursor:
            row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404, detail="Article not found or not accessible"
            )

        user_article_id = row["user_article_id"]
        article_title = row["title"]
        article_text = row["article"] or ""
        article_summary = row["article_summary"] or "No summary available."
        comments_summary = row["comments_summary"] or "No comments summary available."

        # Fetch conversation history
        history_query = """
            SELECT role, content
            FROM messages
            WHERE user_article_id = ?
            ORDER BY timestamp ASC
        """
        async with conn.execute(history_query, (user_article_id,)) as cursor:
            history_rows = await cursor.fetchall()
            conversation_history = [dict(row) for row in history_rows]

        # Build system prompt
        system_prompt = build_system_prompt(
            article_title=article_title,
            article_summary=article_summary,
            article_text=article_text,
            comments_summary=comments_summary,
            user_categories=current_user["categories"],
            user_custom_description=current_user["custom_description"],
        )

        # Build Chat object with history
        chat = Chat(system_prompt)

        # Add conversation history
        for msg in conversation_history:
            if msg["role"] == "user":
                chat.user(msg["content"])
            elif msg["role"] == "assistant":
                chat.assistant(msg["content"])

        # Add new user message
        chat.user(request.message)

        # Get LLM response
        if not app.state.llm:
            raise HTTPException(
                status_code=503,
                detail="AI service not available. Please configure OPENAI_API_KEY environment variable.",
            )

        try:
            ai_response_text = await app.state.llm(chat)
        except Exception as e:
            # Log error and provide fallback response
            print(f"LLM error: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to generate AI response"
            )

        # Store user message
        current_timestamp = int(datetime.now().timestamp() * 1000)
        await conn.execute(
            "INSERT INTO messages (user_article_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (user_article_id, "user", request.message, current_timestamp),
        )

        # Store AI response
        await conn.execute(
            "INSERT INTO messages (user_article_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (user_article_id, "assistant", ai_response_text, current_timestamp + 1),
        )

        await conn.commit()

        return ChatResponse(response=ai_response_text)
    finally:
        await conn.close()


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with consistent JSON format."""
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


# ============================================================================
# Startup Event
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    print(f"FTL News API starting...")
    print(f"Database: {DB_PATH}")
    print(f"Database-backed authentication enabled")

    # Initialize LLM for chatbot
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        app.state.llm = LLM.from_url("openai:///gpt-5-nano")
        print(f"LLM initialized for chatbot")
    else:
        app.state.llm = None
        print("WARNING: OPENAI_API_KEY not set - chatbot will not work")
