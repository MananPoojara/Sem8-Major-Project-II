# agents/crewai_ingest_shim.py

import asyncio
import sys
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os, time, random, traceback
from pathlib import Path
from src.tools.news_tools import (
    download_image,
    make_pdf,
    extract_article_from_html,
    unique_pdf_name,
)
from playwright.sync_api import sync_playwright

# Output folder
OUT_DIR = Path("scraped_data/crewai")
OUT_DIR.mkdir(parents=True, exist_ok=True)

class CrewAIIngestShim:
    """
    Simulates a CrewAI ingestion framework that:
    1. Loads HTML
    2. Extracts title, body, image
    3. Generates a PDF and metadata
    """

    def __init__(self):
        self.framework = "crewai_shim"

    def stage1_normalize(self, html, url):
        """Extract and normalize metadata from HTML"""
        try:
            art = extract_article_from_html(html, base_url=url)
            return {
                "title": art.get("title"),
                "image_url": art.get("image_url"),
                "video_url": art.get("video_url"),
            }
        except Exception as e:
            print(f"[CrewAI] stage1_normalize failed for {url}: {e}")
            return {"title": None, "image_url": None}

    def stage2_create(self, html, url, prefix):
        """Generate PDF and structured metadata"""
        start = time.time()
        try:
            art = extract_article_from_html(html, base_url=url)
            title = art.get("title") or prefix
            body = art.get("text") or ""
            img_url = art.get("image_url")
            video_url = art.get("video_url")

            # download image if available
            img_path = download_image(img_url) if img_url else None

            # build pdf
            pdf_name = unique_pdf_name(prefix=prefix)
            pdf_path = str(OUT_DIR / pdf_name)
            pdf_size = make_pdf(title, url, body, img_path, video_url, pdf_path)

            latency = time.time() - start
            return {
                "framework": self.framework,
                "source_url": url,
                "title": title,
                "pdf_path": pdf_path,
                "pdf_bytes": pdf_size,
                "has_image": bool(img_path),
                "image_path": img_path,
                "text_length": len(body),
                "time_seconds": round(latency, 3),
            }

        except Exception as e:
            print(f"[CrewAI] stage2_create failed for {url}: {e}")
            traceback.print_exc()
            return {
                "framework": self.framework,
                "source_url": url,
                "error": str(e),
            }

    def process_batch(self, items):
        """Process list of HTML pages"""
        results = []
        for i, it in enumerate(items):
            print(f"🔍 Processing ({i+1}/{len(items)}) {it['url']}")
            norm = self.stage1_normalize(it["html"], it["url"])
            res = self.stage2_create(it["html"], it["url"], prefix=f"crew_{i}")
            res.update(norm)
            results.append(res)
        return results


def run_crewai_ingest(urls, max_items=3):
    """
    Headless scrape URLs with Playwright, then process with CrewAI shim.
    Uses DOMContentLoaded wait and retry logic for slow pages.
    """
    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
            ]),
            bypass_csp=True,
            java_script_enabled=True,
        )

        page = context.new_page()

        for idx, u in enumerate(urls[:max_items]):
            print(f"📰 Scraping article {idx+1}: {u}")
            success = False
            for attempt in range(2):  # two attempts per page
                try:
                    page.goto(u, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000 + int(2000 * random.random()))
                    html = page.content()
                    if "<html" in html.lower():
                        items.append({"url": u, "html": html})
                        success = True
                        break
                except Exception as e:
                    print(f"⚠️ Retry {attempt+1} failed for {u}: {e}")
                    page.wait_for_timeout(1500)
            if not success:
                print(f"[CrewAI] Skipping {u} after repeated timeouts.")

        browser.close()

    if not items:
        print("⚠️ No articles scraped successfully.")
        return []

    agent = CrewAIIngestShim()
    results = agent.process_batch(items)
    print(f"✅ CrewAI Ingestion completed for {len(results)} articles.")
    return results


# 🧪 Run directly for testing
if __name__ == "__main__":
    test_urls = [
        "https://timesofindia.indiatimes.com/city/noida/man-wanted-in-double-murder-case-arrested-in-noida/articleshow/125004909.cms",
        "https://timesofindia.indiatimes.com/city/ludhiana/man-arrested-in-murder-case-woman-booked/articleshow/125041249.cms"
    ]
    output = run_crewai_ingest(test_urls, max_items=2)
    for r in output:
        print(r)
