#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import urllib
import httplib
import re
import demjson
import time
import codecs
from datetime import datetime, timedelta, date
from sets import Set

canonicalUsernames = {}
canonicalUsernames[u'anant'] = "anant"
canonicalUsernames[u'anantn'] = "anant"
canonicalUsernames[u'Anant Narayanan'] = "anant"
canonicalUsernames[u'andreasgal'] = "andreas"
canonicalUsernames[u'Andreas Gal'] = "andreas"
canonicalUsernames[u'artur'] = "artur"
canonicalUsernames[u'artur_afk'] = "artur"
canonicalUsernames[u'arturadib'] = "artur"
canonicalUsernames[u'Artur Adib'] = "artur"
canonicalUsernames[u'bdahl'] = "bdahl"
canonicalUsernames[u'bdahl-afk'] = "bdahl"
canonicalUsernames[u'benadida'] = "ben"
canonicalUsernames[u'Ben Adida'] = "ben"
canonicalUsernames[u'brendandahl'] = "bdahl"
canonicalUsernames[u'Brendan Dahl'] = "bdahl"
canonicalUsernames[u'bwalker'] = "bwalker"
canonicalUsernames[u'dclarke'] = "dclarke"
canonicalUsernames[u'David Clarke'] = "dclarke"
canonicalUsernames[u'dianeloviglio'] = 'dianeloviglio'
canonicalUsernames[u'digitarald'] = 'digitarald'
canonicalUsernames[u'dwalkowski'] = 'dwalkowski'
canonicalUsernames[u'fabrice'] = 'fabrice'
canonicalUsernames[u'Harald Kirschner'] = 'harald'
canonicalUsernames[u'mhanson@gmail.com'] = 'mhanson'
canonicalUsernames[u'lloyd'] = 'lloyd'
canonicalUsernames[u'Ian Bicking'] = 'ianb'
canonicalUsernames[u'Julian Viereck'] = 'jviereck'
canonicalUsernames[u'lloyd|mbp'] = 'lloyd'
canonicalUsernames[u'Lloyd Hilaiel'] = 'lloyd'
canonicalUsernames[u'mixedpuppy'] = 'mixedpuppy'
canonicalUsernames[u'notmasteryet'] = 'yury'
canonicalUsernames[u'onecyrenus'] = 'dclarke'
canonicalUsernames[u'shane-tomlinson'] = 'stomlinson'
canonicalUsernames[u'Shane Tomlinson'] = 'stomlinson'
canonicalUsernames[u'stomlinson'] = 'stomlinson'
canonicalUsernames[u'vingtetun'] = 'vingtetun'
canonicalUsernames[u'Vivien Nicolas'] = 'vingtetun'
canonicalUsernames[u'wfwalker'] = 'bwalker'
canonicalUsernames[u'Tarek Ziade'] = 'tarek'

canonicalCategories = {}
canonicalCategories['mozilla/pdf.js'] = 'pdfjs'
canonicalCategories['mozilla/browserid'] = 'identity'
canonicalCategories['mozilla/openwebapps'] = 'openwebapps'
canonicalCategories['anantn/soup'] = 'openwebapps'
canonicalCategories['mozilla/soup'] = 'openwebapps'
canonicalCategories['mozilla/appsync'] = 'openwebapps'
canonicalCategories['mozilla/fx-share-addon'] = 'social'

def canonicalizeUsername(wildID):
	if canonicalUsernames.has_key(wildID):
		return canonicalUsernames[wildID]
	else:
		return wildID

def canonicalizeCategory(wildID):
	if canonicalCategories.has_key(wildID):
		return canonicalCategories[wildID]
	else:
		return wildID

def private_strptime(string):
	# sample 2011-10-26T03:03:55
	t = time.strptime(string, "%Y-%m-%dT%H:%M:%S")
	thing = datetime(*t[0:6])
	return thing

# -------------------------------------------------------

def getAllCommitsForRepo(userAndProject):
	commitRecords = []

	conn = httplib.HTTPSConnection('api.github.com')
	pageURL = "/repos/%s/commits?page=%d&per_page=100" % (userAndProject, 1)

	while True:
		conn.request("GET", pageURL)
		response = conn.getresponse()

		theString = response.read()

		commits = []

		try:
			commits = demjson.decode(theString)
		except ValueError:
			print pageURL

		for commitRecord in commits:
			commitCommittedDate = None
			commitAuthoredDate = None

			if commitRecord.__class__ != dict:
				print u"PARSING ERROR"
				print commitRecord
				continue

			commitDetails = commitRecord["commit"]

			user = "None"
			# try the login fields first
			if (user == "None") and (commitDetails["author"].has_key("login")):
				user = canonicalizeUsername(commitDetails["author"]["login"])
			if (user == "None") and (commitDetails["committer"].has_key("login")):
				user = canonicalizeUsername(commitDetails["committer"]["login"])
			
			# if necessary, try the name fields
			if (user == "None") and (commitDetails["author"].has_key("name")):
				user = canonicalizeUsername(commitDetails["author"]["name"])
			if (user == "None") and (commitDetails["committer"].has_key("name")):
				user = canonicalizeUsername(commitDetails["author"]["name"])

			if (commitDetails.has_key("author")):
				if (commitDetails["author"].has_key("date") and commitDetails["author"]["date"]):
					commitCommittedDate = private_strptime(commitDetails["author"]["date"][0:19])

					if user == "None":
						raise RuntimeError("Bogus username in %s" % commitDetails)

					commitAuthoredRecord = {

						'ts': commitCommittedDate,
						'kind': 'commit authored',
						'category': canonicalizeCategory(userAndProject),
						'user': user,
						'url': 'https://github.com/%s/commit/%s' % (userAndProject, commitRecord["sha"]),
						'title': commitRecord["commit"]["message"][0:80].replace('\n', ' ')
					}

					commitRecords.append(commitAuthoredRecord)

			if (commitDetails.has_key("committer")):
				if (commitDetails["committer"].has_key("date") and commitDetails["committer"]["date"]):
					commitAuthoredDate = private_strptime(commitDetails["committer"]["date"][0:19])

					if (commitAuthoredDate != commitCommittedDate):

						if user == "None":
							raise RuntimeError("Bogus username")
						
						commitCommittedRecord = {
							'ts': commitAuthoredDate,
							'kind': 'commit committed',
							'category': canonicalizeCategory(userAndProject),
							'user': user,
							'url': 'https://github.com/%s/commit/%s' % (userAndProject, commitRecord["sha"]),
							'title': commitRecord["commit"]["message"][0:80].replace('\n', ' ')
						}

						commitRecords.append(commitCommittedRecord)

		if not response.getheader("Link"):
			break

		links = response.getheader("Link").split(",")

		nextLinks = [re.search("<(.*)>", item).group(1) for item in links if item.find('rel="next"') >= 0]
		if len(nextLinks) != 1:
			break;
		if nextLinks[0] == pageURL:
			break
		pageURL = nextLinks[0]

	# print u"<div>%s had %d records</div>" % (userAndProject, len(commitRecords))
	return commitRecords

def getAllCommitsForRepoList(repoList):
	allIssues = []
	for repo in repoList:
		allIssues.extend(getAllCommitsForRepo(repo))

	return allIssues

# ------------------------------------------------------

def getAllPullRequestsForRepo(userAndProject):
	pullRequestRecords = []

	conn = httplib.HTTPSConnection('api.github.com')

	conn.request("GET", '/repos/' + userAndProject + '/pulls?state=open&per_page=100')
	pullRequests = demjson.decode(conn.getresponse().read())

	conn.request("GET", '/repos/' + userAndProject + '/pulls?state=closed&per_page=100')
	pullRequests.extend(demjson.decode(conn.getresponse().read()))

	# print '<div>%s has %d pull requests</div>' % (userAndProject, len(pullRequests))

	# html url
	# https://github.com/mozila/pdf.js/pull/643

	for pullRequest in pullRequests:
		pullRecord = {
			'ts': private_strptime(pullRequest["created_at"][0:19]),
			'kind': 'pull created',
			'category': canonicalizeCategory(userAndProject),
			'user': canonicalizeUsername(pullRequest["user"]["login"]),
			'url': pullRequest["html_url"],
			'title': pullRequest["title"][0:80].replace('\n', ' ')
		}
		pullRequestRecords.append(pullRecord)


	return pullRequestRecords

def getAllPullRequestsForRepoList(repoList):
	allPulls = []
	for repo in repoList:
		allPulls.extend(getAllPullRequestsForRepo(repo))

	return allPulls

# ------------------------------------------------------

def getIssues(userAndProject, status):
	conn = httplib.HTTPSConnection('api.github.com')
	conn.request("GET", '/repos/' + userAndProject + '/issues?per_page=1000&state=' + status)
	return demjson.decode(conn.getresponse().read())

def getAllIssuesForRepo(userAndProject):
	numbers = Set()

	openIssues = getIssues(userAndProject, 'open')
	closedIssues = getIssues(userAndProject, 'closed')

	allIssues = []

	for issue in openIssues:
		if not (issue["number"] in numbers):
			numbers.add(issue["number"])
			issueRecord = {
				'ts': private_strptime(issue["created_at"][0:19]),
				'kind': 'issue opened',
				'category': canonicalizeCategory(userAndProject),
				'user': canonicalizeUsername(issue["user"]["login"]),
				'url': issue["html_url"],
				'title': issue["title"][0:80].replace('\n', ' ')
			}
			allIssues.append(issueRecord)


	for issue in closedIssues:
		if not (issue["number"] in numbers):
			numbers.add(issue["number"])
			issueRecord = {
				'ts': private_strptime(issue["closed_at"][0:19]),
				'kind': 'issue closed &nbsp; <img src="http://cdn1.iconfinder.com/data/icons/pidginsmilies/beer.png" style="position:relative; top:4px; height:16px;">',
				'category': canonicalizeCategory(userAndProject),
				'user': canonicalizeUsername(issue["user"]["login"]),
				'url': issue["html_url"],
				'title': issue["title"][0:80].replace('\n', ' ')
			}
			allIssues.append(issueRecord)


	return allIssues

def getAllIssuesForRepoList(repoList):
	allIssues = []
	for repo in repoList:
		allIssues.extend(getAllIssuesForRepo(repo))

	return allIssues

# -------------------------------------------------------------------------

def getAllIRCUtterancesForChannel(channel):
	utteranceRecords = []
	conn = httplib.HTTPConnection('irclog.gr')
	conn.request("GET", '/api/utterances/irc.mozilla.org/' + channel)
	utterances = demjson.decode(conn.getresponse().read())

	for utterance in utterances:
		utteranceRecord = {
			'ts': datetime.fromtimestamp(utterance["ts"]),
			'kind': 'irc',
			'category': canonicalizeCategory(channel),
			'user': canonicalizeUsername(utterance["who"]),
			'url': 'http://irclog.gr/#show/irc.mozilla.org/%s/%s' % (channel, utterance["id"]),
			'title': utterance["msg"]
		}
		utteranceRecords.append(utteranceRecord)


	return utteranceRecords

def getAllIRCUtterancesForChannelList(channelList):
	allUtterances = []
	for channel in channelList:
		allUtterances.extend(getAllIRCUtterancesForChannel(channel))

	return allUtterances

def getRecentRecords(records, hoursWindow):
	window = timedelta(hours = hoursWindow)
	now = datetime.now()
	then = now - window
	return [record for record in records if (then < record["ts"])]

def retrieveRecordsFromGitHub(repoList, hoursWindow):
	records = []

	# channelList = ['openwebapps', 'pdfjs', 'identity', 'browserid']
	# records.extend(getAllIRCUtterancesForChannelList(channelList))
	records.extend(getAllPullRequestsForRepoList(repoList))
	records.extend(getAllCommitsForRepoList(repoList))
	records.extend(getAllIssuesForRepoList(repoList))

	recentRecords = getRecentRecords(records, hoursWindow)

	# contributors = Set()
	# for record in recentRecords:
	# 	contributors.add(record["user"])

	return sorted(recentRecords, key=lambda record: record["ts"], reverse=True)


def formatHTMLReport(records, titleString):
	reportFile = codecs.open("%s-report.html" % titleString, "w", encoding="utf-8", errors="ignore")

	reportFile.write(u"<html>")
	reportFile.write(u"<head>")
	reportFile.write(u"<link rel='icon' href='http://mozillalabs.com/wp-content/themes/labs2.0/favicon.png' type='image/png' />")
	reportFile.write(u"<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>")
	reportFile.write(u"<meta http-equiv='refresh' content='300'>")
	reportFile.write(u"<title>%s activity report</title>" % titleString)
	reportFile.write(u"<link rel='stylesheet' type='text/css' media='all' href='./kiosk.css' />")
	reportFile.write(u"<script type='text/javascript' src='./sortable.js'></script>")
	reportFile.write(u"<body>")

	reportFile.write(u"<h1>%s activity report</h1>" % titleString)
	
	reportFile.write(u"<table width='100%' class='sortable' id='sortabletable'>")

	for record in recentRecords:
		try:
			reportFile.write(u'<tr><td class="git-user">%s</td> <td class="git-description">%s: <a href="%s">%s</a></td></tr>' % (record["user"], record["kind"], record["url"], record["title"]))
		except RuntimeError:
			reportFile.write(u'<!-- runtime error -->')
		except UnicodeEncodeError:
			reportFile.write(u'<!-- unicode error -->')

	reportFile.write(u"</table>")

	reportFile.write(u"<div style='padding-top: 100px'>%s</div>" % datetime.now())

	reportFile.write(u"</body></html>")



# -----------------------------------------------------------------------

# repoList = [
# 	'mozilla/browserid', 
# 	'mozilla/pdf.js', 
# 	'mozilla/openwebapps', 
# 	'mozilla/fx-share-addon',
# 	'mozilla/apps.mozillalabs.com', 
# 	'mozilla/browserid_addon',   
# 	'mozilla/appsync',   
# 	'mozilla/prospector', 
# 	'anantn/jibe', 
# 	'mozilla/soup'
# 	]

recentRecords = retrieveRecordsFromGitHub(sys.argv[2:], 12)
formatHTMLReport(recentRecords, sys.argv[1])

# consider graphing things with D3://pdf.js/content/web/viewer.html?file=http://vis.stanford.edu/files/2011-D3-InfoVis.pdf

