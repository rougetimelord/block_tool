import tweepy
import json

def connect(name):
    auth = tweepy.OAuthHandler(
        key["con_t"],
        key["con_s"],
        "https://auth.r0uge.org"
    )
    
    if (
        name in key["accounts"]
    ):
        auth.set_access_token(
            key["accounts"][name]["acc_t"],
            key["accounts"][name]["acc_s"]
        )
    else:
        try:
            url = auth.get_authorization_url()
            print("go to %s on %s" % (url, name))
        except tweepy.TweepError:
            print("failed to get url")
            exit()
        verifier = input("verifier: ")
        try:
            auth.get_access_token(verifier)
        except tweepy.TweepError:
            print("failed verifier")
            exit()
        key["accounts"][name] = {
            "acc_t": auth.access_token_secret,
            "acc_s": auth.access_token}
        with open("key.json", "w") as f:
                json.dump(key, f, indent=4, sort_keys=True)

    return tweepy.API(auth)

try:
    with open("key.json", "r") as f:
        key = json.load(f)
except IOError:
    exit()

export_name = input("import name: ")
export_api = connect(name=export_name)
import_name = input("import name: ")
import_api = connect(name=import_name)

cursor = -1
block_list_ids = []
while cursor != 0:
    block_list_resp = export_api.blocks_ids(cursor)
    block_list_ids.append(block_list_resp[0])
    cursor = block_list_resp[1][1]

for acct_id in block_list_ids:
    try:
        import_api.create_block(user_id=acct_id)
    except tweepy.TweepError as e:
        print(e)