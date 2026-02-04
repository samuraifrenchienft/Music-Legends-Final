# Fix: How to Enable Dev Commands (import_packs, create_pack_template, etc.)

## Problem
```
❌ Dev commands are not configured on this bot.
discord.app_commands.errors.CheckFailure: The check functions for command 'import_packs' failed.
```

## Root Cause
The `TEST_SERVER_ID` environment variable is not set in your `.env.txt` file.

## Solution

### Step 1: Get Your Test Server ID

1. Enable Developer Mode in Discord:
   - User Settings → Advanced → Toggle "Developer Mode" ON

2. Get the Server ID:
   - Right-click on your test server name
   - Click "Copy Server ID"
   - Example: `1234567890123456789`

### Step 2: Add to .env.txt

Edit your `.env.txt` file and add:

```
TEST_SERVER_ID=YOUR_SERVER_ID_HERE
```

**Example:**
```
BOT_TOKEN=your_token_here
DISCORD_APPLICATION_ID=your_app_id
TEST_SERVER_ID=1234567890123456789
YOUTUBE_API_KEY=your_youtube_key
# ... other config
```

### Step 3: Restart the Bot

After adding `TEST_SERVER_ID`:

**Local:**
```bash
python run_bot.py
```

**Railway:**
- Push changes to GitHub
- Railway will auto-redeploy
- Or manually trigger a redeployment

### Step 4: Verify

Check the bot logs for:
```
✅ Dev commands will be registered in TEST_SERVER: 1234567890123456789
```

If you see this, the commands are enabled!

## Now Available Commands

Once `TEST_SERVER_ID` is set, you get access to:

### `/import_packs`
Upload a JSON file to import multiple packs at once

**Usage:**
1. Use `/create_pack_template` to get a template
2. Fill in your pack data
3. Upload with `/import_packs`

### `/create_pack_template`
Generate a JSON template for bulk pack import

**Usage:**
```
/create_pack_template num_packs:5
```

This creates a template JSON file with:
- Pack metadata structure
- Example data
- Comments explaining fields

### `/import_packs_help`
View detailed help for bulk pack import

## JSON Format

The template generated will look like:

```json
{
  "packs": [
    {
      "name": "Pack Name",
      "description": "Pack description",
      "pack_type": "community",
      "artists": [
        {
          "name": "Artist Name",
          "image_url": "https://...",
          "tracks": ["Track 1", "Track 2", "Track 3"]
        }
      ]
    }
  ]
}
```

## Troubleshooting

### Still seeing "Dev commands are not configured"?

**Check 1:** Restart bot after adding `TEST_SERVER_ID`
```bash
python run_bot.py
```

**Check 2:** Verify the ID format is correct (numbers only, no special chars)
```
✅ Valid:  TEST_SERVER_ID=1234567890123456789
❌ Invalid: TEST_SERVER_ID=abc123xyz
```

**Check 3:** Make sure you're in the correct server
- Commands only work in the server with ID = `TEST_SERVER_ID`
- Check your server ID matches exactly

**Check 4:** Check bot logs for warning:
```
⚠️  WARNING: TEST_SERVER_ID not set - bulk import commands will not be registered
```

### "This command is only available in the development server"?

This means:
- `TEST_SERVER_ID` is set correctly ✅
- But you're in a DIFFERENT server ❌
- Only use these commands in the server with ID = `TEST_SERVER_ID`

## Alternative: Use /create_pack Instead

If you don't want to set up a test server, you can use:

```
/create_pack artist_name
```

This creates a single pack interactively. It's not bulk, but it works everywhere.

## Questions?

For bulk pack import questions, use:
```
/import_packs_help
```

This shows detailed documentation in Discord.
