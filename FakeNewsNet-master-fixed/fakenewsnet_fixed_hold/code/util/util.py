import csv
import errno
import logging
import os
import sys
from multiprocessing.pool import Pool

from tqdm import tqdm

from util.TwythonConnector import TwythonConnector


class News:

    def __init__(self, info_dict, label, news_platform):
        self.news_id = info_dict["id"]
        self.news_url = info_dict["news_url"]
        self.news_title = info_dict["title"]
        self.tweet_ids = []

        try:
            # Fix: strip whitespace before splitting to handle trailing \t or spaces
            raw = info_dict.get("tweet_ids", "").strip()
            if raw:
                self.tweet_ids = [int(tid) for tid in raw.split("\t") if tid.strip()]
        except (ValueError, AttributeError):
            logging.warning("Could not parse tweet_ids for news_id=%s", self.news_id)

        self.label = label
        self.platform = news_platform


class Config:

    def __init__(self, data_dir, data_collection_dir, tweet_keys_file, num_process):
        self.dataset_dir = data_dir
        self.dump_location = data_collection_dir
        self.tweet_keys_file = tweet_keys_file
        self.num_process = num_process

        # Fix: resolve tweet_keys_file relative to the code/ directory so it always works
        if not os.path.isabs(tweet_keys_file):
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            tweet_keys_file = os.path.join(base, tweet_keys_file)

        self.twython_connector = TwythonConnector("localhost:5000", tweet_keys_file)


class DataCollector:

    def __init__(self, config):
        self.config = config

    def collect_data(self, choices):
        pass

    def load_news_file(self, data_choice):
        # Fix: handle CSV files with very large fields (OverflowError on Windows)
        max_int = sys.maxsize
        while True:
            try:
                csv.field_size_limit(max_int)
                break
            except OverflowError:
                max_int = int(max_int / 10)

        news_list = []
        file_path = "{}/{}_{}.csv".format(
            self.config.dataset_dir,
            data_choice["news_source"],
            data_choice["label"],
        )

        if not os.path.exists(file_path):
            logging.error("Dataset file not found: %s", file_path)
            return news_list

        with open(file_path, encoding="UTF-8", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Fix: skip rows with missing mandatory fields instead of crashing
                if not row.get("id") or not row.get("news_url"):
                    logging.warning("Skipping row with missing id or news_url: %s", row)
                    continue
                news_list.append(News(row, data_choice["label"], data_choice["news_source"]))

        logging.info("Loaded %d news items from %s", len(news_list), file_path)
        return news_list


def create_dir(dir_name):
    if not os.path.exists(dir_name):
        try:
            os.makedirs(dir_name)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise


def is_folder_exists(folder_name):
    return os.path.exists(folder_name)


def equal_chunks(lst, chunk_size):
    """Return successive chunk_size-sized chunks from lst."""
    # Fix: renamed parameter from 'list' (shadows built-in) to 'lst'
    chunks = []
    for i in range(0, len(lst), chunk_size):
        chunks.append(lst[i : i + chunk_size])
    return chunks


def multiprocess_data_collection(function_reference, data_list, args, config: Config):
    """Run function_reference over data_list using a multiprocessing pool."""
    if not data_list:
        logging.info("multiprocess_data_collection: data_list is empty, skipping.")
        return

    pool = Pool(config.num_process)
    pbar = tqdm(total=len(data_list))

    def update(_):
        pbar.update()

    # Fix: correct loop range — was iterating pbar.total times with index i
    # but only the first pbar.total items of data_list were submitted
    results = []
    for item in data_list:
        r = pool.apply_async(function_reference, args=(item,) + args, callback=update)
        results.append(r)

    pool.close()
    pool.join()
    pbar.close()

    # Collect exceptions so errors are visible
    for r in results:
        try:
            r.get()
        except Exception:
            logging.exception("Exception in worker process")
