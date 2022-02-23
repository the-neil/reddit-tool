#!/usr/bin/env python
"""
reddit-tool.py
Neil // 2014-10-03
"""

import sys
import os
import time
import datetime
import argparse
import logging
import json
from pprint import pprint

import requests
import praw
import prawcore
import yaml

try:
    from IPython import embed as debug
except:

    def debug():
        print("Called debug() without iPython loaded.")


VERSION = 2.0
USER_AGENT = "script:reddit-tool:{}".format(VERSION)
CLIENT_ID = ""
CLIENT_SECRET = ""


def main():
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    for logger_name in ("praw", "prawcore"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

    parser = argparse.ArgumentParser(
        description="Import and export data from Reddit accounts.")
    parser.add_argument("action",
                        type=str,
                        choices=("import", "export", "wipe"),
                        help="")
    # parser.add_argument('credentials', type=str, nargs='+', help='')
    parser.add_argument(
        "--subscriptions",
        "-s",
        dest="subscriptions",
        action="store_true",
        default=True,
        help="",
    )
    parser.add_argument(
        "--multireddits",
        "-m",
        dest="multireddits",
        action="store_true",
        default=True,
        help="",
    )
    parser.add_argument("--friends",
                        "-f",
                        dest="friends",
                        action="store_true",
                        default=True,
                        help="")
    parser.add_argument("--saved",
                        "-v",
                        dest="saved",
                        action="store_true",
                        default=False,
                        help="")
    parser.add_argument(
        "--no-subscriptions",
        "-ns",
        dest="subscriptions",
        action="store_false",
        default=True,
        help="",
    )
    parser.add_argument(
        "--no-multireddits",
        "-nm",
        dest="multireddits",
        action="store_false",
        default=True,
        help="",
    )
    parser.add_argument(
        "--no-friends",
        "-nf",
        dest="friends",
        action="store_false",
        default=True,
        help="",
    )
    parser.add_argument("--no-saved",
                        "-nv",
                        dest="saved",
                        action="store_false",
                        default=False,
                        help="")
    # parser.add_argument('--srcuser', type=str, help="")
    # parser.add_argument('--srcpass', type=str, help="")
    # parser.add_argument('--dstuser', type=str, help="")
    # parser.add_argument('--dstpass', type=str, help="")
    parser.add_argument("--profile", dest="profile", type=str, help="")
    parser.add_argument("--input-file", "-i", type=str, help="")
    parser.add_argument("--output-file", "-o", type=str, help="")
    parser.add_argument("--format",
                        "--fmt",
                        choices=["yaml", "json"],
                        default="yaml",
                        help="")
    # Debug Arguments Begin
    parser.add_argument("--debug",
                        action="store_true",
                        default=False,
                        help=argparse.SUPPRESS)
    parser.add_argument("--debug-arguments",
                        action="store_true",
                        default=False,
                        help=argparse.SUPPRESS)
    # Debug Arguments End
    args = parser.parse_args()

    if args.debug_arguments:
        pprint.pprint(args)

    account = authenticate(args.profile)

    if args.action == "import" and not args.input_file:
        sys.stderr.write("Error: importing requires an input file.")
        exit(-1)
    if args.action == "export" and not args.output_file:
        sys.stderr.write("Error: exporting requires an output file.")
        exit(-1)

    if args.action == "wipe" or args.action == "migrate":
        user_wipe(account, args)

    if args.action == "export":
        data, objects = user_export(account, args)
        if args.output_file:
            with open(args.output_file, "w") as outputfile:
                if args.format == "json":
                    outputfile.write(json.dumps(data, sort_keys=True,
                                                indent=2))
                else:
                    outputfile.write(yaml.dump(data, sort_keys=True))

    if args.action == "import":
        with open(args.input_file, "r") as inputfile:
            if args.format == "json":
                data = json.loads(inputfile.read())
            else:
                data = yaml.load(inputfile.read(), Loader=yaml.SafeLoader)
        user_import(account, args, data)


def authenticate(profile=None, username=None, password=None):
    if profile is not None:
        reddit = praw.Reddit(profile, user_agent=USER_AGENT)
    elif username is not None or password is not None:
        if username is None or password is None:
            sys.stderr.write(
                "Error: missing either username or password args.")
            exit(-1)
        else:
            reddit = praw.Reddit(
                username=username,
                password=password,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                user_agent=USER_AGENT,
            )
    else:
        reddit = praw.Reddit("", user_agent=USER_AGENT)
    return reddit


def user_wipe(account, args):
    if args.friends:
        wipe_friends(account)
        print("Unfriended all friends.")
    if args.saved:
        wipe_saved(account)
        print("Deleted all saved submissions.")
    if args.subscriptions:
        wipe_subscriptions(account)
        print("Unsubscribed from all subreddits..")
    if args.multireddits:
        wipe_multireddits(account)
        print("Deleted all multireddits.")


def user_export(account, args):
    objects = {"source_user": account.user}
    data = {
        "source_user": account.user.me().name,
        "export_date": datetime.datetime.now().isoformat(),
    }
    if args.friends:
        data["friends"], objects["friends"] = get_friends(account)
        print("Exported friends.")
    if args.saved:
        data["saved"], objects["saved"] = get_saved(account)
        print("Exported saved submissions.")
    if args.subscriptions:
        data["subscriptions"], objects["subscriptions"] = get_subscriptions(
            account)
        print("Exported subscribed subreddits.")
    if args.multireddits:
        data["multireddits"], objects["multireddits"] = get_multireddits(
            account)
        print("Exported multireddits.")
    return data, objects


def user_import(account, args, data):
    if args.friends:
        set_friends(account, data["friends"])
        print("Imported friends.")
    if args.saved:
        set_saved(account, data["saved"])
        print("Imported saved submissions.")
    if args.subscriptions:
        set_subscriptions(account, data["subscriptions"])
        print("Imported subscribed subreddits.")
    if args.multireddits:
        set_multireddits(account, data["multireddits"])
        print("Imported multireddits.")


def wipe_friends(account):
    friends = account.user.friends().children
    for friend in friends:
        friend.unfriend()


def wipe_saved(account):
    username = account.user.me().name
    submissions = account.redditor(username).saved(limit=1000)
    for sub in submissions:
        sub.unsave()


def wipe_subscriptions(account):
    for sub in account.user.subreddits(limit=1000):
        sub.unsubscribe()


def wipe_multireddits(account):
    for multi in account.user.multireddits():
        multi.delete()


def get_friends(account):
    friend_obj = account.user.friends().children
    friend_txt = []
    for fr in friend_obj:
        friend_txt.append(fr.name)
    return friend_txt, friend_obj


def get_saved(account):
    username = account.user.me().name
    savedsubmission_obj = []
    savedsubmission_txt = []
    for ss in account.redditor(username).saved(limit=1000):

        # txt = {'id': ss.id, 'fullname': ss.fullname, 'url': ss.permalink}
        txt = {"id": ss.id}
        if type(ss) == praw.models.reddit.submission.Submission:
            txt["type"] = "Submission"
            # txt['title'] = ss.title
        elif type(ss) == praw.models.reddit.comment.Comment:
            txt["type"] = "Comment"

        savedsubmission_obj.append(ss)
        savedsubmission_txt.append(txt)

    return savedsubmission_txt, savedsubmission_obj


def get_subscriptions(account):
    subscription_obj = []
    subscription_txt = []
    for sr in account.user.subreddits(limit=1000):
        subscription_obj.append(sr)
        # subscription_txt.append({'name': sr.display_name, 'url': sr.url, 'id': sr.id})
        subscription_txt.append(sr.display_name)
    return subscription_txt, subscription_obj


def get_multireddits(account):
    multireddit_obj = []
    multireddit_txt = []
    for mr in account.user.multireddits():
        multireddit_obj.append(mr)
        multi = {"name": mr.name, "path": mr.path}
        subreddits = []
        for sr in mr.subreddits:
            try:
                subreddits.append(str(sr))
            except requests.exceptions.HTTPError as e:
                import ipdb

                ipdb.set_trace()
                if e.response.status_code == 404:
                    print("Skipped {}".format(sr))
                    continue
                else:
                    raise
        multi["subreddits"] = subreddits
        multireddit_txt.append(multi)
    return multireddit_txt, multireddit_obj


def set_friends(account, friends):
    for friend in friends:
        redditor = account.redditor(friend)
        redditor.friend()


def set_saved(account, savedsubmissions):
    for ss in savedsubmissions:
        if ss["type"] == "Submission":
            saved_obj = account.submission(ss["id"])
        elif ss["type"] == "Comment":
            saved_obj = account.comment(ss["id"])
        else:
            raise Exception("Unknown type of saved item.")
        saved_obj.save()


def set_subscriptions(account, subscriptions):
    for sub in subscriptions:
        sr = account.subreddit(sub)
        sr.subscribe()


def set_multireddits(account, multireddits):
    for multireddit in multireddits:
        subreddits = []
        for sr in multireddit["subreddits"]:
            subreddits.append(account.subreddit(sr))
        try:
            account.multireddit.create(
                display_name=multireddit["name"],
                subreddits=subreddits,
                visibility="private",
            )
        except prawcore.exceptions.Conflict as e:
            for mr_obj in account.user.multireddits():
                if mr_obj.path == multireddit["path"]:
                    for sr in multireddit["subreddits"]:
                        try:
                            sr_obj = account.subreddit(sr)
                            mr_obj.add(sr_obj)
                        except:
                            print("Subreddit: {} NOT FOUND".format(sr))
        except Exception as e:
            import ipdb

            ipdb.set_trace()


if __name__ == "__main__":
    main()
