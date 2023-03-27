import os
import tweepy
import openai
import firebase_admin
from firebase_admin import credentials, storage
from datetime import timedelta

# Set up Twitter API credentials
consumer_key = 'your_consumer_key'
consumer_secret = 'your_consumer_secret'
access_token = 'your_access_token'
access_token_secret = 'your_access_token_secret'

# Set up OpenAI API key
openai.api_key = 'OPEN_AI_API_HERE'

# Authenticate with Twitter API
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# Set up Firebase
cred = credentials.Certificate("LOCATION_OF_YOUR FIRE_BASE")
firebase_admin.initialize_app(cred, {'storageBucket': 'FIREBASE_BUCKET_HERE'})
bucket = storage.bucket()

# Define the bot's behavior
class SummaryBot(tweepy.StreamListener):
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

        # Fact-check the tweet
        fact_check_result = self.fact_check(tweet_text)

        # Summarize the tweet
        summary = self.summarize(tweet_text)

        # Save the summary as a text file
        file_name = f"{tweet_id}_summary.txt"
        with open(file_name, "w") as summary_file:
            summary_file.write(summary)

        # Upload the summary file to Firebase Storage
        blob = bucket.blob(file_name)
        with open(file_name, "rb") as summary_file:
            blob.upload_from_file(summary_file)
        os.remove(file_name)

        # Generate a public download link
        download_url = blob.generate_signed_url(timedelta(hours=24), method="GET")

        # Reply to the tweet with the fact-check result, summary, and download link
        reply = f"@{user_screen_name} Fact Check: {fact_check_result} | Summary: {summary[:100]}... Download full summary: {download_url}"
        api.update_status(status=reply, in_reply_to_status_id=tweet_id)
        print("Tweet fact-checked, summarized, and replied:", reply)

    def fact_check(self, text):
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=f"Please fact check the following tweet: {text}",
            max_tokens=50,
            n=1,
            stop=None,
            temperature=0.7,
        )
        fact_check_result = response.choices[0].text.strip()
        return fact_check_result

    def summarize(self, text):
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=f"Please summarize the following tweet: {text}",
            max_tokens=50,
            n=1,
            stop=None,
            temperature=0.7,
        )
        summary = response.choices[0].text.strip()
        return summary

# Run the bot
if __name__ == "__main__":
    listener = SummaryBot()
    stream = tweepy.Stream(auth=api.auth, listener=listener)

    # Change "your_bot_username" to your bot's username
    stream.filter(track=["YOUR TWITTER_USERNAME_GOES_HERE"])