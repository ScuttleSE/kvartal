from flask import Flask, Response, abort, jsonify
from lxml import etree
from copy import deepcopy
from collections import defaultdict
from dotenv import load_dotenv
import unicodedata
import os
import re
import time
import threading
import requests

load_dotenv()

app = Flask(__name__)

FEED_URL = os.environ['FEED_URL']
CACHE_TTL = int(os.environ['CACHE_TTL'])
MIN_SHOW_SIZE = int(os.environ['MIN_SHOW_SIZE'])

_cache = {'data': None, 'expires': 0}
_cache_lock = threading.Lock()


def slugify(name):
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def get_show_name(title):
    if ':' in title:
        return title.split(':')[0].strip()
    return title.strip()


def fetch_and_parse():
    resp = requests.get(FEED_URL, timeout=15)
    resp.raise_for_status()
    root = etree.fromstring(resp.content)
    channel = root.find('channel')

    items_by_show = defaultdict(list)
    for item in channel.findall('item'):
        title_el = item.find('title')
        title = title_el.text if title_el is not None and title_el.text else ''
        items_by_show[get_show_name(title)].append(item)

    named_shows = {show: items for show, items in items_by_show.items() if len(items) >= MIN_SHOW_SIZE}
    other_items = [item for show, items in items_by_show.items() if show not in named_shows for item in items]

    return {
        'root': root,
        'channel': channel,
        'named_shows': named_shows,
        'other_items': other_items,
        'slug_to_show': {slugify(show): show for show in named_shows},
    }


def get_feed_data():
    with _cache_lock:
        if time.time() < _cache['expires'] and _cache['data'] is not None:
            return _cache['data']
        _cache['data'] = fetch_and_parse()
        _cache['expires'] = time.time() + CACHE_TTL
        return _cache['data']


def build_feed(data, items):
    root, channel = data['root'], data['channel']
    new_root = etree.Element(root.tag, nsmap=root.nsmap)
    new_channel = etree.SubElement(new_root, 'channel')
    for child in channel:
        if child.tag != 'item':
            new_channel.append(deepcopy(child))
    for item in items:
        new_channel.append(deepcopy(item))
    return etree.tostring(new_root, xml_declaration=True, encoding='UTF-8', pretty_print=True)


@app.route('/shows')
def shows():
    data = get_feed_data()
    result = [
        {'show': show, 'slug': slugify(show), 'count': len(items)}
        for show, items in sorted(data['named_shows'].items(), key=lambda x: -len(x[1]))
    ]
    result.append({'show': 'other', 'slug': 'other', 'count': len(data['other_items'])})
    return jsonify(result)


@app.route('/feed/<slug>')
def feed(slug):
    data = get_feed_data()
    if slug == 'other':
        xml = build_feed(data, data['other_items'])
    elif slug in data['slug_to_show']:
        xml = build_feed(data, data['named_shows'][data['slug_to_show'][slug]])
    else:
        abort(404)
    return Response(xml, mimetype='application/rss+xml')


if __name__ == '__main__':
    app.run(debug=True)
