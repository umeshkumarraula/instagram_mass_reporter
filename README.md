# instagram_mass_reporter

A Python tool to fetch and analyze Instagram posts for moderation keywords and suspicious content patterns.

## Quick Start

### Installation
```bash
pip install -r requirements.txt
python main.py
```

## Features

- **Bina login ke kisi bhi public Instagram post ka caption fetch karta hai** (Fetch captions from public Instagram posts without login)
- **Multiple methods try karta hai** — agar ek fail ho toh doosra (Multiple fallback methods - tries GraphQL, oEmbed, HTML scraping, and instagrapi)
- **Content Analysis** - Detects phishing, harmful content, and policy violations
- **Batch Processing** - Analyze multiple posts from JSON file
- **Proxy Support** - Optional proxy support via `proxies.txt`
- **Logging & Statistics** - Track analysis results and export to CSV

## Configuration

### Environment Variables
```bash
export IG_USERNAME="your_instagram_username"  # Optional - for advanced features
export IG_PASSWORD="your_instagram_password"  # Optional - for advanced features
```

### Optional Proxy Configuration
Create a `proxies.txt` file with one proxy per line:
```
http://proxy1.com:8080
http://proxy2.com:8080
http://proxy3.com:3128
```

## Usage

Run the main script:
```bash
python main.py
```

### Menu Options

1. **🔗 Instagram link → analyze + report** - Analyze a single Instagram post
2. **📝 Text manually analyze** - Manually analyze text content
3. **📂 Batch links (JSON file)** - Process multiple posts from a JSON file
4. **📊 Statistics** - View moderation statistics
5. **💾 CSV Export** - Export reports to CSV file
6. **🗑️ Clear logs** - Clear all logged data
7. **🚪 Exit** - Exit the application

## Content Detection

The tool detects various policy violations including:

- **Dangerous Content**: Suicide and self-injury, violence, dangerous organizations
- **Harassment**: Bullying, hate speech, harassment
- **Intellectual Property**: Copyright and trademark violations
- **Spam & Phishing**: 
  - Free money scams ('free money', 'claim prize', 'claim your reward')
  - Account verification scams ('verify your account', 'confirm your details')
  - Financial scams ('bitcoin investment', 'send money', 'western union')
  - Identity theft ('bank account details', 'ssn required', 'social security number')
  - Limited time offers ('limited offer', 'urgent action required', 'act now')
- **Sexual Content**: Nudity and sexual activity

## File Structure

```
instagram_mass_reporter/
├── main.py                 # Main application entry point
├── analyzer.py             # Content analysis engine
├── instagram_scraper.py    # Instagram post fetcher (multiple methods)
├── report_engine.py        # Automated reporting system
├── logger.py               # Logging and statistics
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Security Notes

- This tool is for legitimate content moderation and analysis
- Always respect Instagram's Terms of Service
- Use responsibly and ethically
- No credentials are stored in the codebase
- Proxy support is included to help with rate limiting
- Session data is stored locally in `logs/` directory

## Dependencies

- `requests` - HTTP requests
- `httpx` - Alternative HTTP client
- `nltk` - Natural language processing
- `textblob` - Text analysis and sentiment
- `instagrapi` - Instagram API client (optional, for advanced features)

## Tips & Troubleshooting

**If post fetching fails:**
1. Ensure the post is public
2. Try using a VPN
3. Add proxies to `proxies.txt`
4. Check if Instagram has blocked your IP - wait and retry

**For batch processing:**
- Create a JSON file with format: `[{"url": "https://instagram.com/p/..."}]`
- Max 100,000 posts per batch operation
- Adjust speed settings to avoid rate limiting

## License

This project is provided as-is for educational and legitimate content moderation purposes.

## Disclaimer

This tool should only be used for legitimate content moderation and analysis. Ensure you comply with Instagram's Terms of Service and all applicable laws and regulations.
