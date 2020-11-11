import json, sys
import tweepy
import os.path
from tweepy import cursor
from time import sleep

from tweepy.error import TweepError

try:
    with open("key.json", "r") as f:
        app_key = json.load(f)
        _ = tweepy.AppAuthHandler(
            consumer_key=app_key["con_t"], consumer_secret=app_key["con_s"]
        )
        app_api = tweepy.API(_)
        userAPIs = {}
        nameIDs = {}
        print("loaded app keys")
except IOError:
    print("No key.json found")
    exit()


def fileName(userID):
    return "%s_data.json" % userID


def onboard(userID, acc_t, acc_ts):
    data = {
        "acc_t": acc_t,
        "acc_ts": acc_ts,
        "block_list": [],
        "last_cursor": -1,
    }
    with open(fileName(userID), "w+") as f:
        json.dump(data, f)
    return


def getID(username):
    if username in nameIDs:
        return nameIDs[username]
    return None


def connect(username):
    userID = app_api.get_user(screen_name=username).id
    auth = tweepy.OAuthHandler(
        consumer_key=app_key["con_t"],
        consumer_secret=app_key["con_s"],
        callback="https://auth.r0uge.org",
    )
    if os.path.isfile(fileName(userID)):
        print("got cached key for %s" % username)
        with open(fileName(userID), "r") as f:
            userKey = json.load(f)
        auth.set_access_token(userKey["acc_t"], userKey["acc_ts"])
    else:
        print("onboarding %s" % username)
        try:
            url = auth.get_authorization_url()
            print("go to %s on %s" % (url, username))
        except tweepy.TweepError:
            print("failed to get url")
            exit()
        verifier = input("verifier: ")
        try:
            auth.get_access_token(verifier)
        except tweepy.TweepError:
            print("failed verifier check")
            exit()
        onboard(userID, auth.access_token, auth.access_token_secret)
    userAPIs[userID] = tweepy.API(auth)
    nameIDs[username] = userID
    return


def updateBlocks(userID, userData):
    with open(fileName(userID), "w") as f:
        json.dump(userData, f)
    return


def filterBlockList(block_list):
    res = []
    print("filtering blocks")
    for acct in block_list:
        try:
            app_api.get_user(user_id=acct["id"])
            res.append(acct)
        except tweepy.TweepError as e:
            if e.api_code == 50 or e.api_code == 63:
                continue
            elif e.response.status_code == 429:
                res.append(acct)
                print("waiting out get user")
                sleep(300)
                continue
            else:
                print(e)
                res.append(acct)
                continue
    print("returning %i blocks" % len(res))
    return res


def getBlocks(userID):
    with open(fileName(userID), "r") as f:
        userData = json.load(f)
    cursor = -1
    block_list = []
    while cursor != 0:
        try:
            block_list_resp = userAPIs[userID].blocks(cursor)
            for user in block_list_resp[0]:
                block_list.append({"name": user.screen_name, "id": user.id})
            cursor = block_list_resp[1][1]
        except tweepy.TweepError as e:
            if e.response.status_code == 429:
                print("waiting out get blocks")
                sleep(300)
                continue
            else:
                print(e.reason)
                break
    [
        userData["block_list"].append(entry)
        for entry in block_list
        if entry not in userData["block_list"]
    ]
    if "-filter" in sys.argv:
        userData["block_list"] = filterBlockList(userData["block_list"])
    updateBlocks(userID, userData)
    return


def getBlockList(userID):
    with open(fileName(userID), "r") as f:
        return json.load(f)["block_list"]


def createBlocks(userID, blockList):
    for acct in blockList:
        try:
            userAPIs[userID].create_block(
                user_id=acct["id"], skip_status=True, include_entities=False
            )
        except tweepy.TweepError as e:
            print(e)
    return


export_user = input("export username: ")
connect(export_user)
export_id = getID(export_user)
if "-sb" not in sys.argv:
    getBlocks(export_id)

import_user = input("import username: ")
connect(import_user)
import_id = getID(import_user)
createBlocks(import_id, getBlockList(export_id))
