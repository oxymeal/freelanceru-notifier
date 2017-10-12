#!/usr/bin/env python3
import time
from collections import namedtuple
from datetime import datetime
from typing import Iterator, List, Optional, Dict, Any

import config
import feedparser
import structlog
from telegram import Bot, ParseMode, TelegramError


def add_timestamp_logproc(_logger: Any, _method: str,
                          event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structlog processor, adding current timstamp to the log entry.
    """

    event_dict['when'] = datetime.utcnow().isoformat()
    return event_dict


def get_log_renderer(key: str) -> Any:
    if key == 'json':
        return structlog.processors.JSONRenderer(
            sort_keys=True, ensure_ascii=False)
    elif key == 'console':
        return structlog.dev.ConsoleRenderer()
    else:
        raise ValueError("Unexpected logs renderer " + key)


logger = structlog.wrap_logger(
    structlog.PrintLogger(),
    processors=[
        add_timestamp_logproc,
        get_log_renderer(config.LOGS_RENDERER),
    ])

Entry = namedtuple('Entry', ['title', 'pubdate', 'description', 'link'])


def from_feed_entry(e: feedparser.FeedParserDict) -> Entry:
    return Entry(e.title.strip(),
                 datetime.fromtimestamp(time.mktime(e.published_parsed)),
                 e.description.strip(), e.link)


class FeedPoller:
    def __init__(self, url: str, blacklist: List[str]) -> None:
        self.url = url
        self.entries = []  # type: List[Entry]
        self.last_pubdate = None  # type: Optional[datetime]
        self.blacklist = blacklist

    def is_blacklist(self, e: Entry) -> bool:
        title = e.title.lower()
        description = e.description.lower()
        for word in self.blacklist:
            if word in title or word in description:
                return True
        return False

    def update(self) -> List[Entry]:
        upd_logger = logger.bind(
            method=FeedPoller.update.__qualname__,
            rss_url=self.url,
            last_pubdate=self.last_pubdate)

        upd_logger.info("Retrieving RSS entries")
        feed = feedparser.parse(self.url)
        if feed.get('bozo_exception'):
            upd_logger.error(
                "Error while retrieving RSS",
                exception=str(feed.bozo_exception))
            return []

        self.entries = [from_feed_entry(e) for e in feed.entries]

        new_entries = []
        for entry in self.entries:
            if not self.last_pubdate or entry.pubdate < self.last_pubdate:
                continue

            if self.is_blacklist(entry):
                logger.info("Project was blocked", title=entry.title)
                continue

            new_entries.append(entry)

        upd_logger.info(
            "Retrieved entries", new=len(new_entries), total=len(self.entries))

        self.last_pubdate = max(
            [e.pubdate for e in self.entries], default=None)

        upd_logger.info("New pubdate", new_pubdate=self.last_pubdate)

        return new_entries

    def poll_packs(self, interval: int) -> Iterator[List[Entry]]:
        pp_logger = logger.bind(
            method=FeedPoller.poll_packs.__qualname__,
            rss_url=self.url,
            poll_interval=interval)

        pp_logger.info("Started polling")
        while True:
            pp_logger.info("Poll iteration started")
            started = datetime.now()
            news = self.update()
            pp_logger.info(
                "Entries update finished",
                elapsed=(datetime.now() - started).total_seconds())

            if news:
                yield news

            ended = datetime.now()
            delta = (ended - started).total_seconds()
            pp_logger.info("Poll iteration finished", elapsed=delta)

            if delta < interval:
                time.sleep(interval - delta)


class TelegramSender:
    def __init__(self, bot_token: str) -> None:
        self.bot_token = bot_token
        self.bot = Bot(self.bot_token)

    def format_entry_msg(self, entry: Entry) -> str:
        template = "\n".join([
            "<a href=\"{link}\">{title}</a>",
            "{description}",
        ])

        entry_msg = template.format(
            link=entry.link, title=entry.title,
            description=entry.description).strip()

        return entry_msg

    def format_pack_msg(self, pack: List[Entry]) -> str:
        messages = []
        for entry in pack:
            messages.append(self.format_entry_msg(entry))

        pack_msg = "\n\n".join(messages)
        return pack_msg

    def format_error_msg(self, err: Exception, msg: str = None) -> str:
        error_msg = "{}: {}".format(type(err).__qualname__, str(err))
        if msg:
            error_msg += "; Attempted to send:\n" + msg
        return error_msg

    def send_pack(self, _poller: FeedPoller, pack: List[Entry]) -> None:
        sp_logger = logger.bind(
            method=TelegramSender.send_pack.__qualname__, pack_size=len(pack))

        msg = self.format_pack_msg(pack)
        sp_logger.info("Formatted pack message", msg_size=len(msg))

        try:
            self.bot.send_message(
                config.TARGET_CHAT_ID,
                msg,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True)
            sp_logger.info("Message sent")
        except TelegramError as error:
            sp_logger.error("Sending failed", exception=str(error))
            self.bot.send_message(config.TARGET_CHAT_ID,
                                  self.format_error_msg(error, msg))


def main():
    sender = TelegramSender(config.BOT_TOKEN)
    poller = FeedPoller(url=config.RSS_URL, blacklist=config.BLOCKED_KEYWORDS)
    try:
        for pack in poller.poll_packs(config.POLL_INTERVAL):
            sender.send_pack(poller, pack)
    except KeyboardInterrupt as e:
        logger.info("Polling was interrupted by user")


if __name__ == '__main__':
    main()
