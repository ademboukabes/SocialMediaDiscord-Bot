
# MINI PROJECT : Social Media Tracker
This project aims to create a bot that allows the user to connect to different Social Media platforms at Once. and be able to view and post from a simple
discord Command .
## Main Components 
Instagram Cog
Facebook Cog
Linkdin Cog

# Instagram Discord Bot Cog

This cog allows users to connect their Instagram accounts via OAuth or manually, view posts, delete posts, and view insights. Users are tracked in a SQLite database by Discord ID.

## Setup

1. Install dependencies:

```
pip install discord.py requests python-dotenv
```

2. Create a `.env` file with:

```
APP_ID=your_facebook_app_id
APP_SECRET=your_facebook_app_secret
REDIRECT_URI=https://yourredirect.uri/callback
```

3. Ensure `database.db` exists or will be created automatically.

4. Load the cog in your bot:

```python
await bot.load_extension("cogs.instagram_cog")
```

## Commands

### `/instagram_login`

* Starts the OAuth flow to connect Instagram account.
* Stores token and username in database.

### `/insta_login_dev token username`

* Manually register a token for testing or dev purposes.
* Stores token and username in database.

### `/instagram_posts`

* Lists all Instagram posts for the connected account.
* Displays embedded image, caption, type, timestamp, and shortened URL.
* Adds buttons per post:

  * **Delete Post**: Deletes the post.
  * **View Details**: Shows all data for the post.
  * **View Insights**: Shows metrics depending on media type:

    * IMAGE: `reach, likes, comments, saved`
    * VIDEO: `reach, likes, comments, video_views, shares`
    * REELS: `reach, likes, comments, plays, shares, saved`
### `/Instagram_Post`

### `/Instagram_Post_reel`

### `/disconnect`

* Removes the user from the database.
* Disconnects Instagram account from bot.

## Database

* `users` table:

  * `discord_id`: Discord user ID (unique)
  * `username`: Instagram username
  * `instagram_token`: Access token for API calls
