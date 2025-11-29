import asyncio
import os
from apify_client import ApifyClientAsync
import aiosqlite

DB_PATH = "../data/db.sqlite"
BATCH_SIZE = 20
APIFY_ACTOR = "apify/website-content-crawler"


async def get_links_to_crawl(db: aiosqlite.Connection) -> list[tuple[int, str]]:
    """Fetch all links from the database that haven't been crawled yet."""
    cursor = await db.execute(
        """
        SELECT l.id, l.url
        FROM links l
        LEFT JOIN contents c ON l.id = c.link_id
        WHERE c.id IS NULL
        """
    )
    rows = await cursor.fetchall()
    return [(row[0], row[1]) for row in rows]


async def crawl_url(client: ApifyClientAsync, url: str) -> str | None:
    """Crawl a single URL using Apify and return the article content."""
    run_input = {
        "startUrls": [{"url": url}],
        "maxCrawlPages": 1,
        "crawlerType": "cheerio",
    }

    run = await client.actor(APIFY_ACTOR).call(run_input=run_input)
    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        return None

    dataset_items = await client.dataset(dataset_id).list_items()
    items = dataset_items.items

    if items:
        return items[0].get("text", "")
    return None


async def crawl_batch(
    client: ApifyClientAsync, batch: list[tuple[int, str]]
) -> list[tuple[int, str | None]]:
    """Crawl a batch of URLs concurrently."""
    tasks = [crawl_url(client, url) for _, url in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    crawl_results = []
    for (link_id, url), result in zip(batch, results):
        if isinstance(result, Exception):
            print(f"Error crawling {url}: {result}")
            crawl_results.append((link_id, None))
        else:
            crawl_results.append((link_id, result))

    return crawl_results


async def store_results(
    db: aiosqlite.Connection, results: list[tuple[int, str | None]]
) -> None:
    """Store crawl results in the contents table."""
    for link_id, article in results:
        await db.execute(
            "INSERT INTO contents (link_id, article) VALUES (?, ?)",
            (link_id, article),
        )
    await db.commit()


async def main() -> None:
    api_token = os.environ.get("APIFY_API_TOKEN")
    if not api_token:
        raise RuntimeError("APIFY_API_TOKEN environment variable is required")

    async with aiosqlite.connect(DB_PATH) as db:
        links = await get_links_to_crawl(db)
        print(f"Found {len(links)} links to crawl")

        if not links:
            print("No links to crawl")
            return

        client = ApifyClientAsync(api_token)
        for i in range(0, len(links), BATCH_SIZE):
            batch = links[i : i + BATCH_SIZE]
            print(f"Processing batch {i // BATCH_SIZE + 1} ({len(batch)} links)")

            results = await crawl_batch(client, batch)
            await store_results(db, results)

            successful = sum(1 for _, content in results if content)
            print(f"Batch complete: {successful}/{len(batch)} successful")

    print("Crawling complete")


if __name__ == "__main__":
    asyncio.run(main())
