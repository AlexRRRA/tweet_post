# Crypto Institutional Twitter Bot 🚀

A professional, AI-powered Twitter bot for crypto institutional market analysis. Posts data-driven insights on BTC/ETH/SOL through the lens of ETF flows, Fed policy, and volatility metrics.

## 📋 What This Bot Does

- **Scans news** every 24 hours from mainstream finance (CNBC) and crypto media (CoinDesk, The Block)
- **Analyzes** using Deepseek-V3 with an institutional perspective
- **Posts** 1 professional tweets per day automatically
- **Prevents duplicates** using SQLite database tracking

## 🔑 Step 1: Get Your API Keys

### Anthropic API (Claude)
1. Go to: https://console.anthropic.com/
2. Sign up and create an account
3. Navigate to "API Keys" and click "Create Key"
4. Copy your API key (starts with `sk-ant-...`)
5. **Cost**: ~$3 per 1M input tokens (very affordable)

### Twitter API v2
1. Go to: https://developer.twitter.com/en/portal/dashboard
2. Create a new Project and App
3. In your App settings:
   - Go to "Keys and tokens"
   - Generate "Consumer Keys" (API Key & Secret)
   - Generate "Access Token & Secret"
   - **Important**: Set permissions to "Read and Write"
4. Save all 4 credentials

## 🛠️ Step 2: Installation

### Open Terminal and run these commands:

```bash
# Navigate to the bot directory
cd ~/crypto-twitter-bot

# Create a virtual environment (isolated Python space)
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

## 🔐 Step 3: Configure Your API Keys

```bash
# Copy the template file
cp .env.template .env

# Edit the file with your keys
nano .env
```

Paste your keys like this:
```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
TWITTER_API_KEY=your-twitter-api-key
TWITTER_API_SECRET=your-twitter-api-secret
TWITTER_ACCESS_TOKEN=your-access-token
TWITTER_ACCESS_TOKEN_SECRET=your-access-token-secret
TWEETS_PER_DAY=3
SCAN_INTERVAL_HOURS=8
```

**Press `Ctrl + X`, then `Y`, then `Enter` to save**

## ▶️ Step 4: Run the Bot

### Test Mode (Run Once)
Test everything without scheduling:
```bash
python main.py --once
```

This will:
- Test your API connections
- Fetch recent news
- Generate tweets
- Post to Twitter
- Exit

### Production Mode (Scheduled)
Run continuously (every 8 hours):
```bash
python main.py
```

**To stop**: Press `Ctrl + C`

## 📁 Project Structure

```
crypto-twitter-bot/
├── .env                    # Your API keys (SECRET!)
├── .env.template           # Template for API keys
├── requirements.txt        # Python dependencies
├── news_history.db         # SQLite database (auto-created)
├── main.py                 # Main orchestrator
├── config.py              # Settings & prompts
├── news_fetcher.py        # RSS feed fetcher
├── analyzer.py            # Claude AI analysis
├── poster.py              # Twitter posting
└── storage.py             # Database management
```

## 🎯 How It Works

1. **Fetch**: Scrapes RSS feeds from Yahoo Finance, CNBC, CoinDesk, The Block
2. **Filter**: Keeps only crypto/macro-relevant articles (BTC, ETH, Fed, etc.)
3. **Dedupe**: Checks database to avoid reposting
4. **Analyze**: Sends top articles to Claude with institutional prompt
5. **Post**: Publishes thread to Twitter
6. **Track**: Saves to database to prevent duplicates

## 🔧 Customization

### Change Posting Frequency
Edit `.env`:
```
SCAN_INTERVAL_HOURS=6  # Post every 6 hours instead of 8
TWEETS_PER_DAY=4       # Post 4 tweets per day instead of 3
```

### Add More News Sources
Edit `config.py` and add RSS feeds to the `RSS_FEEDS` list:
```python
RSS_FEEDS = [
    "https://your-favorite-news-site.com/rss",
    # ... existing feeds
]
```

### Modify Analysis Tone
Edit `config.py` and customize the `ANALYSIS_PROMPT` to change how Claude analyzes news.

## 🐛 Troubleshooting

### "ANTHROPIC_API_KEY not found"
- Make sure your `.env` file exists in the `crypto-twitter-bot` folder
- Check that keys are on separate lines without spaces around `=`

### "Twitter API connection failed"
- Verify all 4 Twitter credentials are correct
- Make sure your app has "Read and Write" permissions
- Regenerate tokens if needed

### "No articles found"
- RSS feeds might be temporarily down (normal)
- Try running again in a few hours

### How to check what was posted
The database stores everything. To view:
```bash
sqlite3 news_history.db "SELECT posted_at, title FROM posted_news ORDER BY posted_at DESC LIMIT 10;"
```

## 🚀 Running 24/7 (Advanced)

### Option 1: Keep Mac Awake
Use the `caffeinate` command:
```bash
caffeinate -s python main.py
```

### Option 2: Run on a Server
Deploy to a free cloud service:
- **Railway.app**: Free tier, easy deployment
- **Render.com**: Free tier with scheduled jobs
- **AWS EC2**: Free tier for 1 year

### Option 3: GitHub Actions (Scheduled)
Run 3x daily without a server (free). Let me know if you want this setup!

## 📊 Expected Costs

- **Anthropic API**: ~$0.50-2/month (very low usage)
- **Twitter API**: Free (v2 Essential tier)
- **Total**: Essentially free!

## 🛡️ Security Notes

- **NEVER** share your `.env` file
- **NEVER** commit `.env` to Git (it's in `.gitignore`)
- Store API keys securely

## 📝 Notes for Beginners

- **Virtual environment** (`.venv`): Keeps this project's packages separate from your system
- **Activate before running**: Always run `source .venv/bin/activate` before using the bot
- **Logs**: The bot prints detailed logs so you can see what it's doing
- **Database**: `news_history.db` is created automatically - don't delete it!

## 🆘 Need Help?

If something doesn't work:
1. Check the error message in the terminal
2. Verify your API keys in `.env`
3. Make sure virtual environment is activated (you should see `(.venv)` in terminal)
4. Try running in test mode first: `python main.py --once`

---

**Built with**: Python, Claude AI, Twitter API v2, RSS Feeds, SQLite
