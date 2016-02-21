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
import textwrap
import numpy

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
from graph import entities

__author__ = "poijqwef"
__copyright__ = "poijqwef"
__license__ = "none"


class iNode:
    def __init__(self,channelId):
        self.channelId = channelId
        self.inwardEdges = []
        self.outwardEdges = []
        self.name = None
        self.nInwardEdges = 0
        self.nOutwardEdges = 0
    def setName(self,name):
        self.name = name
    def addInwardEdge(self,edge):
        self.inwardEdges.append(edge)
        self.nInwardEdges+=1
    def addOutwardEdge(self,edge):
        self.outwardEdges.append(edge)
        self.nOutwardEdges+=1
    def info(self):
        print('iNode info:')
        print('ChannelId:',self.channelId)
        print('Name:',self.name)
        print('InwardEges:',self.nInwardEdges)
        for i in self.inwardEdges:
            i.print()
        print('OutwardEdges:',self.nOutwardEdges)
        for i in self.outwardEdges:
            i.print()
        print('~~~~~~~~~~')

class iDirectedEdge:
    def __init__(self,nodeFrom,nodeTo):
        self.nodeFrom = nodeFrom
        self.nodeTo = nodeTo
    def print(self):
        print(self.nodeFrom.name,'->',self.nodeTo.name)
    def info(self):
        print('iDirectedEdge info:')
        print('NodeFrom:',self.nodeFrom.name)
        print('NodeTo:',self.nodeTo.name)
        print('~~~~~~~~~~')

_logger = logging.getLogger(__name__)
youtube = build(YOUTUBE_API_SERVICE_NAME,YOUTUBE_API_VERSION,developerKey=DEVELOPER_KEY)
graphType='fdp'
outputGraph='svg'
mainShape='square'
childrenShape='circle'
shapeWidth='2'
nodeSeparation='2'

myWrapper = textwrap.TextWrapper(width=20)

def getYoutubeName(channelId):
    userChannelIdRequest = youtube.channels().list(part="brandingSettings",id=channelId).execute()
    if len(userChannelIdRequest) == 0:
        return None
    title = None
    for item in userChannelIdRequest.get("items", []):
        if 'title' in item['brandingSettings']['channel']:
            title = item['brandingSettings']['channel']['title']
        else:
            return None
    return title

def getChannelConnections(channelId,connectingProperty):
    userChannelsRequest = youtube.channels().list(part="brandingSettings",id=channelId).execute()
    #print(json.dumps(userChannelsRequest, sort_keys=True,
    #    indent=4, separators=(',', ': ')))
    channelIds=[]
    for search_result in userChannelsRequest.get("items",[]):
        if connectingProperty in search_result['brandingSettings']['channel'].keys():
            channelIds = search_result['brandingSettings']['channel'][connectingProperty]
    return channelIds

def crawlYoutube(node,depth,maxDepth,nodes,edges):
    if depth > maxDepth:
        return
    channelIds = getChannelConnections(node.channelId,'featuredChannelsUrls')
    for i in channelIds:
        if i in nodes.keys():
            myNode=nodes[i]
        else:
            myNode=iNode(i)
            myNode.setName(getYoutubeName(i))
            nodes[i]=myNode
            crawlYoutube(myNode,depth+1,maxDepth,nodes,edges)

        myEdge=iDirectedEdge(node,myNode)
        node.addOutwardEdge(myEdge)
        myNode.addInwardEdge(myEdge)
        edges.append(myEdge)

def getNodeStyle(node):
    width=str(1.+numpy.log(1.+node.nInwardEdges))
    hexColor='blue'
    styleToken='[style=filled,fillcolor="'+hexColor+\
               '",shape="'+childrenShape+\
    '",fontcolor=white,fixedsize=true,width='+width+'];'
    return styleToken

def getEdgeStyle(edge):
    title='\n'.join(myWrapper.wrap(edge.nodeFrom.name))
    titleTo='\n'.join(myWrapper.wrap(edge.nodeTo.name))
    label=title+' -> '+titleTo
    styleToken='"'+title+'" -> "'+titleTo+'" [label="'+label+'"];'
    return styleToken

def getColorFromDepth(depth,maxDepth):
    green=0.2*(maxDepth-depth)/float(maxDepth)
    hexColor = 'red' if depth == 0 else 'blue' #matplotlib.colors.rgb2hex((0,green,0.8))
    shape=mainShape if depth == 0 else childrenShape
    return '[style = filled, fillcolor = "'+hexColor+'", shape = "'+shape+'", fontcolor = white, fixedsize=true, width='+shapeWidth+'];'


def printChannelGraph(rootUrl,depth,maxDepth,outputFile,titleDepth):
    if depth >= maxDepth:
        return
    urls,title = getFeaturedChannels(rootUrl)
    minDepth=depth
    if title in titleDepth.keys():
        minDepth = min(titleDepth[title],minDepth)
    else:
        titleDepth[title]=minDepth
    title = '\n'.join(myWrapper.wrap(title))
    outToken='"'+title+ '" '+getColorFromDepth(minDepth,maxDepth)
    outputFile.write(outToken.encode('utf-8')+'\n')

    depth+=1
    for url in urls:
        titleTo = channelTitleFromUrl(url)
        minDepth=depth
        if title == None or titleTo == None:
            continue
        if titleTo in titleDepth.keys():
            minDepth = min(titleDepth[titleTo],minDepth)
        else:
            titleDepth[titleTo]=minDepth
        titleTo = '\n'.join(myWrapper.wrap(titleTo))
        label=title+' -> '+titleTo
        edge = '"'+title+ '" -> "'+titleTo+'" [label = "'+label+'" ];'
        outputFile.write(edge.encode('utf-8')+'\n')
        outputFile.write('"'+titleTo.encode('utf-8')+ '" '+getColorFromDepth(minDepth,maxDepth).encode('utf-8')+'\n')
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
    title = None
    for item in userChannelIdRequest.get("items", []):
        if 'title' in item['brandingSettings']['channel']:
            title = item['brandingSettings']['channel']['title']
        else:
            return None
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
    parser.add_argument('-rootChannelId',required=False)
    parser.add_argument('-rootUserid',required=False)
    parser.add_argument('-depth',default=2,required=False,type=int)
    parser.add_argument('-edgeNames',default=False,required=False)
    parser.add_argument('-o',default='graph_output.'+graphType)
    args = parser.parse_args(args)
    if not args.rootChannelId and not args.rootUserid:
        print('error: Use either rootChannelor rootUserid')
        sys.exit(1)
    return args

def main(args):
    args = parse_args(args)
    print(args.rootChannelId)
    if not args.rootChannelId:
        rootChannelId = channelUrlFromUsername(args.rootUserid)
    else:
        rootChannelId = args.rootChannelId

    titleDepth=dict()

    if rootChannelId:
        myNode=iNode(rootChannelId)
        myNode.setName(getYoutubeName(rootChannelId))
        nodes={rootChannelId:myNode}
        edges=[]
        initialDepth=0
        maxDepth=args.depth
        crawlYoutube(myNode,initialDepth,maxDepth,nodes,edges)

        outputFile=open(args.o,'w')
        outputFile.write('digraph {\n')
        outputFile.write('K='+nodeSeparation+'\n')
        for i in nodes.values():
            if i.name:
                title='\n'.join(myWrapper.wrap(i.name))
                outToken='"'+title+'" '+getNodeStyle(i)
                outputFile.write(outToken.encode('utf-8')+'\n')
        for i in edges:
            if i.nodeFrom.name and i.nodeTo.name:
                outToken=getEdgeStyle(i)
                outputFile.write(outToken.encode('utf-8')+'\n')
        outputFile.write('}\n')
        outputFile.close()
        cmd=graphType+' -T'+outputGraph+' -o graph_output.'+outputGraph+' graph_output.'+graphType
        subprocess.check_call(shlex.split(cmd))

        #printChannelGraph(rootUrl,0,args.depth,outputFile,titleDepth)

    _logger.info("Script ends here")

def _graphFeaturedChannels():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main(sys.argv[1:])

def run():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main(sys.argv[1:])

if __name__ == "__main__":
    run()
