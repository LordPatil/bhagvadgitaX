from fastapi import FastAPI, BackgroundTasks
import tweepy
import json
import asyncio
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import random
import google.generativeai as genai
from PIL import Image
import io

load_dotenv()

app = FastAPI()

# Twitter API credentials (replace these)
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
API_KEY = os.getenv("API_KEY")
API_KEY_SECRET = os.getenv("API_KEY_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Setup Tweepy client v2
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_KEY_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

# Setup Tweepy API v1.1 for media uploads
auth_v1 = tweepy.OAuth1UserHandler(
    consumer_key=API_KEY,
    consumer_secret=API_KEY_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)
api_v1 = tweepy.API(auth_v1)

# Configure Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Function to generate image using Gemini
async def generate_image_with_gemini(tweet_text: str):
    if not GEMINI_API_KEY:
        print(f"[{datetime.now()}] Gemini API key not found. Skipping image generation.")
        return None
    try:
        print(f"[{datetime.now()}] Generating image for tweet: {tweet_text}")
        
        # Fallback to GenerativeModel, assuming genai.Client() is not available in the installed version
        # genai.configure(api_key=GEMINI_API_KEY) is assumed to be called at startup
        model = genai.GenerativeModel("gemini-2.0-flash-preview-image-generation")
        
        prompt = f"Generate a visually compelling and artistic image that encapsulates the wisdom of the following Gita verse: '{tweet_text}'. Aim for a symbolic or metaphorical representation, perhaps with a touch of an ethereal, serene, or cosmic art style."
        
        # Pass generation_config as a dictionary
        generation_config_dict = {
            "response_modalities": ['TEXT', 'IMAGE']
        }

        response = await asyncio.to_thread(
            model.generate_content,
            contents=prompt,
            generation_config=generation_config_dict
        )
        
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_data = part.inline_data.data
                    print(f"[{datetime.now()}] Image generated successfully.")
                    return image_data
        # Log the full response if no image data is found for debugging
        print(f"[{datetime.now()}] No image data found in Gemini response. Full response: {response}")
        return None
    except Exception as e:
        print(f"[{datetime.now()}] Error generating image with Gemini: {e}")
        return None

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
                media_id = None
                try:
                    # Generate image
                    image_bytes = await generate_image_with_gemini(tweet)
                    
                    if image_bytes:
                        try:
                            # Save image to a BytesIO object
                            img_byte_arr = io.BytesIO(image_bytes)
                            # Upload image to Twitter
                            media = api_v1.media_upload(filename="tweet_image.png", file=img_byte_arr)
                            media_id = media.media_id_string
                            print(f"[{datetime.now()}] Image uploaded to Twitter, media_id: {media_id}")
                        except Exception as e:
                            print(f"[{datetime.now()}] Error uploading image to Twitter: {e}")

                    # Post tweet with or without image
                    if media_id:
                        response = client.create_tweet(text=tweet, media_ids=[media_id])
                    else:
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