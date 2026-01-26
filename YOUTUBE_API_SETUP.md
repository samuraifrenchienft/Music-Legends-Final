# YouTube API Setup for Pack Creation

## Required Environment Variables

Add these to your `.env.txt` file:

```
YOUTUBE_API_KEY=your_youtube_api_key_here
```

## How to Get YouTube API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable YouTube Data API v3
4. Go to Credentials → Create Credentials → API Key
5. Copy the API key and add it to your environment

## API Key Permissions

The YouTube Data API v3 needs:
- YouTube Data API v3 enabled
- No additional restrictions needed for basic video data

## Testing the API

Once you've set the API key, test with:

```
/create_community_pack https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## Troubleshooting

- **"API key not found"**: Make sure YOUTUBE_API_KEY is set in environment
- **"API quota exceeded"**: YouTube API has daily limits
- **"Video not found"**: Check if the YouTube URL is valid and public

## What the Bot Does With YouTube Data

- Extracts video title, channel name, view count, likes
- Creates artist cards based on the channel/artist
- Generates supporting cards from the same channel
- Uses real YouTube statistics for card rarity determination
