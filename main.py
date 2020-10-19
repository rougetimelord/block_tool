import tweepy
import json

def connect(name):
    auth = tweepy.OAuthHandler(
        key["con_t"],
        key["con_s"],
        "https://auth.r0uge.org"
    )
    
    if (
        name in key["account_keys"]
    ):
        print("got cached key for %s" % name)
        auth.set_access_token(
            key["account_keys"][name]["acc_t"],
            key["account_keys"][name]["acc_ts"]
        )
    else:
        print("setting up key for %s" % name)
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
        key["account_keys"][name] = {
            "acc_ts": auth.access_token_secret,
            "acc_t": auth.access_token}
        with open("key.json", "w") as f:
                json.dump(key, f, indent=4, sort_keys=True)

    return tweepy.API(auth)

try:
    with open("key.json", "r") as f:
        key = json.load(f)
except IOError:
    exit()

export_name = input("import name: ")
export_api = connect(export_name)
import_name = input("import name: ")
import_api = connect(import_name)

cursor = -1
block_list = []
while cursor != 0:
    block_list_resp = export_api.blocks(cursor)
    for user in block_list_resp[0]:
        block_list.append({
            'name': user.screen_name,
            'id': user.id})
    cursor = block_list_resp[1][1]

print("blocking %i accounts on %s" % (len(block_list), import_name))
for index, acct in enumerate(block_list):
    try:
        print("%04d blocking %s" % (index + 1, acct['name']))
        import_api.create_block(user_id=acct['id'])
    except tweepy.TweepError as e:
        print(e)