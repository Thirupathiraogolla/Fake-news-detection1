import json
import logging
import os
from pathlib import Path

from twython import TwythonRateLimitError

from util.Constants import GET_USER, GET_USER_TWEETS, USER_ID, FOLLOWERS, FOLLOWING, GET_FRIENDS_ID, GET_FOLLOWERS_ID
from util.TwythonConnector import TwythonConnector
from util.util import Config, is_folder_exists, create_dir, multiprocess_data_collection, DataCollector


def get_user_ids_in_folder(samples_folder):
    """Walk the news folders and collect unique user IDs from saved tweet JSON files."""
    user_ids = set()

    if not is_folder_exists(samples_folder):
        logging.warning("Folder does not exist, skipping user ID collection: %s", samples_folder)
        return user_ids

    for news_id in os.listdir(samples_folder):
        tweets_dir = os.path.join(samples_folder, news_id, "tweets")
        if not is_folder_exists(tweets_dir):
            continue

        for tweet_file in os.listdir(tweets_dir):
            tweet_path = os.path.join(tweets_dir, tweet_file)
            try:
                with open(tweet_path, "r", encoding="utf-8") as f:
                    tweet_object = json.load(f)
                # Fix: guard against missing 'user' key in tweet object
                uid = tweet_object.get("user", {}).get("id")
                if uid is not None:
                    user_ids.add(uid)
            except Exception:
                logging.exception("Could not read tweet file: %s", tweet_path)

    return user_ids


def dump_user_profile_job(user_id, save_location, twython_connector: TwythonConnector):
    out_file = os.path.join(save_location, "{}.json".format(user_id))
    if Path(out_file).is_file():
        return  # already collected

    profile_info = None
    try:
        profile_info = twython_connector.get_twython_connection(GET_USER).show_user(user_id=user_id)
    except TwythonRateLimitError:
        logging.exception("Rate limit hit fetching user profile for %s", user_id)
    except Exception:
        logging.exception("Exception fetching user profile for %s", user_id)

    if profile_info:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(profile_info, f, ensure_ascii=False, indent=2)


def dump_user_recent_tweets_job(user_id, save_location, twython_connector: TwythonConnector):
    out_file = os.path.join(save_location, "{}.json".format(user_id))
    if Path(out_file).is_file():
        return

    profile_info = None
    try:
        profile_info = twython_connector.get_twython_connection(GET_USER_TWEETS).get_user_timeline(
            user_id=user_id, count=200
        )
    except TwythonRateLimitError:
        logging.exception("Rate limit hit fetching timeline for %s", user_id)
    except Exception:
        logging.exception("Exception fetching timeline for %s", user_id)

    if profile_info:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(profile_info, f, ensure_ascii=False, indent=2)


def fetch_user_follower_ids(user_id, twython_connection):
    try:
        result = twython_connection.get_followers_ids(user_id=user_id)
        return result.get("ids", [])
    except Exception:
        logging.exception("Exception getting follower IDs for user: %s", user_id)
        return []


def fetch_user_friends_ids(user_id, twython_connection):
    try:
        result = twython_connection.get_friends_ids(user_id=user_id)
        return result.get("ids", [])
    except Exception:
        logging.exception("Exception getting friend IDs for user: %s", user_id)
        return []


def dump_user_followers(user_id, save_location, twython_connector: TwythonConnector):
    out_file = os.path.join(save_location, "{}.json".format(user_id))
    if Path(out_file).is_file():
        return

    try:
        ids = fetch_user_follower_ids(
            user_id, twython_connector.get_twython_connection(GET_FOLLOWERS_ID)
        )
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({USER_ID: user_id, FOLLOWERS: ids}, f, ensure_ascii=False, indent=2)
    except Exception:
        logging.exception("Exception saving follower IDs for user: %s", user_id)


def dump_user_following(user_id, save_location, twython_connector: TwythonConnector):
    out_file = os.path.join(save_location, "{}.json".format(user_id))
    if Path(out_file).is_file():
        return

    try:
        ids = fetch_user_friends_ids(
            user_id, twython_connector.get_twython_connection(GET_FRIENDS_ID)
        )
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({USER_ID: user_id, FOLLOWING: ids}, f, ensure_ascii=False, indent=2)
    except Exception:
        logging.exception("Exception saving following IDs for user: %s", user_id)


# ── Collector classes ──────────────────────────────────────────────────────────

class UserProfileCollector(DataCollector):
    def __init__(self, config):
        super().__init__(config)

    def collect_data(self, choices):
        all_user_ids = set()
        for choice in choices:
            folder = "{}/{}/{}".format(self.config.dump_location, choice["news_source"], choice["label"])
            all_user_ids.update(get_user_ids_in_folder(folder))

        folder = "{}/user_profiles".format(self.config.dump_location)
        create_dir(folder)
        multiprocess_data_collection(
            dump_user_profile_job, list(all_user_ids),
            (folder, self.config.twython_connector), self.config
        )


class UserTimelineTweetsCollector(DataCollector):
    def __init__(self, config):
        super().__init__(config)

    def collect_data(self, choices):
        all_user_ids = set()
        for choice in choices:
            folder = "{}/{}/{}".format(self.config.dump_location, choice["news_source"], choice["label"])
            all_user_ids.update(get_user_ids_in_folder(folder))

        folder = "{}/user_timeline_tweets".format(self.config.dump_location)
        create_dir(folder)
        multiprocess_data_collection(
            dump_user_recent_tweets_job, list(all_user_ids),
            (folder, self.config.twython_connector), self.config
        )


class UserFollowersCollector(DataCollector):
    def __init__(self, config):
        super().__init__(config)

    def collect_data(self, choices):
        all_user_ids = set()
        for choice in choices:
            folder = "{}/{}/{}".format(self.config.dump_location, choice["news_source"], choice["label"])
            all_user_ids.update(get_user_ids_in_folder(folder))

        folder = "{}/user_followers".format(self.config.dump_location)
        create_dir(folder)
        multiprocess_data_collection(
            dump_user_followers, list(all_user_ids),
            (folder, self.config.twython_connector), self.config
        )


class UserFollowingCollector(DataCollector):
    def __init__(self, config):
        super().__init__(config)

    def collect_data(self, choices):
        all_user_ids = set()
        for choice in choices:
            folder = "{}/{}/{}".format(self.config.dump_location, choice["news_source"], choice["label"])
            all_user_ids.update(get_user_ids_in_folder(folder))

        folder = "{}/user_following".format(self.config.dump_location)
        create_dir(folder)
        multiprocess_data_collection(
            dump_user_following, list(all_user_ids),
            (folder, self.config.twython_connector), self.config
        )
