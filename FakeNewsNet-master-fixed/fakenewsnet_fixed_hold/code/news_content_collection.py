import json
import logging
import os
import time

import requests
from tqdm import tqdm
from newspaper import Article

from util.util import DataCollector, Config, create_dir


def crawl_link_article(url):
    """Download and parse an article from url. Returns a dict or None on failure."""
    result_json = None

    try:
        # Fix: normalise URLs that are missing the scheme
        if not url.startswith("http"):
            url = url.lstrip("/")
            candidate_urls = ["http://" + url, "https://" + url]
        else:
            candidate_urls = [url]

        article = None
        for candidate in candidate_urls:
            try:
                a = Article(candidate)
                a.download()
                time.sleep(2)
                a.parse()
                if a.is_parsed:
                    article = a
                    break
            except Exception:
                logging.debug("Failed to fetch %s", candidate)

        if article is None or not article.is_parsed:
            return None

        result_json = {
            "url":            url,
            "text":           article.text,
            "images":         list(article.images),
            "top_img":        article.top_image,
            "keywords":       article.keywords,
            "authors":        article.authors,
            "canonical_link": article.canonical_link,
            "title":          article.title,
            "meta_data":      article.meta_data,
            "movies":         article.movies,
            # Fix: safely convert publish_date to epoch (was crashing on None)
            "publish_date":   _safe_epoch(article.publish_date),
            "source":         article.source_url,
            "summary":        article.summary,
        }

    except Exception:
        logging.exception("Exception fetching article from URL: %s", url)

    return result_json


def _safe_epoch(time_obj):
    """Convert a datetime to epoch float, returning None safely."""
    try:
        return time_obj.timestamp() if time_obj else None
    except Exception:
        return None


def get_web_archive_results(search_url):
    """Query the Wayback Machine CDX API for cached versions of search_url."""
    try:
        archive_url = (
            "http://web.archive.org/cdx/search/cdx?url={}&output=json".format(search_url)
        )
        response = requests.get(archive_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data[1:] if len(data) > 1 else None   # Fix: skip header row safely
    except Exception:
        logging.debug("Web archive lookup failed for %s", search_url)
        return None


def get_website_url_from_archive(url):
    """Return the earliest Wayback Machine URL for the given URL, or None."""
    results = get_web_archive_results(url)
    if results:
        return "https://web.archive.org/web/{}/{}".format(results[0][1], results[0][2])
    return None


def crawl_news_article(url):
    """Try to fetch the article directly; fall back to Web Archive if unavailable."""
    news_article = crawl_link_article(url)
    if news_article is None:
        archive_url = get_website_url_from_archive(url)
        if archive_url:
            news_article = crawl_link_article(archive_url)
    return news_article


def collect_news_articles(news_list, news_source, label, config: Config):
    create_dir(config.dump_location)
    create_dir("{}/{}".format(config.dump_location, news_source))
    create_dir("{}/{}/{}".format(config.dump_location, news_source, label))

    save_dir = "{}/{}/{}".format(config.dump_location, news_source, label)

    for news in tqdm(news_list, desc="{}/{} articles".format(news_source, label)):
        news_dir = "{}/{}".format(save_dir, news.news_id)
        create_dir(news_dir)

        # Fix: use os.path.join and a safe filename (no spaces)
        out_file = os.path.join(news_dir, "news_content.json")

        # Skip if already collected
        if os.path.exists(out_file):
            continue

        news_article = crawl_news_article(news.news_url)
        if news_article:
            with open(out_file, "w", encoding="UTF-8") as f:
                json.dump(news_article, f, ensure_ascii=False, indent=2, default=str)


class NewsContentCollector(DataCollector):

    def __init__(self, config):
        super().__init__(config)

    def collect_data(self, choices):
        for choice in choices:
            news_list = self.load_news_file(choice)
            collect_news_articles(
                news_list, choice["news_source"], choice["label"], self.config
            )
