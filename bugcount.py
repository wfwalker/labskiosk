#!/usr/bin/python
import time
import httplib
import urllib
import string
from datetime import date, datetime
import demjson

def buglistURLPrefix():
    return "https://bugzilla.mozilla.org/buglist.cgi"

def apiURLPrefix():
    return "https://api-dev.bugzilla.mozilla.org/latest/bug"

# -----------------------------------------------------

def getListOfComponentsWithoutBlockingTrackers():
    return ["General", "Dashboard"]

def getComponentToBlockersMap():
    return {"AppSync": "700492", "AMO": "690899", "Add-on": "698879", "Soup": "698883" }

def getStatuses():
    return ["UNCONFIRMED", "NEW", "ASSIGNED", "REOPENED"]

def getURLForPrefixAndParams(inPrefix, inPriorities, inParams):
    params = urllib.urlencode(inParams)
    statusParams = string.join(['bug_status=%s' % x for x in getStatuses()], "&")
    priorityParams = string.join(['priority=%s' % x for x in inPriorities], "&")
    return '%s?%s&%s&%s' % (inPrefix, statusParams, priorityParams, params)

def countBugsFromAPI(completeURL):
    f = urllib.urlopen(completeURL)
    resultString = f.read()
    resultDict = demjson.decode(resultString)
    return  len(resultDict["bugs"])

# -----------------------------------------------------

def countBugsForComponent(inProduct, inComponent):
    completeURL = getURLForPrefixAndParams(apiURLPrefix(), ["P1"], {'product': inProduct, 'component': inComponent})
    return countBugsFromAPI(completeURL)

def showBugsForComponent(inProduct, inComponent):
    return getURLForPrefixAndParams(buglistURLPrefix(), ["P1"], {'product': inProduct, 'component': inComponent})

def countBugsBlockingABug(inBugID):
    completeURL = getURLForPrefixAndParams(apiURLPrefix(), ["P1"], {'blocks': inBugID})
    return countBugsFromAPI(completeURL)

def showBugsBlockingABug(inBugID):
    magicQueryURL = "https://bugzilla.mozilla.org/buglist.cgi?priority=P1&list_id=1819781&field0-0-0=blocked&resolution=---&query_format=advanced&type0-0-0=equals&value0-0-0=%s"
    return magicQueryURL % inBugID

# -----------------------------------------------------

print "<html>"
print "<head>"
print "<link rel='icon' href='http://mozillalabs.com/wp-content/themes/labs2.0/favicon.png' type='image/png' />"

print "<meta http-equiv='refresh' content='300'>"
print "<title>Apps bug counts for Developer Preview</title>"
print "<link href='./kiosk.css' rel='stylesheet' type='text/css' />"
print "</head>"
    
print "<body>"
print "<h1>Apps bug counts for Developer Preview</h1>"

print "<table width='100%'>"

countMap = {}
linkMap = {}

for component in getListOfComponentsWithoutBlockingTrackers():
    countMap[component] = countBugsForComponent('Web Apps', component)
    linkMap[component] = showBugsForComponent('Web Apps', component)

for component, bugID in getComponentToBlockersMap().iteritems():
    countMap[component] = countBugsBlockingABug(bugID)
    linkMap[component] = showBugsBlockingABug(bugID)

needsTriageParams = "priority=--&product=Web+Apps&resolution=---"
countMap["Triage"] = countBugsFromAPI("%s?%s" % (apiURLPrefix(), needsTriageParams))
linkMap["Triage"] = "%s?%s" % (buglistURLPrefix(), needsTriageParams)

for aKey in countMap.keys():
    print "<div class='container'><div class='count'><a target='_blank' href='%s'>%d</a></div><div class='label'>%s</div></div>" % (linkMap[aKey], countMap[aKey], aKey)

print "<br clear='all' />"
print "<div style='padding-top: 100px'>%s</div>" % datetime.now()

print "</body>"
print "</html>"
