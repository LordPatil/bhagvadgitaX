from fastapi import FastAPI, BackgroundTasks
import tweepy
import json
import asyncio
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import random

load_dotenv()

app = FastAPI()

# Twitter API credentials (replace these)
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
API_KEY = os.getenv("API_KEY")
API_KEY_SECRET = os.getenv("API_KEY_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")

# Setup Tweepy client
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_KEY_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

# Function to post tweets at intervals
async def post_tweets():
    while True:
        try:
            # Load all tweets
            with open("tweets.json", "r") as f:
                data = json.load(f)
                all_tweets = data.get("tweets", [])

            if len(all_tweets) < 15:
                print("Not enough tweets in tweets.json (need at least 15).")
                return

            # Select 15 random tweets for the day
            tweets_to_post = random.sample(all_tweets, 15)

            # Calculate interval: 24 hours / 15 tweets
            interval_seconds = int((24 * 60 * 60) / 15)

            for idx, tweet in enumerate(tweets_to_post):
                try:
                    response = client.create_tweet(text=tweet)
                    print(f"[{datetime.now()}] Posted tweet {idx + 1}/15: ID = {response.data['id']}")
                except Exception as e:
                    print(f"[{datetime.now()}] Error posting tweet {idx + 1}: {e}")

                if idx < 14:  # No sleep after last tweet
                    await asyncio.sleep(interval_seconds)

        except Exception as e:
            print(f"[{datetime.now()}] Fatal error: {e}. Retrying in 5 minutes...")
            await asyncio.sleep(5 * 60)  # Wait 5 minutes before retrying in case of major failure
            
@app.on_event("startup")
async def start_tweeting_on_startup():
    # Start tweeting in background
    asyncio.create_task(post_tweets())

@app.get("/")
def root():
    return {"message": "Tweet scheduler is running."}