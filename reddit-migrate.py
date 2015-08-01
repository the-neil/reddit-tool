#!/usr/bin/env python
'''
reddit-tool.py
Neil // 2014-10-03
'''

import sys
import os
import time
import datetime
import argparse
import json
import pprint

import requests
import praw

try:
	from IPython import embed as debug
except:
	def debug():
		print("Called debug() without iPython loaded.")

VERSION = 0.1
USER_AGENT = "reddit-tool v.{}".format(VERSION)
OAUTH_SCOPE = ["mysubreddits", "subscribe", "identity"]


def main():
	parser = argparse.ArgumentParser(description="Manage and migrate Reddit accounts.")
	parser.add_argument('action', type=str, choices=('import', 'export', 'migrate', 'wipe'), help='')
	#parser.add_argument('credentials', type=str, nargs='+', help='')
	parser.add_argument('--subscriptions', '-s', dest='subscriptions', action='store_true', default=True, help="")
	parser.add_argument('--multireddits', '-m', dest='multireddits', action='store_true', default=True, help="")
	parser.add_argument('--friends', '-f', dest='friends', action='store_true', default=True, help="")
	parser.add_argument('--saved', '-v', dest='saved', action='store_true', default=True, help="")
	parser.add_argument('--no-subscriptions', '-ns', dest='subscriptions', action='store_false', default=True, help="")
	parser.add_argument('--no-multireddits', '-nm', dest='multireddits', action='store_false', default=True, help="")
	parser.add_argument('--no-friends', '-nf', dest='friends', action='store_false', default=True, help="")
	parser.add_argument('--no-saved', '-nv', dest='saved', action='store_false', default=True, help="")
	parser.add_argument('--srcuser', type=str, help="")
	parser.add_argument('--srcpass', type=str, help="")
	parser.add_argument('--dstuser', type=str, help="")
	parser.add_argument('--dstpass', type=str, help="")
	parser.add_argument('--input-file', '-i', type=str, help="")
	parser.add_argument('--output-file', '-o', type=str, help="")
	# Debug Arguments Begin
	parser.add_argument('--debug', action='store_true', default=False, help=argparse.SUPPRESS)
	parser.add_argument('--debug-arguments', action='store_true', default=False, help=argparse.SUPPRESS)
	# Debug Arguments End
	args = parser.parse_args()

	if args.debug_arguments:
		pprint.pprint(args)

	if args.action == 'import' and not args.input_file:
		sys.stderr.write("Error: importing requires and input file.")
		exit(-1)
	if args.action == 'export' and not args.output_file:
		sys.stderr.write("Error: exporting requires an output file.")
		exit(-1)

	if args.action == 'export' or args.action == 'migrate':
		data, objects = user_export(args)
		if args.output_file:
			json.dump(data, open(args.output_file, 'w'))

	if args.action == 'wipe' or args.action == 'migrate':
		user_wipe(args)

	if args.action == 'import':
		data = json.load(open(args.input_file, 'r'))

	if args.action == 'import' or args.action == 'migrate':
		user_import(args, data)

	if args.debug:
		src = authenticate(args.srcuser, args.srcpass)
		dst = tgt = authenticate(args.dstuser, args.dstpass)
		debug()




def authenticate(username, password):
	reddit = praw.Reddit(user_agent=USER_AGENT, store_json_result='yes')
	reddit.login(username, password)
	return reddit

def user_wipe(args):
	tgt = authenticate(args.dstuser, args.dstpass)
	if args.friends:
		wipe_friends(tgt)
		print("Unfriended all friends.")
	if args.saved:
		wipe_saved(tgt)
		print("Deleted all saved submissions.")
	if args.subscriptions:
		wipe_subscriptions(tgt)
		print("Unsubscribed from all subreddits..")
	if args.multireddits:
		wipe_multireddits(tgt)
		print("Deleted all multireddits.")

def user_export(args):
	src = authenticate(args.srcuser, args.srcpass)
	objects = {'source_user': src.user}
	data = {'source_user': src.user.name, 'export_date': datetime.datetime.now().isoformat()}
	if args.friends:
		data['friends'], objects['friends'] = get_friends(src)
		print("Exported friends.")
	if args.saved:
		data['saved'], objects['saved'] = get_saved(src)
		print("Exported saved submissions.")
	if args.subscriptions:
		data['subscriptions'], objects['subscriptions'] = get_subscriptions(src)
		print("Exported subscribed subreddits.")
	if args.multireddits:
		data['multireddits'], objects['multireddits'] = get_multireddits(src)
		print("Exported multireddits.")
	return data, objects

def user_import(args, data):
	dst = authenticate(args.dstuser, args.dstpass)
	if args.friends:
		set_friends(dst, data['friends'])
		print("Imported friends.")
	if args.saved:
		set_saved(dst, data['saved'])
		print("Imported saved submissions.")
	if args.subscriptions:
		set_subscriptions(dst, data['subscriptions'])
		print("Imported subscribed subreddits.")
	if args.multireddits:
		set_multireddits(dst, data['multireddits'])
		print("Imported multireddits.")


def wipe_friends(reddit):
	friends = reddit.user.get_friends(limit=None).children
	for friend in friends:
		friend.unfriend()

def wipe_saved(reddit):
	submissions = reddit.user.get_saved(limit=None)
	for sub in submissions:
		sub.unsave()

def wipe_subscriptions(reddit):
	subscriptions = reddit.get_my_subreddits(limit=None)
	for sub in subscriptions:
		sub.unsubscribe()

def wipe_multireddits(reddit):
	multireddits = reddit.get_my_multireddits()
	for multi in multireddits:
		reddit.delete_multireddit(multi.name)


def get_friends(reddit):
	friend_obj = reddit.user.get_friends(limit=None).children
	friend_txt = []
	for fr in friend_obj:
		friend_txt.append({'name': str(fr)})
	return friend_txt, friend_obj

def get_saved(reddit):
	savedsubmission_obj = list(reddit.user.get_saved(limit=None))
	savedsubmission_txt = []
	for ss in savedsubmission_obj:
		savedsubmission_txt.append({'id': ss.id, 'fullname': ss.fullname, 'url': ss.permalink, 'title': ss.title})
	return savedsubmission_txt, savedsubmission_obj

def get_subscriptions(reddit):
	subscription_obj = list(reddit.get_my_subreddits(limit=None))
	subscription_txt = []
	for sr in subscription_obj:
		subscription_txt.append({'name': str(sr)})
	return subscription_txt, subscription_obj

def get_multireddits(reddit):
	multireddit_obj = reddit.get_my_multireddits()
	multireddit_txt = []
	for mo in multireddit_obj:
		multi = {'name': mo.name, 'path': mo.path}
		subreddits = []
		for sr in mo.subreddits:
			try:
				subreddits.append({'name': str(sr)})
			except requests.exceptions.HTTPError as e:
				if e.response.status_code == 404:
					print("Skipped {}".format(sr))
					continue
				else:
					raise
		multi['subreddits'] = subreddits
		multireddit_txt.append(multi)
	return multireddit_txt, multireddit_obj


def set_friends(reddit, friends):
	for friend in friends:
		redditor = reddit.get_redditor(friend['name'])
		redditor.friend()

def set_saved(reddit, savedsubmissions):
	submission_ids = [ssub['fullname'] for ssub in savedsubmissions]
	submissions = reddit.get_submissions(submission_ids)
	for sub in submissions:
		sub.save()

def set_subscriptions(reddit, subscriptions):
	for sub in subscriptions:
		sr = reddit.get_subreddit(sub['name'])
		sr.subscribe()

def set_multireddits(reddit, multireddits):
	for multireddit in multireddits:
		subreddits = [sr['name'] for sr in multireddit['subreddits']]
		reddit.create_multireddit(name=multireddit['name'], subreddits=subreddits, visibility="private")




if __name__ == '__main__':
	main()
