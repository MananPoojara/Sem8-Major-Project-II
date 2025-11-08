import os
import time
import random
import pandas as pd
from multiprocessing import Process, Queue
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from src.tools.news_tools import (
    make_pdf,
    unique_pdf_name,
    download_image,
)

# ============================================================
# WINDOWS-SAFE PLAYWRIGHT WRAPPER
# ============================================================

def _playwright_worker(target_func, q, *args, **kwargs):
    try:
        with sync_playwright() as p:
            result = target_func(p, *args, **kwargs)
            q.put(result)
    except Exception as e:
        q.put(e)


def run_playwright_task(target_func, *args, **kwargs):
    q = Queue()
    proc = Process(target=_playwright_worker, args=(target_func, q, *args), kwargs=kwargs)
    proc.start()
    proc.join()

    if not q.empty():
        res = q.get()
        if isinstance(res, Exception):
            raise res
        return res
    raise RuntimeError("No result returned from Playwright process.")

# ============================================================
# SCRAPER: TIMES OF INDIA ONLY
# ============================================================

def scrape_timesofindia(p, topic="murder case", max_items=5):
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    base = "https://timesofindia.indiatimes.com"
    articles = []

    search_term = topic.replace(" ", "-")

    for i in range(1, 4):
        url = f"{base}/topic/{search_term}?page={i}"
        print(f"📰 Scraping Times of India page {i}: {url}")
        try:
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            time.sleep(random.uniform(3, 5))
        except Exception as e:
            print(f"⚠️ Timeout or navigation error: {e}")
            continue

        soup = BeautifulSoup(page.content(), "html.parser")
        for a in soup.select("a[href*='/articleshow/']"):
            href = a.get("href")
            title = a.get_text(strip=True)
            if href and len(title) > 20:
                full_url = href if href.startswith("http") else base + href
                articles.append({"title": title, "url": full_url})

        time.sleep(random.uniform(2, 4))

    browser.close()
    unique_articles = {a["url"]: a for a in articles}.values()
    print(f"✅ Found {len(unique_articles)} unique articles.")
    return list(unique_articles)[:max_items]

# ============================================================
# ARTICLE DETAIL SCRAPER
# ============================================================

def scrape_toi_article(p, article):
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    url = article["url"]

    print(f"📄 Opening article: {url}")
    try:
        page.goto(url, timeout=120000, wait_until="domcontentloaded")
        time.sleep(random.uniform(3, 6))
        html = page.content()
    except Exception as e:
        browser.close()
        raise RuntimeError(f"Failed to load article {url}: {e}")

    browser.close()
    soup = BeautifulSoup(html, "html.parser")

    # ✅ Extract title and content using your provided selectors
    title_tag = soup.select_one("h1.HNMDR, h1.HNMDF")
    body_tag = soup.select_one("div[data-articlebody]")

    title = title_tag.get_text(strip=True) if title_tag else article["title"]
    text = body_tag.get_text(" ", strip=True) if body_tag else ""
    img_tag = soup.select_one("div[data-articlebody] img")
    img_url = img_tag.get("src") if img_tag else None

    img_path = download_image(img_url) if img_url else None
    pdf_path = os.path.join("scraped_data", "pdfs", unique_pdf_name("toi"))

    make_pdf(title, url, text, img_path, None, pdf_path)

    return {
        **article,
        "pdf_path": pdf_path,
        "image_path": img_path,
        "text_length": len(text),
        "text_snippet": text[:400],
    }

# ============================================================
# MAIN EXECUTION
# ============================================================

def run_langchain_ingest(keywords="murder case", max_items=3):
    print("Starting LangChain Ingestion Agent :)) (Times of India only) ")

    # Ensure keywords is a string
    if isinstance(keywords, list):
        keywords = " ".join(keywords)

    # Step 1: Collect article links
    articles = run_playwright_task(scrape_timesofindia, keywords, max_items)
    print(f"Collected {len(articles)} article URLs")

    # Step 2: Deep scrape articles
    results = []
    for idx, art in enumerate(articles):
        print(f"Hang In There ({idx+1}/{len(articles)}) Scraping article ...")
        try:
            res = run_playwright_task(scrape_toi_article, art)
            results.append(res)
        except Exception as e:
            print(f"Error scraping!!!!!! {art['url']}: {e}")
        time.sleep(random.uniform(2, 4))

    # Step 3: Save CSV
    if results:
        df = pd.DataFrame(results)
        os.makedirs("scraped_data", exist_ok=True)
        df.to_csv("scraped_data/langchain_toi_results.csv", index=False)
        print("Results saved to scraped_data/langchain_toi_results.csv")
    else:
        print("No articles processed successfully.")

    return results


if __name__ == "__main__":
    run_langchain_ingest("murder case", max_items=3)
