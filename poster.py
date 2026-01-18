"""Twitter poster module to publish tweets via Twitter API v2.

NOTE: tweepy.Client does NOT accept proxies argument - cloud deployment ready.
"""

import os
import time
import tweepy
import logging
from typing import List

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TwitterPoster:
    def __init__(self):
        # Load credentials from environment
        api_key = os.getenv("TWITTER_API_KEY")
        api_secret = os.getenv("TWITTER_API_SECRET")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        
        if not all([api_key, api_secret, access_token, access_token_secret]):
            raise ValueError("Twitter API credentials not found in environment")
        
        # Authenticate with Twitter API v2
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        logger.info("Twitter API client initialized")
    
    def post_tweet(self, text: str) -> bool:
        """
        Post a single tweet.
        
        Args:
            text: Tweet content (max 280 characters)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.create_tweet(text=text)
            logger.info(f"Tweet posted successfully: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return False
    
    def post_thread(self, tweets: List[str]) -> bool:
        """
        Post a thread of tweets.

        Args:
            tweets: List of tweet texts

        Returns:
            True if all tweets posted successfully
        """
        if not tweets:
            logger.warning("No tweets to post")
            return False

        # DRY RUN MODE: Preview tweets without posting
        if config.DRY_RUN:
            logger.info("[DRY RUN MODE] Previewing tweets without posting to Twitter")
            for i, tweet_text in enumerate(tweets, 1):
                print(f"\n{'='*50}")
                print(f"=== [DRY RUN] TWEET PREVIEW {i}/{len(tweets)} ===")
                print(f"{'='*50}")
                print(f"{tweet_text}")
                print(f"{'='*50}")
                print(f"Characters: {len(tweet_text)}/280")
            print()
            logger.info(f"[DRY RUN] Previewed {len(tweets)} tweets")
            return True

        # LIVE MODE: Actually post to Twitter
        previous_tweet_id = None
        all_success = True

        for i, tweet_text in enumerate(tweets, 1):
            try:
                logger.info(f"Posting tweet {i}/{len(tweets)}")

                if previous_tweet_id:
                    # Reply to previous tweet to create a thread
                    response = self.client.create_tweet(
                        text=tweet_text,
                        in_reply_to_tweet_id=previous_tweet_id
                    )
                else:
                    # First tweet in thread
                    response = self.client.create_tweet(text=tweet_text)

                previous_tweet_id = response.data["id"]
                logger.info(f"Tweet {i} posted: {tweet_text[:50]}...")

                # Add delay between tweets to avoid rate limits
                if i < len(tweets):
                    logger.info("Waiting 60 seconds before next tweet...")
                    time.sleep(60)

            except Exception as e:
                logger.error(f"Error posting tweet {i}: {e}")
                # Fallback: print the full tweet content to console
                print(f"\n--- TWEET CONTENT (Failed to post) ---\n{tweet_text}\n--------------------------------------\n")
                all_success = False

        if all_success:
            logger.info(f"Thread of {len(tweets)} tweets posted successfully")
        else:
            logger.warning("Some tweets failed to post - see console for content")

        return all_success
    
    def test_connection(self) -> bool:
        """
        Test if Twitter API credentials are configured.

        NOTE: Twitter Free Tier blocks get_me() and verify_credentials().
        We just verify credentials are present - actual posting will confirm access.
        """
        logger.info("Twitter API client ready (credentials configured)")
        return True

# Force Railway Rebuild
