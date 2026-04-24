import json
import logging
import os
import time

import requests
from twython import Twython


class TwythonConnector:

    def __init__(self, keys_server_url, key_file):
        self.streams = []
        self.url = "http://" + keys_server_url + "/get-keys?resource_type="
        self.max_fail_count = 3

        # Fix: check that the keys file actually exists before trying to open it
        if not os.path.exists(key_file):
            logging.warning(
                "Twitter keys file not found at '%s'. "
                "Tweet/retweet/user collection will not work without valid Twitter API keys.",
                key_file,
            )
            return

        self.init_twython_objects(key_file)

    def init_twython_objects(self, keys_file):
        """Read the keys file and initialise an array of Twython objects."""
        with open(keys_file, "r", encoding="utf-8") as f:
            keys = json.load(f)

        for key in keys:
            try:
                self.streams.append(
                    self._get_twitter_connection(
                        connection_mode=1,
                        app_key=key["app_key"],
                        app_secret=key["app_secret"],
                        oauth_token=key["oauth_token"],
                        oauth_token_secret=key["oauth_token_secret"],
                    )
                )
            except Exception:
                logging.exception("Failed to initialise Twython object for key: %s", key.get("app_key"))

    @staticmethod
    def _get_twitter_connection(
        connection_mode=1,
        app_key=None,
        app_secret=None,
        oauth_token=None,
        oauth_token_secret=None,
    ):
        client_args = {"timeout": 30}

        if connection_mode == 1:  # User auth mode
            return Twython(
                app_key=app_key,
                app_secret=app_secret,
                oauth_token=oauth_token,
                oauth_token_secret=oauth_token_secret,
                client_args=client_args,
            )

        elif connection_mode == 0:  # App auth mode
            twitter = Twython(app_key, app_secret, oauth_version=2)
            access_token = twitter.obtain_access_token()
            return Twython(app_key, access_token=access_token, client_args=client_args)

    def get_twython_connection(self, resource_type):
        """Return the Twython object for making requests, sleeping if rate-limited."""
        resource_index = self.get_resource_index(resource_type)
        return self.streams[resource_index]

    def get_resource_index(self, resource_type):
        fail_count = 0
        while True:
            try:
                response = requests.get(self.url + resource_type, timeout=10)
                # Fix: check HTTP status before parsing JSON
                response.raise_for_status()
                data = response.json()

                if data.get("status") == 200:
                    logging.info("Resource allocated: id=%s", data["id"])
                    return data["id"]
                else:
                    wait = data.get("wait_time", 60)
                    logging.info("Rate limited — sleeping for %d seconds", wait)
                    time.sleep(wait)

            except requests.exceptions.RequestException:
                fail_count += 1
                logging.exception(
                    "Resource server request failed (attempt %d/%d)",
                    fail_count,
                    self.max_fail_count,
                )
                if fail_count >= self.max_fail_count:
                    raise RuntimeError(
                        "Resource server at {} is unreachable after {} attempts. "
                        "Make sure you have started resource_server/app.py first.".format(
                            self.url, self.max_fail_count
                        )
                    )
                time.sleep(5)
