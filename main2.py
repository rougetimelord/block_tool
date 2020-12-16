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


def filterRunnerAPI(username):
    # Keep track of how many method switches have happened in a row,
    # if either method works this gets reset.
    global switchCounter

    try:
        app_api.get_user(screen_name=username)
        switchCounter = 0
        return [0, True]
    except tweepy.TweepError as e:
        if e.api_code == 50 or e.api_code == 63:
            switchCounter = 0
            return [1, True]

        elif e.response.status_code == 429:
            print("Switching method to Selenium")

            switchCounter += 1
            # If there are succesive switches just wait a bit
            if switchCounter >= 3:
                print("Waiting 5 minutes to switch")
                sleep(300)

            res = filterRunnerSelenium(username)
            res[1] = False
            return res
        else:
            print(e)
            return [0, True]


def filterRunnerSelenium(username):
    # Keep track of how many method switches have happened in a row,
    # if either method works this gets reset.
    global switchCounter

    driver.get(base + username)
    # Wait for the page to render
    sleep(0.5)

    try:
        elem = driver.find_element_by_css_selector(
            "div.css-1dbjc4n.r-15d164r.r-1g94qm0 > div > div > div.css-1dbjc4n.r-1awozwy.r-18u37iz.r-dnmrzs > div > span > span"
        )
    except NoSuchElementException:
        print("Switching method to API")

        # If there are succesive switches just wait a bit
        switchCounter += 1
        if switchCounter >= 3:
            print("Waiting 5 minutes to switch")
            sleep(300)

        res = filterRunnerAPI(username)
        res[1] = False
        return res

    # Debug print statement
    # print(driver.title, username, sep="::")
    switchCounter = 0
    if driver.title == "Profile / Twitter":
        return [1, True]
    return [0, True]


def filterBlockList(userID):
    with open(fileName(userID), "r") as f:
        userData = json.load(f)

    res = []
    print("filtering blocks")
    filterMethod = 1  # 0: Selenium, 1: API
    # The API method is much faster than the slenium based

    for acct in userData["block_list"]:
        if filterMethod == 0:
            filterResult = filterRunnerSelenium(acct["name"])
            if filterResult[0] == 0:
                res.append(acct)
            if not filterResult[1]:
                filterMethod = 1

        elif filterMethod == 1:
            filterResult = filterRunnerAPI(acct["name"])
            if filterResult[0] == 0:
                res.append(acct)
            if not filterResult[1]:
                filterMethod = 0

    userData["block_list"] = res
    print("returning %i blocks" % len(res))
    updateBlocks(userID, userData)
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

if "-filter" in sys.argv:
    from selenium import webdriver
    from selenium.common.exceptions import NoSuchElementException

    switchCounter = 0
    driver = webdriver.Chrome()
    base = "https://twitter.com/"
    filterBlockList(export_id)
    driver.close()

import_user = input("import username: ")
connect(import_user)
import_id = getID(import_user)
createBlocks(import_id, getBlockList(export_id))
