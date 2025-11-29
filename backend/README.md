# Backend for FTL2 news engine

This directory holds the source code for the backend service for
FTL2 news engine. The engine scrapes news sources (currently only
Hacker News is supported), summarizes and analyses the articles
and comments, notifies subscribers about new articles matching
their interests (categories) and allows them to read and "chat with"
the article (through an AI chatbot).

The data is stored in the SQLite database.

## Digest procedure

Phases:

1. Ingest
2. Scrape content and comments
3. Analyze
4. Send digest emails
