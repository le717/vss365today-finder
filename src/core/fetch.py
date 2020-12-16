from datetime import datetime, timedelta
from pprint import pprint
from typing import Optional

from requests.exceptions import HTTPError
import tweepy

from src.helpers import (
    connect_to_twitter,
    find_prompt_tweet,
    find_prompt_word,
    get_tweet_media,
    get_tweet_text,
)
from src.helpers import api
from src.helpers.date import create_api_date


__all__ = ["main"]


# Connect to the Twitter API
TWITTER_API = connect_to_twitter()


def __is_hosts_own_tweet(status: tweepy.Status) -> bool:
    """Identify if this tweet is original to the prompter.

    Currently, this means removing both retweets and
    retweeted quote tweets of the prompter's tweets.
    """
    return not status.retweeted and not hasattr(status, "retweeted_status")


def process_tweets(
    uid: str, tweet_id: str = None, recur_count: int = 0
) -> Optional[tweepy.Status]:
    # If we recurse too many times, stop searching
    if recur_count > 7:
        return None

    # Get the latest tweets from the prompt Host
    # We need to enable extended mode to get tweets with over 140 characters
    statuses = TWITTER_API.user_timeline(
        uid, max_id=tweet_id, count=20, tweet_mode="extended"
    )

    # Start by collecting _only_ the prompter's original tweets
    own_tweets = [status for status in statuses if __is_hosts_own_tweet(status)]

    found_tweet = None
    for tweet in own_tweets:
        # Try to find the prompt tweet among the pulled tweets
        if find_prompt_tweet(tweet.full_text):
            found_tweet = tweet
            break
        continue

    # We didn't find the prompt tweet, so we need to search again,
    # but this time, older than the oldest tweet we currently have
    if found_tweet is None:
        return process_tweets(uid, own_tweets[-1].id_str, recur_count + 1)
    return found_tweet


def __get_host_start_day(today: datetime) -> int:
    """Determine the starting date for this hosting period."""
    # Hosts begin on the 1st and 16th
    START_DATES = [1, 16]

    # ...Except for February. It's special. Hosts begin on the 1st and 15th
    if today.month == 2:
        START_DATES = [1, 15]

    # If the current day is between the start and (exclusive) end,
    # we are in the first Host's period
    if START_DATES[0] <= today.day < START_DATES[1]:
        return START_DATES[0]

    # Except it's not in that first range, so we're in the second Host's period
    return START_DATES[1]


def main() -> bool:
    # Start by getting today's date because it's surprising
    # how often we actually need this info
    TODAY = datetime.now()
    is_2021 = TODAY.year >= 2021

    # Get the latest recorded prompt to see if we need to do anything
    LATEST_TWEET = api.get("prompt")[0]
    LATEST_TWEET["date"] = create_api_date(LATEST_TWEET["date"])

    # We already have latest tweet, don't do anything
    if (
        LATEST_TWEET["date"].year == TODAY.year
        and LATEST_TWEET["date"].month == TODAY.month
        and LATEST_TWEET["date"].day == TODAY.day
    ):
        print(f"Tweet for {TODAY} already found. Aborting...")
        return False

    # Starting in 2021, Hosts will serve for 15 days (2 Hosts/mo).
    # This is incompatible with the existing 1 Host/mo format.
    # To ensure a seamless transition, use the required Host IDing
    # process for whatever the current year is and
    # TODO Remove the pre-2021 code after NYD 2021!!!
    print("Identifying the current Host")
    if is_2021:
        # Search for the Host for this hosting period
        hosting_period = datetime.now().replace(day=__get_host_start_day(TODAY))
        CURRENT_HOST = api.get("host", "date", params={"date": hosting_period})[0]
    else:
        # Start by searching for the Host for this day, and if that fails,
        # search for the Host for the whole month
        try:
            CURRENT_HOST = api.get("host", "date", params={"date": TODAY})[0]
        except HTTPError:
            month_host = TODAY.replace(day=1)
            CURRENT_HOST = api.get("host", "date", params={"date": month_host})[0]

    # Attempt to find the prompt
    print("Searching for the latest prompt tweet")
    prompt_tweet = process_tweets(CURRENT_HOST["id"])

    # The tweet was not found at all :(
    if prompt_tweet is None:
        print("Search limit reached without finding prompt tweet! Aborting...")
        return False

    # The found tweet date is yesterday's date, indicating a
    # time zone difference. Tweet datetimes are always expressed
    # in UTC, so attempt to get to tomorrow's date
    # and see if it matches the expected tweet date
    tweet_date = prompt_tweet.created_at
    if tweet_date.day - TODAY.day < 0:
        next_day_hour_difference = 24 - prompt_tweet.created_at.hour
        tweet_date = prompt_tweet.created_at + timedelta(hours=next_day_hour_difference)

    # We already have the latest tweet, don't do anything
    # This condition is hit when it is _technnically_ the next day
    # but the newest tweet hasn't been sent out
    if (
        tweet_date.year == LATEST_TWEET["date"].year
        and tweet_date.month == LATEST_TWEET["date"].month
        and tweet_date.day == LATEST_TWEET["date"].day
    ):
        print(f"The latest tweet for {tweet_date} has already found. Aborting...")
        return False

    # Pull out the tweet media and text content
    media_url, tweet_media = get_tweet_media(prompt_tweet)
    tweet_text = get_tweet_text(prompt_tweet, media_url)
    del media_url

    # Attempt to extract the prompt word and back out if we can't
    prompt_word = find_prompt_word(tweet_text)
    if prompt_word is None:
        print(f"Cannot find prompt word in tweet {prompt_tweet.id_str}")
        return False

    # Construct a dictionary with only the info we need
    prompt = {
        "id": prompt_tweet.id_str,
        "uid": prompt_tweet.author.id_str,
        "date": str(tweet_date),
        "word": prompt_word,
        "content": tweet_text,
        "media": tweet_media,
    }
    pprint(prompt)

    try:
        # Add the tweet to the database
        print("Adding tweet to database")
        api.post("prompt", json=prompt)

        # Send the email broadcast
        print("Sending out notification emails")
        api.post("broadcast", params={"date": tweet_date})

    except HTTPError:
        print(f"Cannot add prompt for {tweet_date} to the database!")
    return True
