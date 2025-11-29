import os
import uuid
import random
from datetime import datetime
from typing import Optional, List
from urllib.parse import urlparse

import aiosqlite
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

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

# Mock user storage (to be replaced with actual database later)
# Structure: {email: {password, token, topics, customDescription}}
MOCK_USERS = {}

# Mock chat storage (to be replaced with actual database later)
# Structure: {article_id: {user_email: [messages]}}
MOCK_CHATS = {}


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
                a.comments_summary
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
                a.comments_summary
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
    """Mock password hashing (replace with proper hashing later)."""
    # TODO: Use bcrypt or similar in production
    return f"hashed_{password}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Mock password verification (replace with proper verification later)."""
    # TODO: Use bcrypt or similar in production
    return hashed_password == f"hashed_{plain_password}"


async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Dependency to validate bearer token and return user email."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization.replace("Bearer ", "")

    # Find user by token
    for email, user_data in MOCK_USERS.items():
        if user_data.get("token") == token:
            return email

    raise HTTPException(status_code=401, detail="Invalid or expired token")


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


def generate_mock_scores(title: str, user_topics: List[str]) -> dict:
    """Generate mock relevance, trustworthiness, and controversy scores."""
    # Calculate relevance based on topic matching (simple keyword match)
    relevance = 2.0  # Base relevance
    title_lower = title.lower()

    # Get category keywords from user's selected topics
    category_keywords = []
    for slug, cat_title, cat_desc in CATEGORIES:
        if slug in user_topics:
            # Extract keywords from category title and description
            keywords = cat_title.lower().split() + cat_desc.lower().split()
            category_keywords.extend([k.strip(",.()") for k in keywords if len(k) > 3])

    # Check if any keywords match the title
    matches = sum(1 for keyword in category_keywords if keyword in title_lower)
    relevance += min(matches * 0.5, 3.0)  # Cap at 5.0

    # Generate realistic trustworthiness (3.0-4.5 range typically)
    trustworthiness = random.uniform(3.0, 4.5)

    # Generate controversy score (1.0-4.0 range, most articles are low controversy)
    controversy = random.uniform(1.0, 4.0)

    return {
        "relevanceScore": round(relevance, 1),
        "trustworthinessScore": round(trustworthiness, 1),
        "controversyScore": round(controversy, 1),
    }


def map_article_to_response(article_data: dict, user_topics: List[str]) -> ArticleResponse:
    """Map database article to API response format."""
    scores = generate_mock_scores(article_data["title"], user_topics)

    # Use analysis summaries if available, otherwise provide placeholder
    article_summary = article_data.get("article_summary") or "Article summary not yet available."
    comments_summary = article_data.get("comments_summary") or "Comments summary not yet available."

    return ArticleResponse(
        id=str(article_data["id"]),
        title=article_data["title"],
        domain=extract_domain(article_data["url"]),
        hnScore=article_data["score"] or 0,
        hnComments=article_data["descendants"] or 0,
        relevanceScore=scores["relevanceScore"],
        trustworthinessScore=scores["trustworthinessScore"],
        controversyScore=scores["controversyScore"],
        summary=article_summary,
        commentsSummary=comments_summary,
        articleUrl=article_data["url"] or article_data["hnlink"],
        hnUrl=article_data["hnlink"],
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
    if request.email in MOCK_USERS:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Generate token for new user
    token = generate_token()

    # Store user in mock storage
    MOCK_USERS[request.email] = {
        "password": hash_password(request.password),
        "token": token,
        "topics": [],
        "customDescription": "",
    }

    return LoginResponse(token=token)


@app.post("/api/auth/login")
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate user and return bearer token."""
    user = MOCK_USERS.get(request.email)

    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate new token
    token = generate_token()
    user["token"] = token

    return LoginResponse(token=token)


# ============================================================================
# Profile Endpoints
# ============================================================================

@app.get("/api/profile/")
async def get_profile(current_user: str = Depends(get_current_user)) -> ProfileResponse:
    """Fetch user profile and preferences."""
    user = MOCK_USERS[current_user]
    return ProfileResponse(
        topics=user["topics"],
        customDescription=user["customDescription"],
    )


@app.post("/api/profile/")
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: str = Depends(get_current_user)
):
    """Update user profile and preferences."""
    if not request.topics:
        raise HTTPException(status_code=400, detail="At least one topic is required")

    # Validate topics against available categories
    valid_slugs = {slug for slug, _, _ in CATEGORIES}
    invalid_topics = [t for t in request.topics if t not in valid_slugs]
    if invalid_topics:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid topics: {', '.join(invalid_topics)}"
        )

    # Update user profile
    user = MOCK_USERS[current_user]
    user["topics"] = request.topics
    user["customDescription"] = request.customDescription

    return {"message": "Profile updated successfully"}


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
async def get_articles(current_user: str = Depends(get_current_user)) -> List[ArticleResponse]:
    """Fetch all articles personalized for the user."""
    user = MOCK_USERS[current_user]
    user_topics = user["topics"]

    # Fetch all articles from database
    articles = await get_all_articles()

    # Filter by user's topics
    filtered_articles = filter_articles_by_topics(articles, user_topics)

    # Map to response format
    return [map_article_to_response(article, user_topics) for article in filtered_articles]


@app.get("/api/articles/{article_id}/")
async def get_article(
    article_id: str,
    current_user: str = Depends(get_current_user)
) -> ArticleResponse:
    """Fetch detailed information for a specific article."""
    user = MOCK_USERS[current_user]
    user_topics = user["topics"]

    # Fetch article from database
    article = await get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return map_article_to_response(article, user_topics)


# ============================================================================
# Chat Endpoints
# ============================================================================

@app.get("/api/articles/{article_id}/chat/")
async def get_chat_history(
    article_id: str,
    current_user: str = Depends(get_current_user)
) -> List[ChatMessage]:
    """Fetch chat history for a specific article."""
    # Get chat history for this article and user
    if article_id not in MOCK_CHATS:
        MOCK_CHATS[article_id] = {}

    if current_user not in MOCK_CHATS[article_id]:
        MOCK_CHATS[article_id][current_user] = []

    return MOCK_CHATS[article_id][current_user]


@app.post("/api/articles/{article_id}/chat/send")
async def send_chat_message(
    article_id: str,
    request: ChatMessageRequest,
    current_user: str = Depends(get_current_user)
) -> ChatResponse:
    """Send a chat message and receive AI response."""
    # Verify article exists
    article = await get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Initialize chat storage if needed
    if article_id not in MOCK_CHATS:
        MOCK_CHATS[article_id] = {}
    if current_user not in MOCK_CHATS[article_id]:
        MOCK_CHATS[article_id][current_user] = []

    # Store user message
    user_message = ChatMessage(
        id=str(uuid.uuid4()),
        role="user",
        content=request.message,
        timestamp=int(datetime.now().timestamp() * 1000),
    )
    MOCK_CHATS[article_id][current_user].append(user_message)

    # Generate mock AI response
    article_title = article["title"]
    mock_responses = [
        f"That's an interesting question about '{article_title}'. Based on the article, I can help you understand this topic better.",
        f"Great question! Regarding '{article_title}', let me explain...",
        f"From the article '{article_title}', we can see that this is a complex topic. Here's what you need to know...",
        f"I'd be happy to discuss '{article_title}' with you. The key points to consider are...",
    ]

    ai_response_text = random.choice(mock_responses)

    # Store AI response
    ai_message = ChatMessage(
        id=str(uuid.uuid4()),
        role="assistant",
        content=ai_response_text,
        timestamp=int(datetime.now().timestamp() * 1000),
    )
    MOCK_CHATS[article_id][current_user].append(ai_message)

    return ChatResponse(response=ai_response_text)


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with consistent JSON format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    print(f"FTL News API starting...")
    print(f"Database: {DB_PATH}")
    print(f"Mock authentication enabled (replace with real auth later)")
