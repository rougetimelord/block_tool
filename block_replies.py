import json
import tweepy
from time import sleep

from tweepy.error import RateLimitError, TweepError
from main2 import (
    fileName,
    onboard,
    getID,
    connect,
    createBlocks,
    app_api,
    nameIDs,
)


def cursor_handled(cursor):
    while True:
        try:
            yield cursor.next()
        except RateLimitError:
            print("waiting out rate limit")
            sleep(15 * 60)
        except TweepError as e:
            if e.response.status_code == 429:
                print("waiting out rate limit")
                sleep(15 * 60)
            else:
                print(e.reason)
                return
        except StopIteration:
            return


def go():
    tweetURL = input("tweet url: ")
    tweetID = tweetURL.split("/")[-1]
    tweet = app_api.get_status(tweetID)
    tweet2ID = input("next tweet URL: ").split("/")[-1]
    if tweet2ID == "":
        tweet2ID = None

    users = set()
    for reply in cursor_handled(
        tweepy.Cursor(
            app_api.search,
            q=f"to:{tweet.author.screen_name}",
            since_id={tweet.id},
            maxID=tweet2ID,
        ).items()
    ):
        a = len(users)
        users.add(reply.author.id)
        if a != len(users):
            print(f"adding {reply.author.screen_name}")

    users = list(users)
    users_acct = []
    for user in users:
        users_acct.append({"id": user})

    username = input("block on: ")
    connect(username)
    createBlocks(nameIDs[username], users_acct)


if __name__ == "__main__":
    go()
