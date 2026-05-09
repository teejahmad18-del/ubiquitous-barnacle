#!/usr/bin/env python3
"""
X/Twitter Original Tweets Scraper - FIXED
Scrapes recent 200 ORIGINAL tweets from users in users.txt
Excludes: replies, retweets, quote tweets
Note: view_count is not available through the bird library Twitter API
"""

import os
import time
import json
import subprocess
import sys
from datetime import datetime
from typing import List, Tuple, Optional

# ============================================================
# INSTALL DEPENDENCIES
# ============================================================
print("📦 Checking dependencies...")
try:
    from bird import TwitterClient
    print("   ✅ bird library already installed")
except ImportError:
    print("   📥 Installing bird library...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "bird", "-q"])
    from bird import TwitterClient
    print("   ✅ bird library installed")

# ============================================================
# CONFIGURATION
# ============================================================
COOKIES_FOLDER = "cookies"
INPUT_FILE = "users.txt"
OUTPUT_FILE = "tweets_scraped.json"
MAX_RETRIES = 3
DELAY_BETWEEN_USERS = 3
DELAY_ON_RATE_LIMIT = 300
TWEETS_PER_USER = 200
TWEETS_PER_SEARCH = 40

# ============================================================
# COOKIE MANAGEMENT
# ============================================================
def extract_tokens_from_cookie_file(cookie_file_path: str) -> Tuple[Optional[str], Optional[str]]:
    cookies = {}
    try:
        with open(cookie_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]
        return cookies.get("auth_token"), cookies.get("ct0")
    except Exception as e:
        print(f"   ⚠️ Error reading {cookie_file_path}: {e}")
        return None, None

# ============================================================
# SETUP COOKIES
# ============================================================
if not os.path.exists(COOKIES_FOLDER):
    os.makedirs(COOKIES_FOLDER)

cookie_files = [f for f in os.listdir(COOKIES_FOLDER) if f.endswith('.txt') and not f.startswith('.')]

if not cookie_files:
    print("\n⚠️ NO COOKIE FILES FOUND!")
    try:
        from google.colab import files
        import zipfile
        print("📤 Please upload cookie files...")
        uploaded = files.upload()
        for filename, content in uploaded.items():
            if filename.endswith('.zip'):
                with open(filename, 'wb') as f:
                    f.write(content)
                with zipfile.ZipFile(filename, 'r') as zip_ref:
                    zip_ref.extractall(COOKIES_FOLDER)
                os.remove(filename)
            elif filename.endswith('.txt'):
                filepath = os.path.join(COOKIES_FOLDER, filename)
                with open(filepath, 'wb') as f:
                    f.write(content)
        cookie_files = [f for f in os.listdir(COOKIES_FOLDER) if f.endswith('.txt') and not f.startswith('.')]
    except:
        print("❌ Cannot upload files")
        sys.exit(1)

print(f"✅ Found {len(cookie_files)} cookie files")

accounts = []
for cf in cookie_files:
    fp = os.path.join(COOKIES_FOLDER, cf)
    auth, ct0 = extract_tokens_from_cookie_file(fp)
    if auth and ct0:
        accounts.append((auth, ct0, cf))
        print(f"   ✅ Loaded: {cf}")

if not accounts:
    print("\n❌ No valid accounts found!")
    sys.exit(1)

print(f"✅ Loaded {len(accounts)} valid account(s)")

# ============================================================
# COOKIE ROTATOR
# ============================================================
class CookieRotator:
    def __init__(self, accounts):
        self.accounts = accounts
        self.index = 0
        self.cooldowns = {}
        self.failures = [0] * len(accounts)
        self.max_failures = 3

    def get_client(self):
        now = time.time()
        for _ in range(len(self.accounts)):
            if (now >= self.cooldowns.get(self.index, 0) and
                self.failures[self.index] < self.max_failures):
                auth_token, ct0, desc = self.accounts[self.index]
                try:
                    client = TwitterClient(auth_token=auth_token, ct0=ct0)
                    current_index = self.index
                    self.index = (self.index + 1) % len(self.accounts)
                    return client, current_index
                except Exception as e:
                    print(f"   ⚠️ Error: {str(e)[:100]}")
                    self.failures[self.index] += 1
            self.index = (self.index + 1) % len(self.accounts)

        min_wait = min(self.cooldowns.values()) if self.cooldowns else 0
        wait_time = max(0, min_wait - now)
        if wait_time > 0:
            print(f"   ⏳ All accounts cooling down. Waiting {wait_time:.0f}s...")
            time.sleep(wait_time)
        return self.get_client()

    def mark_rate_limited(self, idx):
        self.cooldowns[idx] = time.time() + DELAY_ON_RATE_LIMIT
        print(f"   🚫 Rate limited. Cooling down {DELAY_ON_RATE_LIMIT}s")

    def mark_failed(self, idx):
        self.failures[idx] += 1

# ============================================================
# LOAD USERS
# ============================================================
def load_usernames(filepath: str) -> List[str]:
    if not os.path.exists(filepath):
        print(f"\n❌ File '{filepath}' not found!")
        return []

    usernames = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            username = line.strip()
            if username and not username.startswith('#'):
                if username.startswith('@'):
                    username = username[1:]
                usernames.append(username)
    return usernames

# ============================================================
# TWEET FILTERING - FIXED
# ============================================================
def is_original_tweet(tweet) -> bool:
    """
    Check if a tweet is an original tweet (not reply, retweet, or quote tweet)
    Based on actual bird library attributes
    """
    # Check if it's a reply
    if hasattr(tweet, 'in_reply_to_status_id'):
        reply_id = tweet.in_reply_to_status_id
        if reply_id and str(reply_id) not in ['None', '', '0']:
            return False

    # Check if it's a quote tweet (bird uses 'quoted_tweet' not 'quoted_status')
    if hasattr(tweet, 'quoted_tweet') and tweet.quoted_tweet is not None:
        return False

    # Check text for RT prefix (retweet)
    if hasattr(tweet, 'text'):
        text = tweet.text.strip()
        if text.startswith('RT @'):
            return False
        # Check if it starts with @ (reply)
        if text.startswith('@'):
            return False

    return True

# ============================================================
# DATE PARSING FOR SORTING
# ============================================================
def parse_twitter_date(date_str: str) -> datetime:
    """Parse Twitter's date format to datetime for sorting"""
    try:
        # Format: 'Sun May 03 18:42:24 +0000 2026'
        return datetime.strptime(date_str, '%a %b %d %H:%M:%S %z %Y')
    except:
        try:
            # Alternative format without timezone
            return datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y')
        except:
            return datetime.min

# ============================================================
# TWEET EXTRACTION
# ============================================================
def extract_tweet_data(tweet) -> dict:
    """Extract relevant data from a tweet object"""
    return {
        'id': getattr(tweet, 'id', ''),
        'text': getattr(tweet, 'text', ''),
        'created_at': str(getattr(tweet, 'created_at', '')),
        'like_count': getattr(tweet, 'like_count', 0) or 0,
        'retweet_count': getattr(tweet, 'retweet_count', 0) or 0,
        'reply_count': getattr(tweet, 'reply_count', 0) or 0,
        'view_count': None,  # Not available in bird library
    }

def fetch_original_tweets(client, username: str, max_tweets: int = TWEETS_PER_USER) -> List[dict]:
    """
    Fetch only ORIGINAL tweets from a user using search
    Excludes replies, retweets, and quote tweets
    """
    all_tweets = []
    seen_ids = set()

    try:
        # Use search with filters to exclude replies and retweets
        print(f"      Fetching original tweets...")
        query = f"from:{username} -filter:replies -filter:retweets"
        result = client.search(query, count=TWEETS_PER_SEARCH)

        if isinstance(result, tuple) and len(result) >= 1:
            tweets = result[0]
            if tweets:
                for tweet in tweets:
                    tweet_id = getattr(tweet, 'id', '')
                    if tweet_id and tweet_id not in seen_ids:
                        # Filter out quote tweets and any other non-original tweets
                        if is_original_tweet(tweet):
                            seen_ids.add(tweet_id)
                            all_tweets.append(extract_tweet_data(tweet))

                print(f"         +{len(all_tweets)} original tweets")

        # If we need more tweets, try to get older ones
        if len(all_tweets) < max_tweets and all_tweets:
            # Get the oldest tweet date
            oldest_date = None
            for tweet in all_tweets:
                created_str = tweet.get('created_at', '')
                if created_str:
                    parsed = parse_twitter_date(created_str)
                    if oldest_date is None or parsed < oldest_date:
                        oldest_date = parsed

            if oldest_date:
                until_date = oldest_date.strftime('%Y-%m-%d')
                print(f"      Fetching older tweets before {until_date}...")

                query = f"from:{username} -filter:replies -filter:retweets until:{until_date}"
                result = client.search(query, count=TWEETS_PER_SEARCH)

                if isinstance(result, tuple) and len(result) >= 1:
                    tweets = result[0]
                    if tweets:
                        new_count = 0
                        for tweet in tweets:
                            tweet_id = getattr(tweet, 'id', '')
                            if tweet_id and tweet_id not in seen_ids:
                                if is_original_tweet(tweet):
                                    seen_ids.add(tweet_id)
                                    all_tweets.append(extract_tweet_data(tweet))
                                    new_count += 1
                        print(f"         +{new_count} original tweets (Total: {len(all_tweets)})")

    except Exception as e:
        print(f"      ❌ Error fetching tweets: {str(e)[:100]}")

    # Sort by created_at (most recent first)
    all_tweets.sort(key=lambda x: parse_twitter_date(x.get('created_at', '')), reverse=True)

    # Limit to max_tweets
    return all_tweets[:max_tweets]

# ============================================================
# MAIN SCRAPER
# ============================================================
print("\n" + "="*60)
print("📊 X/TWITTER ORIGINAL TWEETS SCRAPER")
print("="*60)

# Load users
print(f"\n📋 Loading users from '{INPUT_FILE}'...")
usernames = load_usernames(INPUT_FILE)

if not usernames:
    print(f"\n❌ No usernames found in '{INPUT_FILE}'!")
    sys.exit(1)

# Remove duplicates
unique_usernames = []
seen = set()
for u in usernames:
    if u.lower() not in seen:
        seen.add(u.lower())
        unique_usernames.append(u)

print(f"✅ Loaded {len(unique_usernames)} unique usernames")
print(f"📊 Target: Up to {TWEETS_PER_USER} original tweets per user")
print(f"🚫 Excluding: Replies, Retweets, Quote Tweets")
print(f"⚠️  Note: View counts not available via bird library API")
print()

rotator = CookieRotator(accounts)
all_results = {}
start_time = time.time()

print("="*60)
print("🔍 SCRAPING ORIGINAL TWEETS ONLY...")
print("="*60)

for i, username in enumerate(unique_usernames, 1):
    print(f"\n[{i:4d}/{len(unique_usernames)}] @{username}")
    print("-" * 40)

    success = False
    for attempt in range(MAX_RETRIES):
        try:
            client, acc_idx = rotator.get_client()
            tweets = fetch_original_tweets(client, username, TWEETS_PER_USER)

            if tweets:
                # Calculate stats
                total_likes = sum(t['like_count'] for t in tweets)
                total_retweets = sum(t['retweet_count'] for t in tweets)
                total_replies = sum(t['reply_count'] for t in tweets)

                all_results[username] = {
                    'username': username,
                    'tweets_count': len(tweets),
                    'tweets': tweets,
                    'stats': {
                        'total_likes': total_likes,
                        'total_retweets': total_retweets,
                        'total_replies': total_replies
                    },
                    'fetched_at': datetime.now().isoformat()
                }
                print(f"   ✅ Total: {len(tweets)} original tweets")
                print(f"      ❤️ {total_likes} likes | 🔄 {total_retweets} RTs | 💬 {total_replies} replies")
            else:
                all_results[username] = {
                    'username': username,
                    'tweets_count': 0,
                    'tweets': [],
                    'stats': {
                        'total_likes': 0,
                        'total_retweets': 0,
                        'total_replies': 0
                    },
                    'fetched_at': datetime.now().isoformat()
                }
                print(f"   ⚠️ No original tweets found for @{username}")

            success = True
            break

        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg or "limit" in error_msg or "429" in error_msg:
                rotator.mark_rate_limited(acc_idx)
                print(f"   ❌ Rate limited")
                if attempt < MAX_RETRIES - 1:
                    print(f"   ⏳ Waiting {DELAY_ON_RATE_LIMIT}s...")
                    time.sleep(DELAY_ON_RATE_LIMIT)
            elif "not found" in error_msg or "404" in error_msg:
                print(f"   ❌ User not found")
                all_results[username] = {
                    'username': username,
                    'tweets_count': 0,
                    'tweets': [],
                    'stats': {},
                    'error': 'User not found',
                    'fetched_at': datetime.now().isoformat()
                }
                success = True
                break
            elif "401" in error_msg or "403" in error_msg:
                rotator.mark_failed(acc_idx)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5)
            else:
                print(f"   ❌ Error: {str(e)[:100]}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)

    if not success:
        print(f"   ❌ Failed after {MAX_RETRIES} attempts")
        all_results[username] = {
            'username': username,
            'tweets_count': 0,
            'tweets': [],
            'stats': {},
            'error': 'Failed after retries',
            'fetched_at': datetime.now().isoformat()
        }

    # Save progress every 5 users
    if i % 5 == 0:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'scraped_at': datetime.now().isoformat(),
                'total_users': len(unique_usernames),
                'users_processed': i,
                'tweets_per_user_target': TWEETS_PER_USER,
                'note': 'Original tweets only (no replies, retweets, or quote tweets). View counts not available via bird library.',
                'results': all_results
            }, f, indent=2, ensure_ascii=False)
        print(f"\n   💾 Progress saved at {i} users")

    # Delay between users
    if i < len(unique_usernames):
        time.sleep(DELAY_BETWEEN_USERS)

# ============================================================
# SAVE FINAL RESULTS
# ============================================================
elapsed_time = time.time() - start_time

total_tweets = sum(r.get('tweets_count', 0) for r in all_results.values())
total_likes = sum(r.get('stats', {}).get('total_likes', 0) for r in all_results.values())
total_retweets = sum(r.get('stats', {}).get('total_retweets', 0) for r in all_results.values())
total_replies = sum(r.get('stats', {}).get('total_replies', 0) for r in all_results.values())
users_with_tweets = sum(1 for r in all_results.values() if r.get('tweets_count', 0) > 0)
users_without_tweets = sum(1 for r in all_results.values() if r.get('tweets_count', 0) == 0)

final_output = {
    'scraped_at': datetime.now().isoformat(),
    'total_users': len(unique_usernames),
    'users_with_tweets': users_with_tweets,
    'users_without_tweets': users_without_tweets,
    'total_tweets_scraped': total_tweets,
    'total_likes': total_likes,
    'total_retweets': total_retweets,
    'total_replies': total_replies,
    'tweets_per_user_target': TWEETS_PER_USER,
    'elapsed_seconds': round(elapsed_time, 1),
    'note': 'Original tweets only (no replies, retweets, or quote tweets). View counts not available via bird library API.',
    'results': all_results
}

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(final_output, f, indent=2, ensure_ascii=False)

# ============================================================
# DISPLAY SUMMARY
# ============================================================
print(f"\n{'='*60}")
print(f"📊 SCRAPING COMPLETE")
print(f"{'='*60}")
print(f"Total users processed: {len(unique_usernames)}")
print(f"Users with original tweets: {users_with_tweets}")
print(f"Users without original tweets: {users_without_tweets}")
print(f"Total original tweets scraped: {total_tweets}")
print(f"Total likes: {total_likes:,}")
print(f"Total retweets: {total_retweets:,}")
print(f"Total replies: {total_replies:,}")
if len(unique_usernames) > 0:
    print(f"Average tweets per user: {total_tweets/len(unique_usernames):.1f}")

if total_tweets > 0 and elapsed_time > 0:
    print(f"Speed: {total_tweets/elapsed_time:.1f} tweets/second")

# Show top users by tweet count
if all_results:
    print(f"\n📈 Top Users by Original Tweets:")
    top_users = sorted(all_results.items(), key=lambda x: x[1].get('tweets_count', 0), reverse=True)[:10]
    for i, (username, data) in enumerate(top_users, 1):
        count = data.get('tweets_count', 0)
        stats = data.get('stats', {})
        likes = stats.get('total_likes', 0)
        print(f"   {i:2d}. @{username}: {count} tweets | {likes:,} likes")

# Check if any users got 0 tweets
if users_without_tweets > 0:
    print(f"\n⚠️ Users with 0 original tweets:")
    for username, data in all_results.items():
        if data.get('tweets_count', 0) == 0:
            error = data.get('error', 'Unknown reason')
            print(f"   - @{username}: {error}")

# Save files
minutes = int(elapsed_time // 60)
seconds = int(elapsed_time % 60)
print(f"\n💾 Saved to: {OUTPUT_FILE}")
print(f"⏱️  Total time: {minutes}m {seconds}s")

print(f"\n{'='*60}")
print(f"✅ DONE!")
print(f"{'='*60}")
