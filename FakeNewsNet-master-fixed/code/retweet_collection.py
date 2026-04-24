import json
import logging
import os

from twython import TwythonRateLimitError

from tweet_collection import Tweet
from util.TwythonConnector import TwythonConnector
from util.util import create_dir, Config, multiprocess_data_collection, DataCollector
from util import Constants


def dump_retweets_job(tweet: Tweet, config: Config, twython_connector: TwythonConnector):
    retweets = []
    try:
        connection = twython_connector.get_twython_connection(Constants.GET_RETWEET)
        retweets = connection.get_retweets(id=tweet.tweet_id, count=100, cursor=-1)

    except TwythonRateLimitError:
        logging.exception("Twitter API rate limit hit — tweet id: %s", tweet.tweet_id)
    except Exception:
        logging.exception("Exception getting retweets for tweet id %s", tweet.tweet_id)

    dump_dir    = "{}/{}/{}/{}".format(config.dump_location, tweet.news_source, tweet.label, tweet.news_id)
    retweet_dir = "{}/retweets".format(dump_dir)
    create_dir(dump_dir)
    create_dir(retweet_dir)

    out_file = "{}/{}.json".format(retweet_dir, tweet.tweet_id)
    # Fix: skip if already saved to avoid redundant API calls on re-runs
    if not os.path.exists(out_file):
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({"retweets": retweets}, f, ensure_ascii=False, indent=2)


def collect_retweets(news_list, news_source, label, config: Config):
    create_dir(config.dump_location)
    create_dir("{}/{}".format(config.dump_location, news_source))
    create_dir("{}/{}/{}".format(config.dump_location, news_source, label))

    tweet_id_list = [
        Tweet(tweet_id, news.news_id, news_source, label)
        for news in news_list
        for tweet_id in news.tweet_ids
    ]

    if not tweet_id_list:
        logging.info("No tweet IDs found for retweet collection: %s/%s", news_source, label)
        return

    multiprocess_data_collection(
        dump_retweets_job, tweet_id_list, (config, config.twython_connector), config
    )


class RetweetCollector(DataCollector):

    def __init__(self, config):
        super().__init__(config)

    def collect_data(self, choices):
        for choice in choices:
            news_list = self.load_news_file(choice)
            collect_retweets(news_list, choice["news_source"], choice["label"], self.config)
