#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division, print_function, absolute_import

import argparse
import sys
import os 
import logging
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
import json
import urllib
import sys
import ConfigParser
import re
import subprocess
import shlex
import matplotlib

[scriptDir,scriptName]=os.path.split(__file__)

# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
config = ConfigParser.ConfigParser()
config.readfp(open('api_keys.cfg'))
DEVELOPER_KEY = config.get('google','youtubeDataKey')
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
FREEBASE_SEARCH_URL = "https://www.googleapis.com/freebase/v1/search?%s"
CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"
VIDEO_WATCH_URL = "https://www.youtube.com/watch?v="
# youtube apis: https://developers.google.com/youtube/v3/docs/search/list

#outputDir=os.environ['HOME']+'/Downloads/Youtubes'

from graph import __version__

__author__ = "poijqwef"
__copyright__ = "poijqwef"
__license__ = "none"

_logger = logging.getLogger(__name__)
youtube = build(YOUTUBE_API_SERVICE_NAME,YOUTUBE_API_VERSION,developerKey=DEVELOPER_KEY)


def getColorFromDepth(depth,maxDepth):
    green=0.2*(maxDepth-depth)/float(maxDepth)
    hexColor = 'red' if depth == 0 else matplotlib.colors.rgb2hex((0,green,0.8))
    shape='square' if depth == 0 else 'oval'
    return '[style = filled, fillcolor = "'+hexColor+'", shape = "'+shape+'", fontcolor = white];'

def printChannelGraph(rootUrl,depth,maxDepth,outputFile,titleDepth):
    if depth >= maxDepth:
        return
    urls,title = getFeaturedChannels(rootUrl)
    minDepth=depth
    if title in titleDepth.keys():
        minDepth = min(titleDepth[title],minDepth)
    else:
        titleDepth[title]=minDepth
    outputFile.write('"'+title+ '" '+getColorFromDepth(minDepth,maxDepth)+'\n')

    depth+=1
    for url in urls:
        titleTo = channelTitleFromUrl(url)
        minDepth=depth

        if titleTo in titleDepth.keys():
            minDepth = min(titleDepth[titleTo],minDepth)
        else:
            titleDepth[titleTo]=minDepth
        
        label='From '+title[0:3]+' to '+titleTo[0:3]
        outputFile.write('"'+title+ '" -> "'+titleTo+'" [label = "'+label+'"];\n')
        outputFile.write('"'+titleTo+ '" '+getColorFromDepth(minDepth,maxDepth)+'\n')
        printChannelGraph(url,depth,maxDepth,outputFile,titleDepth)

def channelUrlFromUsername(username):
    userChannelIdRequest = youtube.channels().list(part="id",forUsername=username).execute()
    if len(userChannelIdRequest) == 0:
        return None
    for item in userChannelIdRequest.get("items", []):
        userChannelId = item['id']
    return userChannelId

def channelTitleFromUrl(url):
    userChannelIdRequest = youtube.channels().list(part="brandingSettings",id=url).execute()
    if len(userChannelIdRequest) == 0:
        return None
    for item in userChannelIdRequest.get("items", []):
        title = item['brandingSettings']['channel']['title']
    return title

def getFeaturedChannels(channelUrl):
    userChannelsRequest = youtube.channels().list(part="brandingSettings",id=channelUrl).execute()
    #print(json.dumps(userChannelsRequest, sort_keys=True,
    #    indent=4, separators=(',', ': ')))
    featuredChannels = []
    title = None
    for search_result in userChannelsRequest.get("items", []):
        if 'featuredChannelsUrls' in search_result['brandingSettings']['channel'].keys():
            featuredChannels = search_result['brandingSettings']['channel']['featuredChannelsUrls']
            title = search_result['brandingSettings']['channel']['title']
    if not title:
        return [],''
    return featuredChannels,title

def parse_args(args):
    parser = argparse.ArgumentParser(
        description="Just a Fibonnaci demonstration")
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version='graph {ver}'.format(ver=__version__))
    parser.add_argument('-rootChannel',required=True)
    parser.add_argument('-depth',default=2,required=False,type=int)
    parser.add_argument('-o',default='graph_output.dot')
    return parser.parse_args(args)

def main(args):
    args = parse_args(args)
    rootUrl = channelUrlFromUsername(args.rootChannel)
    outputFile=open(args.o,'w')
    outputFile.write('digraph {\n')
    titleDepth=dict()
    if rootUrl:
        printChannelGraph(rootUrl,0,args.depth,outputFile,titleDepth)
    outputFile.write('}')
    outputFile.close()
    cmd='dot -Tpng -o graph_output.png graph_output.dot'
    subprocess.check_call(shlex.split(cmd))
    _logger.info("Script ends here")

def _graphFeaturedChannels():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main(sys.argv[1:])

def run():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main(sys.argv[1:])

if __name__ == "__main__":
    run()
