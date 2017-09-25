#!/usr/bin/env python3
import time
from collections import namedtuple
from datetime import datetime
from typing import Iterator, List, Optional

import config
import feedparser

Entry = namedtuple('Entry', ['title', 'pubdate', 'description', 'link'])


def from_feed_entry(e: feedparser.FeedParserDict) -> Entry:
    return Entry(
        e.title,
        datetime.fromtimestamp(time.mktime(e.published_parsed)),
        e.description,
        e.link, )


class FeedPoller:
    def __init__(self, url: str) -> None:
        self.url = url
        self.entries = []  # type: List[Entry]
        self.last_pubdate = None  # type: Optional[datetime]

    def update(self) -> List[Entry]:
        feed = feedparser.parse(self.url)
        self.entries = [from_feed_entry(e) for e in feed.entries]

        new_entries = []
        for entry in self.entries:
            if self.last_pubdate and entry.pubdate > self.last_pubdate:
                new_entries.append(entry)

        self.last_pubdate = max(
            [e.pubdate for e in self.entries], default=None)
        return new_entries

    def poll(self, interval: int) -> Iterator[Entry]:
        while True:
            started = datetime.now()
            news = self.update()
            for n in news:
                yield n

            ended = datetime.now()
            delta = (ended - started).total_seconds()
            if delta > interval:
                time.sleep(delta - interval)


def main():
    print(config.RSS_URL)
    poller = FeedPoller(config.RSS_URL)
    for entry in poller.poll(config.POLL_INTERVAL):
        print(entry)


if __name__ == '__main__':
    main()
