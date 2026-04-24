import csv
import json
import logging
import os
import sys
import time

# Fix: use absolute-style imports so the script runs correctly from the code/ directory
from util.util import Config, News
from news_content_collection import NewsContentCollector
from retweet_collection import RetweetCollector
from tweet_collection import TweetCollector
from user_profile_collection import (
    UserProfileCollector,
    UserTimelineTweetsCollector,
    UserFollowingCollector,
    UserFollowersCollector,
)


class DataCollectorFactory:

    def __init__(self, config):
        self.config = config

    def get_collector_object(self, feature_type):
        collectors = {
            "news_articles":        NewsContentCollector,
            "tweets":               TweetCollector,
            "retweets":             RetweetCollector,
            "user_profile":         UserProfileCollector,
            "user_timeline_tweets": UserTimelineTweetsCollector,
            "user_following":       UserFollowingCollector,
            "user_followers":       UserFollowersCollector,
        }
        cls = collectors.get(feature_type)
        if cls is None:
            logging.warning("Unknown feature type: %s", feature_type)
            return None
        return cls(self.config)


def init_config():
    # Fix: use __file__-relative path so config.json is always found regardless of CWD
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        json_object = json.load(f)

    config = Config(
        json_object["dataset_dir"],
        json_object["dump_location"],
        json_object["tweet_keys_file"],
        int(json_object["num_process"]),
    )

    data_choices = json_object["data_collection_choice"]
    data_features_to_collect = json_object["data_features_to_collect"]

    return config, data_choices, data_features_to_collect


def init_logging(config):
    log_format = "%(asctime)s %(process)d %(module)s %(levelname)s %(message)s"
    logging.basicConfig(
        filename="data_collection_{}.log".format(int(time.time())),
        level=logging.INFO,
        format=log_format,
    )
    logging.getLogger("requests").setLevel(logging.CRITICAL)
    # Also log to console so the user can see progress
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(console)


def download_dataset():
    config, data_choices, data_features_to_collect = init_config()
    init_logging(config)
    data_collector_factory = DataCollectorFactory(config)

    for feature_type in data_features_to_collect:
        logging.info("Starting collection for feature: %s", feature_type)
        data_collector = data_collector_factory.get_collector_object(feature_type)
        if data_collector is not None:
            data_collector.collect_data(data_choices)
        logging.info("Finished collection for feature: %s", feature_type)


if __name__ == "__main__":
    download_dataset()
