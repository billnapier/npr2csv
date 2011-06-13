#!/usr/bin/python

import codecs
import csv
import sys
import urllib
import urlparse
import xml.etree.ElementTree as et

from optparse import OptionParser

_NPR_API_HOSTNAME = 'api.npr.org'
_NPR_SHOWS_LIST_ID ='3004'

def _require_arg(args, option):
    if not args.__dict__[option]:
        print 'Missing required argument %s' % option
        sys.exit(1)

def parse_args():
    parser = OptionParser()
    parser.add_option('-k', '--api_key', dest='api_key', help='NPR API key')
    parser.add_option('-s', '--show_name', dest='show_name', help='Show Name (partial OK)')
    parser.add_option('-f', '--filename', dest='filename', help='Output filename')

    args = parser.parse_args()[0]
    _require_arg(args, 'api_key')
    _require_arg(args, 'show_name')
    _require_arg(args, 'filename')        

    return args

def build_api_url(path, query_map):
    query = urllib.urlencode(query_map)
    return urlparse.urlunparse(['http', _NPR_API_HOSTNAME, path, '', query, ''])

def retrieve_url(url):
    f = urllib.urlopen(url)
    res = f.read()
    f.close()
    return res

def find_show_id(show_name):
    show_name = show_name.lower()
    url = build_api_url('list', dict(id=_NPR_SHOWS_LIST_ID))
    data = retrieve_url(url)
    doc = et.fromstring(data)
    for item in doc.findall('item'):
        title = item.find('title')
        if title is not None:
            if title.text.lower().find(show_name) != -1:
                return item.attrib['id']

def query_stories_for_show(show_id, api_key, start_num, num_results=20):
    url = build_api_url('query', dict(startNum=start_num,
                                      numResults=num_results,
                                      id=show_id,
                                      apiKey=api_key))
    data = retrieve_url(url)
    doc = et.fromstring(data)
    return [story for story in doc.findall('list/story')]

def find_best_thumbnail(story):
    thumbnail = story.find('thumbnail/large')
    if thumbnail is not None:
        return thumbnail.text
    thumbnail = story.find('thumbnail/medium')
    if thumbnail is not None:
        return thumbnail.text    
    thumbnail = story.find('thumbnail/small')
    if thumbnail is not None:
        return thumbnail.text
    return None

def convert_xml_data(x):
    if x is None:
        return ''
    # CSV writer later on is picky about charset, so make it all UTF-8
    return x.encode('UTF-8')

def parse_story_into_row(story):
    title = story.find('title').text
    link = story.find('link[@type="short"]').text
    teaser = story.find('teaser').text
    short_teaser = story.find('miniTeaser').text
    thumbnail = find_best_thumbnail(story)
    story_date = story.find('storyDate').text

    result = [title, link, short_teaser, teaser, thumbnail, story_date]
    
    return [convert_xml_data(x) for x in result]

def main():
    args = parse_args()
    show_id = find_show_id(show_name=args.show_name)

    output_file = open(args.filename, 'w')
    csv_file = csv.writer(output_file)    

    num = 1
    batch_size = 20
    
    while True:
        # output where we're at so the user can follow along
        print 'Fetching %s items starting from offset %s' % (batch_size, num)
        
        stories = query_stories_for_show(show_id=show_id,
                                         api_key=args.api_key,
                                         start_num=num,
                                         num_results=batch_size)

        for story in stories:
            csv_file.writerow(parse_story_into_row(story))

        # If we get less results back than we asked for, we're at the end.
        if len(stories) != batch_size:
            break

        num = num + batch_size

    output_file.close()

if __name__ == '__main__':
    main()
