CREATE TABLE IF NOT EXISTS "contents" (
	"id"	INTEGER NOT NULL,
	"link_id"	INTEGER NOT NULL,
	"article"	TEXT,
	"comments"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE IF NOT EXISTS "analysis" (
	"id"	INTEGER NOT NULL,
	"content_id"	INTEGER NOT NULL,
	"article_summary"	TEXT,
	"comments_summary"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
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
