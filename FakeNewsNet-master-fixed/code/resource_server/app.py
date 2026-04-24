import json
import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

from resource_server.ResourceAllocator import ResourceAllocator

app = Flask(__name__)
CORS(app)

keys_state = {}


def init_state(num_keys):
    print("Initialising resource server with {} Twitter key(s)".format(num_keys))
    keys_state["get_retweet"]             = ResourceAllocator(num_keys, time_window=905,  window_limit=75)
    keys_state["get_tweet"]               = ResourceAllocator(num_keys, time_window=905,  window_limit=900)
    keys_state["get_follower_friends_ids"]= ResourceAllocator(num_keys, time_window=920,  window_limit=15)
    keys_state["get_followers_ids"]       = ResourceAllocator(num_keys, time_window=900,  window_limit=15)
    keys_state["get_friends_ids"]         = ResourceAllocator(num_keys, time_window=900,  window_limit=15)
    keys_state["get_user"]                = ResourceAllocator(num_keys, time_window=905,  window_limit=900)
    keys_state["get_user_tweets"]         = ResourceAllocator(num_keys, time_window=925,  window_limit=900)


@app.route("/get-keys", methods=["GET"])
def get_key_index():
    resource_type = request.args.get("resource_type")

    # Fix: return a proper 400 if the required query param is missing
    if not resource_type:
        return jsonify({"status": 400, "error": "Missing resource_type parameter"}), 400

    allocator = keys_state.get(resource_type)
    # Fix: return 404 for unknown resource types instead of raising an unhandled exception
    if allocator is None:
        return jsonify({"status": 404, "error": "Unknown resource_type: {}".format(resource_type)}), 404

    try:
        resource_index = allocator.get_resource_index()
        if resource_index < 0:
            return jsonify({"status": 404, "wait_time": abs(resource_index)})
        return jsonify({"status": 200, "id": resource_index})
    except Exception as ex:
        app.logger.exception("Error in get_key_index")
        return jsonify({"status": 500, "error": str(ex)}), 500


def get_num_keys():
    # Fix: resolve config.json relative to this file so it works regardless of CWD
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return int(data["num_twitter_keys"])


if __name__ == "__main__":
    init_state(get_num_keys())
    app.run(host="0.0.0.0", port=5000, debug=False)
