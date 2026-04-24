import os
import requests
import feedparser
from anthropic import Anthropic

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]

# RSS feeds to pull from
RSS_FEEDS = [
    "https://tldr.tech/api/rss/ai",                       # TLDR AI
    "https://tldr.tech/api/rss/dev",                      # TLDR Dev
    "https://tldr.tech/api/rss/tech",                     # TLDR Tech
    "https://www.artificialintelligence-news.com/feed/",  # AI News
    "https://simonwillison.net/atom/everything/",         # Simon Willison (Claude/LLM expert)
    "https://github.blog/feed/",                          # GitHub Blog (Copilot, Codespaces)
]

MAX_ITEMS_PER_FEED = 5  # how many articles to pull per feed
# ─────────────────────────────────────────────────────────────────────────────


def fetch_articles() -> list[dict]:
    """Pull recent articles from all RSS feeds."""
    articles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
                articles.append({
                    "title":   entry.get("title", "No title"),
                    "summary": entry.get("summary", entry.get("description", "")),
                    "link":    entry.get("link", ""),
                    "source":  feed.feed.get("title", url),
                })
        except Exception as e:
            print(f"⚠️  Could not fetch {url}: {e}")
    return articles


def summarize_with_claude(articles: list[dict]) -> str:
    """Ask Claude to produce a clean daily digest."""
    if not articles:
        return "No AI news articles found today."

    # Build a compact text block for Claude
    articles_text = "\n\n".join(
        f"[{a['source']}] {a['title']}\n{a['summary'][:300]}\n{a['link']}"
        for a in articles
    )

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": (
                "You are a tech news curator for a senior software developer who loves AI and developer tooling.\n"
                "Below are today's raw articles. Create a concise daily digest for Telegram.\n\n"
                "Priority topics (highlight these first if present):\n"
                "1. Claude Code, Anthropic updates, Claude models\n"
                "2. AI coding tools (Cursor, Copilot, Devin, Codeium, etc.)\n"
                "3. Developer tools, frameworks, and productivity\n"
                "4. General AI/LLM news and research\n\n"
                "Format rules:\n"
                "- Start with: 🤖 *AI & Dev Digest – [today's date]*\n"
                "- Group into two sections: *🛠 Dev & Claude Code* and *🧠 AI News*\n"
                "- List 4–5 stories per section\n"
                "- Each story: one bold title + 1-2 sentence summary + URL on its own line\n"
                "- Use simple Telegram markdown (* for bold, no # headers)\n"
                "- End with a short 'That's a wrap!' line\n\n"
                f"Articles:\n{articles_text}"
            )
        }]
    )
    return response.content[0].text


def send_telegram(text: str) -> None:
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    print("✅ Message sent to Telegram!")


def main():
    print("📡 Fetching articles...")
    articles = fetch_articles()
    print(f"   Found {len(articles)} articles across {len(RSS_FEEDS)} feeds.")

    print("🧠 Summarising with Claude...")
    digest = summarize_with_claude(articles)

    print("📨 Sending to Telegram...")
    send_telegram(digest)


if __name__ == "__main__":
    main()
