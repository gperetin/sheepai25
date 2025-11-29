import asyncio
import os
from apify_client import ApifyClientAsync
import aiosqlite

DB_PATH = "../data/db.sqlite"
BATCH_SIZE = 5
APIFY_ACTOR = "apify/website-content-crawler"
GORANS_APIFY_ACTOR = "aYG0l9s7dbB7j3gbS"

APIFY_RUN_INPUT = {
    # "startUrls": [{ "url": "https://docs.apify.com/academy/web-scraping-for-beginners" }],
    "useSitemaps": False,
    "respectRobotsTxtFile": True,
    "crawlerType": "playwright:adaptive",
    "includeUrlGlobs": [],
    "excludeUrlGlobs": [],
    "keepUrlFragments": False,
    "ignoreCanonicalUrl": False,
    "ignoreHttpsErrors": False,
    "maxCrawlDepth": 1,
    "maxCrawlPages": 1,
    "initialConcurrency": 0,
    "maxConcurrency": 2,
    "initialCookies": [],
    "customHttpHeaders": {},
    "signHttpRequests": False,
    "pageFunction": "",
    "proxyConfiguration": { "useApifyProxy": True },
    "maxSessionRotations": 10,
    "maxRequestRetries": 3,
    "requestTimeoutSecs": 60,
    "minFileDownloadSpeedKBps": 128,
    "dynamicContentWaitSecs": 10,
    "waitForSelector": "",
    "softWaitForSelector": "",
    "maxScrollHeightPixels": 5000,
    "keepElementsCssSelector": "",
    "removeElementsCssSelector": """nav, footer, script, style, noscript, svg, img[src^='data:'],
[role=\"alert\"],
[role=\"banner\"],
[role=\"dialog\"],
[role=\"alertdialog\"],
[role=\"region\"][aria-label*=\"skip\" i],
[aria-modal=\"true\"]""",
    "removeCookieWarnings": True,
    "blockMedia": True,
    "expandIframes": True,
    "clickElementsCssSelector": "[aria-expanded=\"false\"]",
    "htmlTransformer": "readableText",
    "readableTextCharThreshold": 100,
    "aggressivePrune": False,
    "debugMode": False,
    "storeSkippedUrls": False,
    "debugLog": False,
    "saveHtml": False,
    "saveHtmlAsFile": False,
    "saveMarkdown": True,
    "saveFiles": False,
    "saveScreenshots": False,
    "maxResults": 9999999,
    "clientSideMinChangePercentage": 15,
    "renderingTypeDetectionPercentage": 10,
}


async def get_links_to_crawl(db: aiosqlite.Connection) -> list[tuple[int, str]]:
    """Fetch all links from the database that haven't been crawled yet."""
    cursor = await db.execute(
        """
        SELECT l.id, l.url
        FROM links l
        JOIN contents c ON l.id = c.link_id
        WHERE c.article IS NULL
        """
    )
    rows = await cursor.fetchall()
    return [(row[0], row[1]) for row in rows]


async def crawl_url(client: ApifyClientAsync, url: str) -> str | None:
    """Crawl a single URL using Apify and return the article content."""

    run_input = APIFY_RUN_INPUT.copy()
    run_input["startUrls"] = [{"url": url}]

    run = await client.actor(GORANS_APIFY_ACTOR).call(run_input=run_input, memory_mbytes=2048)
    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        return None

    dataset_items = await client.dataset(dataset_id).list_items()
    items = dataset_items.items

    if items:
        return items[0].get("markdown", None)
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
        if article is None:
            continue

        await db.execute(
            "UPDATE contents SET article = ? WHERE link_id = ?",
            (article, link_id),
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
