#!/usr/bin/env python3
import time
from collections import namedtuple
from datetime import datetime
from typing import Iterator, List, Optional

import config
import feedparser
from telegram import Bot, ParseMode

Entry = namedtuple('Entry', ['title', 'pubdate', 'description', 'link'])


def from_feed_entry(e: feedparser.FeedParserDict) -> Entry:
    return Entry(e.title.strip(),
                 datetime.fromtimestamp(time.mktime(e.published_parsed)),
                 e.description.strip(), e.link)


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

    def poll_packs(self, interval: int) -> Iterator[List[Entry]]:
        while True:
            started = datetime.now()
            news = self.update()
            if news:
                yield news

            ended = datetime.now()
            delta = (ended - started).total_seconds()
            if delta > interval:
                time.sleep(delta - interval)


def main():
    print(config.RSS_URL)
    bot = Bot(config.BOT_TOKEN)
    poller = FeedPoller(config.RSS_URL)
    for pack in poller.poll_packs(config.POLL_INTERVAL):
        messages = []
        for entry in pack:
            template = "\n".join([
                "<a href=\"{link}\"><b>{title}</b></a>",
                "{description}",
            ])

            entry_msg = template.format(
                link=entry.link,
                title=entry.title,
                description=entry.description).strip()

            messages.append(entry_msg)

        compiled_msg = "\n\n".join(messages)
        bot.send_message(
            config.TARGET_CHAT_ID,
            compiled_msg,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True)


if __name__ == '__main__':
    main()
