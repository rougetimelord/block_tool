import json, sys, tweepy, os.path
from time import sleep

# Load up keys
try:
    with open("key.json", "r") as f:
        app_key = json.load(f)
        _ = tweepy.AppAuthHandler(
            consumer_key=app_key["con_t"], consumer_secret=app_key["con_s"]
        )
        app_api = tweepy.API(_)
        # Start API instance cache, username to user id cache and user data cache
        userAPIs = {}
        nameIDs = {}
        userDataCache = {}
        print("loaded app keys")
except IOError:
    print("No key.json found")
    exit()


def fileName(userID) -> str:
    """Generates the JSON filename from a user's ID.

    Args:
        userID (int): The user's ID

    Returns:
        str: The filename for the user's data.
    """
    return "%s_data.json" % userID


def onboard(userID, acc_t, acc_ts) -> None:
    """Initializes the data file for a user

    Args:
        userID (int): The user's ID.
        acc_t (str): The user's access token.
        acc_ts (str): The user's access secret.
    """
    data = {
        "acc_t": acc_t,
        "acc_ts": acc_ts,
        "block_list": [],
    }
    updateUserData(userID, data)
    return


def getID(username) -> int:
    """Gets the user's id out of the the username to ID cache.

    Args:
        username (str): The user's username.

    Returns:
        int: The user's ID.
    """
    return nameIDs[username] if username in nameIDs else None


def connect(username) -> None:
    """Creates a user's API instance.

    Args:
        username (str): The user's username.
    """
    userID = app_api.get_user(screen_name=username).id
    auth = tweepy.OAuthHandler(
        consumer_key=app_key["con_t"],
        consumer_secret=app_key["con_s"],
        callback="https://auth.r0uge.org",
    )
    if os.path.isfile(fileName(userID)):
        print("got cached key for %s" % username)
        userKey = getUserData(userID)
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


def updateUserData(userID, userData) -> None:
    """Dumps a user's data to disk.

    Args:
        userID (int): The user's ID.
        userData (dict): The in memory version of the user's data.
    """
    with open(fileName(userID), "w+") as f:
        json.dump(userData, f)
    return


def getUserData(userID) -> dict:
    """Gets a user's data from either disk or the cache.

    Args:
        userID (int): The user's ID.

    Returns:
        dict: The user's data.
    """
    if userID in userDataCache:
        return userDataCache[userID]
    else:
        with open(fileName(userID), "r") as f:
            userData = json.load(f)
            userDataCache[userID] = userData
        return userData


def getBlocks(userID) -> None:
    """Gets a user's block list from the twitter API.

    Args:
        userID (int): The user's ID.
    """
    userData = getUserData(userID)
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
    updateUserData(userID, userData)
    return


def getBlockList(userID) -> list:
    """Gets the block_list of a user from disk

    Args:
        userID (int): The user's ID.

    Returns:
        list: A list of dicts that include blocked user's username and ID.
    """
    return getUserData(userID)["block_list"]


def createBlocks(userID, blockList, exportID=0) -> None:
    """Creates a blocks on the user's account.

    Args:
        userID (int): The user's ID.
        blockList (list): A list of dicts that include the username and IDs of accounts to block
        exportID (int, optional): The user ID of the source of the blocklist, used to store the filtered block list.
    """
    filteredList = []
    for acct in blockList:
        try:
            userAPIs[userID].create_block(
                user_id=acct["id"], skip_status=True, include_entities=False
            )
            filteredList.append(acct)
        except tweepy.TweepError as e:
            if e.api_code == 50 or e.api_code == 63:
                print(acct["name"], e, sep=": ")
            elif e.response.status_code == 429:
                print("Waiting out blocking")
                sleep(900)
                userAPIs[userID].create_block(
                    user_id=acct["id"], skip_status=True, include_entities=False
                )
                filteredList.append(acct)
    if not exportID == 0:
        exportData = getUserData(export_id)
        exportData["block_list"] = filteredList
        updateUserData(exportID, exportData)
    return


export_user = input("export username: ")
connect(export_user)
export_id = getID(export_user)

if "-sb" not in sys.argv:
    getBlocks(export_id)

if "-g" in sys.argv:
    imports = input("comma seperated list: ")
    importList = "".join(imports.split()).split(",")
    for name in importList:
        connect(name)
        id = getID(name)
        createBlocks(id, getBlockList(export_id), exportID=export_id)
else:
    import_user = input("import username: ")
    connect(import_user)
    import_id = getID(import_user)
    createBlocks(import_id, getBlockList(export_id), exportID=export_id)
