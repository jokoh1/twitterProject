import os
import tweepy
import openai
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, storage
from datetime import timedelta

load_dotenv()

# Set up Twitter API credentials
consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
access_token = os.getenv('TWITTER_ACCESS_TOKEN')
access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

# Set up OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Authenticate with Twitter API
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# Set up Firebase
cred = credentials.Certificate(os.getenv('FIREBASE_CERT'))
firebase_admin.initialize_app(cred, {'storageBucket': os.getenv('FIREBASE_BUCKET')})
bucket = storage.bucket()

# Define the bot's behavior
class FactCheckSummaryBot(tweepy.StreamListener):
    def on_status(self, status):
        tweet_id = status.id
        tweet_text = status.text
        user_screen_name = status.user.screen_name

        tweet_coordinates = status.coordinates
        if tweet_coordinates:
            latitude, longitude = tweet_coordinates['coordinates']
        else:
            latitude, longitude = None, None

        tweet_source = status.source

        # Fact-check and summarize the tweet
        fact_check_summary = self.fact_check_and_summarize(tweet_text)

        # Save the fact-check summary as a text file
        file_name = f"{tweet_id}_fact_check_summary.txt"
        with open(file_name, "w") as summary_file:
            summary_file.write(fact_check_summary)

        # Upload the fact-check summary file to Firebase Storage
        blob = bucket.blob(file_name)
        with open(file_name, "rb") as summary_file:
            blob.upload_from_file(summary_file)
        os.remove(file_name)

        # Generate a public download link
        download_url = blob.generate_signed_url(timedelta(hours=24), method="GET")

        # Reply to the tweet with the fact-check summary and download link
        reply = f"@{user_screen_name} Fact-check summary: {fact_check_summary[:100]}... Download full summary: {download_url}"
        api.update_status(status=reply, in_reply_to_status_id=tweet_id)
        print("Tweet fact-checked, summarized, and replied:", reply)

    def fact_check_and_summarize(self, text):
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=f"Please fact check and summarize the following tweet: {text}",
            max_tokens=50,
            n=1,
            stop=None,
            temperature=0.7,
        )
        fact_check_summary = response.choices[0].text.strip()
        return fact_check_summary

# Run the bot
if __name__ == "__main__":
    listener = FactCheckSummaryBot()
    stream = tweepy.Stream(auth=api.auth, listener=listener)

    # Change "your_bot_username" to your bot's username
    stream.filter(track=["YOUR TWITTER_USERNAME_GOES_HERE"])