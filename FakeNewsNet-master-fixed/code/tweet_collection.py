import json
import logging

from twython import TwythonRateLimitError

from util.TwythonConnector import TwythonConnector
from util.util import create_dir, Config, multiprocess_data_collection, DataCollector, equal_chunks
from util import Constants


class Tweet:

    def __init__(self, tweet_id, news_id, news_source, label):
        self.tweet_id = tweet_id
        self.news_id = news_id
        self.news_source = news_source
        self.label = label


def dump_tweet_information(tweet_chunk: list, config: Config, twython_connector: TwythonConnector):
    """Collect and save info for a chunk of up to 100 tweets."""
    tweet_id_list = [tweet.tweet_id for tweet in tweet_chunk]

    try:
        tweet_objects_map = (
            twython_connector
            .get_twython_connection(Constants.GET_TWEET)
            .lookup_status(id=tweet_id_list, include_entities=True, map=True)["id"]
        )

        for tweet in tweet_chunk:
            tweet_object = tweet_objects_map.get(str(tweet.tweet_id))
            if not tweet_object:
                continue

            dump_dir  = "{}/{}/{}/{}".format(config.dump_location, tweet.news_source, tweet.label, tweet.news_id)
            tweet_dir = "{}/tweets".format(dump_dir)
            create_dir(dump_dir)
            create_dir(tweet_dir)

            out_file = "{}/{}.json".format(tweet_dir, tweet.tweet_id)
            # Fix: skip if already saved
            if not __import__("os").path.exists(out_file):
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(tweet_object, f, ensure_ascii=False, indent=2)

    except TwythonRateLimitError:
        logging.exception("Twitter API rate limit hit while collecting tweets")
    except Exception:
        logging.exception("Exception collecting tweet objects for chunk of %d tweets", len(tweet_chunk))


def collect_tweets(news_list, news_source, label, config: Config):
    create_dir(config.dump_location)
    create_dir("{}/{}".format(config.dump_location, news_source))
    create_dir("{}/{}/{}".format(config.dump_location, news_source, label))

    tweet_id_list = [
        Tweet(tweet_id, news.news_id, news_source, label)
        for news in news_list
        for tweet_id in news.tweet_ids
    ]

    if not tweet_id_list:
        logging.info("No tweet IDs found for %s/%s", news_source, label)
        return

    tweet_chunks = equal_chunks(tweet_id_list, 100)
    multiprocess_data_collection(
        dump_tweet_information, tweet_chunks, (config, config.twython_connector), config
    )


class TweetCollector(DataCollector):

    def __init__(self, config):
        super().__init__(config)

    def collect_data(self, choices):
        for choice in choices:
            news_list = self.load_news_file(choice)
            collect_tweets(news_list, choice["news_source"], choice["label"], self.config)
