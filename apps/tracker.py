import time
import hashlib
from urllib.request import urlopen, Request
import requests
import argparse
import difflib


def inline_diff(a, b):
    matcher = difflib.SequenceMatcher(None, a, b)
    def process_tag(tag, i1, i2, j1, j2):
        if tag == 'replace':
            return '{ %s -> %s }' % (matcher.a[i1:i2].decode(), matcher.b[j1:j2].decode())
        if tag == 'delete':
            return '{- %s }' % matcher.a[i1:i2].decode()
        if tag == 'equal':
            return matcher.a[i1:i2].decode()
        if tag == 'insert':
            return '{+ %s }' % matcher.b[j1:j2].decode()
        assert False, "Unknown tag %r"%tag

    tags_data = []
    for t in matcher.get_opcodes():
        current_diff = process_tag(*t)
        if type(current_diff) == bytes:
            current_diff = current_diff.decode()
        tags_data.append(current_diff)
    return ''.join(tags_data)

class Tracker:
    def __init__(self, image_compare=False):
        self.url = ""
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.enabled = True
        self.previous_data = {
            "hash": "",
            "data": ""
        }
        self.image_compare = image_compare

    def get_hash(self, data):
        return hashlib.sha224(data).hexdigest()

    def get_data_from_requests(self, url):
        req = Request(url=url, headers=self.headers)
        return urlopen(req).read()
    
    def start_tracking(self):
        while self.enabled:
            if self.image_compare:
                pass
            else:
                data = self.get_data_from_requests(self.url)
                hash = self.get_hash(data)
                time.sleep(2)
                if self.previous_data.get('hash') == "":
                    self.previous_data['hash'] = hash
                    self.previous_data['data'] = data
                if hash != self.previous_data.get('hash'):
                    print("Change detected")
                    print(inline_diff(self.previous_data.get('data'), data))
                    self.previous_data['hash'] = hash
                    self.previous_data['data'] = data
                time.sleep(1)

    def stop_tracking(self):
        self.enabled = False

if __name__ == "__main__":
    tracker = Tracker(image_compare=False)

    default_url = "https://api.npoint.io/798ff17987ae0adc364c"
    #default_url = "https://www.npoint.io/docs/798ff17987ae0adc364c"
    # get value from args
    argsParser = argparse.ArgumentParser()
    argsParser.add_argument("-u", "--url", help="URL to track",default=default_url)
    
    args = argsParser.parse_args()

    if args.url:
        tracker.url = args.url
        tracker.start_tracking()
    else:
        print("No URL provided")