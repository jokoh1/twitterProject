import os
from dotenv import load_dotenv
import tweepy
import openai
import firebase_admin
from firebase_admin import credentials, storage
from datetime import timedelta

# Load environment variables
load_dotenv()

# Set up Twitter API credentials
consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
access_token = os.getenv('TWITTER_ACCESS_TOKEN')
access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

# Set up OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Set up Firebase
cred = credentials.Certificate(os.getenv('FIREBASE_CERTIFICATE'))
firebase_admin.initialize_app(cred, {'storageBucket': os.getenv('FIREBASE_BUCKET')})
bucket = storage.bucket()

# Define the bot's behavior
class FactCheckBot(tweepy.StreamListener):
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

        # Summarize the fact-check result
        summary = self.summarize(fact_check_result)

        # Save the summary as a text file
        file_name = "{}_fact_check_summary.txt".format(tweet_id)
        with open(file_name, "w") as summary_file:
            summary_file.write(summary)

        # Upload the summary file to Firebase Storage
        blob = bucket.blob(file_name)
        with open(file_name, "rb") as summary_file:
            blob.upload_from_file(summary_file)
        os.remove(file_name)

        # Generate a public download link
        download_url = blob.generate_signed_url(timedelta(hours=24), method="GET")

        # Reply to the tweet with the summary and download link
        reply = f"@{user_screen_name} Fact check summary: {summary[:100]}... Download full summary: {download_url}"
        api.update_status(status=reply, in_reply_to_status_id=tweet_id)
        print("Tweet fact-checked and replied:", reply)

    def fact_check(self, text):
        response = openai.Completion.create(
            engine="davinci",
            prompt=f"Fact check the following tweet: {text}",
            max_tokens=50,
            n=1,
            stop=None,
            temperature=0.7,
        )
        fact_check_result = response.choices[0].text.strip()
        return fact_check_result

    def summarize(self, text):
        response = openai.Completion.create(
            engine="davinci",
            prompt=f"Please summarize the fact-check result: {text}",
            max_tokens=50,
            n=1,
            stop=None,
            temperature=0.7,
        )
        summary = response.choices[0].text.strip()
        return summary

# Run the bot
if __name__ == "__main__":
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)

    listener = FactCheckBot()
    stream = tweepy.Stream(auth=api.auth, listener=listener)

    # Change "your_bot_username" to your bot's username
    stream.filter(track=["YOUR TWITTER_USERNAME_GOES_HERE"])

    print
