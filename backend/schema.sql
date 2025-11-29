CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE IF NOT EXISTS "links" (
	"id"	INTEGER NOT NULL,
	"hn_id"	INTEGER UNIQUE,
	"title"	TEXT,
	"url"	TEXT,
	"score"	INTEGER,
	"time"	INTEGER,
	"author"	TEXT,
	"descendants"	INTEGER,
	"hnlink"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "contents" (
	"id"	INTEGER NOT NULL,
	"link_id"	INTEGER NOT NULL,
	"article"	TEXT,
	"comments"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    token TEXT UNIQUE,  -- Session token (nullable until user logs in)
    is_active INTEGER DEFAULT 1,  -- SQLite uses INTEGER for boolean (1=true, 0=false)
    is_email_verified INTEGER DEFAULT 1,  -- Default to true for now
    categories TEXT DEFAULT '',  -- Comma-separated category slugs
    custom_description TEXT DEFAULT '',
    created_at INTEGER NOT NULL,  -- Unix timestamp
    updated_at INTEGER NOT NULL   -- Unix timestamp
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_token ON users(token);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_article_id INTEGER NOT NULL,  -- FK to user_articles entry (not directly to user+article)
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp INTEGER NOT NULL,  -- Unix timestamp in milliseconds for ordering
    FOREIGN KEY (user_article_id) REFERENCES user_articles(id) ON DELETE CASCADE
);
CREATE INDEX idx_messages_user_article ON messages(user_article_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE TABLE IF NOT EXISTS "analysis" (
	"id"	INTEGER NOT NULL,
	"content_id"	INTEGER NOT NULL,
	"article_summary"	TEXT,
	"comments_summary"	TEXT,
	"categories"	TEXT,
	"scores"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "user_articles" (
	"id"	INTEGER,
	"user_id"	INTEGER NOT NULL,
	"article_id"	INTEGER NOT NULL,
	"is_read"	INTEGER DEFAULT 0,
	"created_at"	INTEGER NOT NULL,
	"matched_categories"	TEXT,
	"relevance_score"	NUMERIC, is_sent INTEGER DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("user_id","article_id"),
	FOREIGN KEY("article_id") REFERENCES "links"("id") ON DELETE CASCADE,
	FOREIGN KEY("user_id") REFERENCES "users"("id") ON DELETE CASCADE
);
CREATE INDEX idx_user_articles_article ON user_articles(article_id);
CREATE INDEX idx_user_articles_is_read ON user_articles(is_read);
CREATE INDEX idx_user_articles_user ON user_articles(user_id);
CREATE INDEX idx_user_articles_is_sent ON user_articles(is_sent);
