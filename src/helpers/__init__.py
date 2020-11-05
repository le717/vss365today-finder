from datetime import datetime
import re
from typing import Optional, Tuple

from requests.exceptions import HTTPError
import sys_vars
import tweepy

from src.helpers import api


__all__ = [
    "connect_to_twitter",
    "find_prompt_tweet",
    "find_prompt_word",
    "get_all_hashtags",
    "get_tweet_media",
    "get_tweet_text",
]


# Pull the finder config from the API
CONFIG = api.get("settings", headers=api.create_auth_token())


def __filter_hashtags(hashtags: tuple) -> tuple:
    """Remove all hashtags that we don't need to process."""
    # Get the words used for this month and remove them from consideration
    right_now = datetime.now()
    try:
        month_prompts: dict = api.get(
            "browse", params={"year": right_now.year, "month": right_now.month}
        )
        month_words = [prompt["word"] for prompt in month_prompts["prompts"]]

    # There are no words available for this month. That probably means
    # it's the beginning of the month and no prompts have been given out yet.
    # Skip over the work variations matching process and go straight
    # to filtering out the tweet's hashtags
    except HTTPError:
        month_words = []

    # Regardless if we have any previous words for the month, we need to add
    # the additional hashtags to filter to the list and match them in a partial
    # manner as well. This helps make the filter more flexible in its matching
    # and futher prevents incorrect selection issues that can occurr when a
    # Host uses a small, unfiltered variation of a filtered hashtag.
    # Ex: if the filtered hashtag is "writer", we'll also filter out "writers".
    month_words.extend(CONFIG["additionals"])

    # Go through each word for the month and find variations
    # of it in the tweet. Ex: the word is "motif", so find
    # "motifs" if it exists. Of course, exact word duplications
    # will also be matched. Our endgame is to filter out
    # previous prompt words in the prompt tweet
    # so they are not picked back up and recorded
    matched_variants = []
    for word in month_words:
        # Build a regex that will match exact words and suffix variations
        regex = re.compile(rf"#?{word}\w*\b", re.I)

        # Search the tweet's hashtags for the words
        variants = [
            match.upper() for match in filter(regex.search, hashtags) if match
        ]  # noqa

        # Record all variants we find
        if variants:
            matched_variants.extend(variants)

    # Merge the filter sets then take out all the hashtags
    hashtags_to_filter = matched_variants + CONFIG["identifiers"]
    return tuple(ht for ht in hashtags if ht.upper() not in hashtags_to_filter)


def connect_to_twitter() -> tweepy.API:
    """Connect to the Twitter API."""
    auth = tweepy.OAuthHandler(
        sys_vars.get("TWITTER_APP_KEY"), sys_vars.get("TWITTER_APP_SECRET")
    )
    auth.set_access_token(sys_vars.get("TWITTER_KEY"), sys_vars.get("TWITTER_SECRET"))
    twitter_api = tweepy.API(auth)
    return twitter_api


def find_prompt_tweet(text: str) -> bool:
    return all(hashtag in text.upper() for hashtag in CONFIG["identifiers"])


def get_all_hashtags(text: str) -> Optional[tuple]:
    matches = re.findall(r"(#\w+)", text, re.I)
    return tuple(matches) if matches else None


def find_prompt_word(text: str) -> Optional[str]:
    prompt_word = None

    # Find all hashtags in the tweet
    hashtags = get_all_hashtags(text)
    if hashtags is None:
        return prompt_word

    # Remove all identifying and unneeded hashtags
    remaining = __filter_hashtags(hashtags)

    # If there are any hashtags left, get the first one
    # and remove the prefixed pound sign
    if remaining:
        prompt_word = remaining[CONFIG["word_index"]].replace("#", "").lower()
    return prompt_word


def get_tweet_media(tweet: tweepy.Status) -> Tuple[str, None]:
    """Get the tweet's media if it exists."""
    media_url = ""
    tweet_media = None

    # If we have media in our tweet
    if hasattr(tweet, "extended_entities"):
        media = tweet.extended_entities.get("media")
        if media:
            # We only need a static image, and it's the same route
            # to get one regardless if the media is an image
            # or an "animated GIF"
            media_url = media[0]["url"]
            tweet_media = media[0]["media_url_https"]
    return (media_url, tweet_media)


def get_tweet_text(tweet: tweepy.Status, media_url: str) -> str:
    """Get the tweet's complete text."""
    # Because we're accessing "extended" tweets (> 140 chars),
    # we need to be sure to access the full_text property
    # that holds the non-truncated text
    return tweet.full_text.replace(media_url, "").strip()
