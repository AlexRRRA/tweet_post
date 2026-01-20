"""AI analyzer using LLM via OpenRouter to generate institutional-grade analysis."""

import os
import re
from datetime import datetime
from typing import List, Dict
import logging
import httpx
from openai import OpenAI

from config import MAX_TWEET_LENGTH, LLM_MODEL

# System prompt for Trader's Desk persona - CLEAN THREAD FORMAT
SYSTEM_PROMPT = """You are a SENIOR CRYPTO PROPRIETARY TRADER writing a research note for X/Twitter.

=== YOUR MISSION ===

Write a SINGLE-SUBJECT analysis on the provided news story. You are explaining this to sophisticated traders. Use "We" and "Our Desk" language.

This is NOT a news summary. This is a TRADER'S ANALYSIS explaining WHY this matters and WHAT the market implications are.

=== ACCURACY RULES (NON-NEGOTIABLE) ===

1. **SINGLE SUBJECT FOCUS:** Analyze ONLY the news item provided. Go DEEP on ONE topic.

2. **SOURCE-BASED FACTS:** Only cite facts from the news. Do NOT invent numbers or events. You MAY add factual context.

3. **NO TRADING INSTRUCTIONS:** FORBIDDEN: "Buy", "Sell", "Long", "Short". ALLOWED: "Bullish for...", "We see risk/reward skewed to..."

=== LOGICAL SANITY RULES (CRITICAL) ===

**NO FORCED CAUSALITY:**
- Do NOT link niche geopolitical events (e.g., trade disputes in small nations, obscure regional conflicts) to Crypto price action unless there is a DIRECT, PROVEN correlation.
- Bad example: "Greenland tariffs caused BTC to drop" - This is FAKE and FORCED.
- If the connection between the news and crypto is weak or speculative, DO NOT fabricate a link.

**OPTIONAL CRYPTO STANCE:**
- If the news is purely Macro/TradFi (e.g., US tariffs on Europe, regional trade policy), analyze the MACRO impact first:
  - How does it affect inflation, the Dollar Index (DXY), bond yields, or risk appetite?
- You do NOT need to force a "Bitcoin Stance" if the link to crypto is weak.
- If the event has no direct impact on Crypto, simply explain the event and its significance for the general economy.
- Good example: "US announces tariffs on European nations. This may strengthen the DXY and put pressure on risk assets globally. Markets await Fed response."

**OBJECTIVE REPORTING:**
- Be professional and objective. Do not manufacture bullish/bearish takes for engagement.
- If the crypto angle is unclear, end with a neutral macro observation rather than a forced crypto stance.

=== TONE & VOCABULARY ===

Voice: First-person plural ("We", "Our desk", "Our view")
Style: Opinionated but professional. Like a morning desk note.

USE trader language: risk/reward, liquidity, order flow, structural bid, positioning, capitulation, squeeze, thesis validation, regime shift, repricing

=== OUTPUT FORMAT (CRITICAL) ===

Output a CLEAN thread with NO LABELS or HEADERS. Just natural paragraphs separated by double newlines.

Structure your response as:

PARAGRAPH 1 (Hook + Facts):
Start with a punchy one-liner hook, then state the key facts from the news. (2-3 sentences total)

PARAGRAPH 2 (Deep Dive):
Why does this matter? Explain second-order effects, market structure implications, what most people are missing. (4-6 sentences)

PARAGRAPH 3 (Desk View + Tags):
State the institutional view directly as the final paragraph. Do NOT use the label 'Stance:'. Just write the conclusion naturally.
- If crypto-relevant: End with 2 tags like $BTC #Macro
- If purely macro: End with macro tags like #Fed #DXY or #Macro #RiskOff
Remember: A forced crypto stance is worse than an objective macro observation.

=== BANNED ===

- ANY labels/headers like [HEADLINE], [THE MECHANICS], **Section**, Tweet 1:, etc.
- Retail language: "moon", "HODL", "gem", "LFG", "WAGMI"
- Emojis
- Hedging: "could go either way", "time will tell"

=== EXAMPLE OUTPUT ===

The Fed just blinked. Chicago Fed President Goolsbee warned that inflation could "roar back" if central bank independence is compromised—a rare public acknowledgment of political pressure on monetary policy.

This isn't routine Fed speak. When a voting member explicitly defends institutional autonomy, it signals internal concern about external interference. Our desk sees this as the Fed pre-positioning narrative defense ahead of potential policy clashes. The subtext: rate cuts may face political headwinds that markets aren't pricing. If independence becomes a campaign issue, expect volatility around FOMC dates to spike.

We're treating this as a yellow flag for risk assets. The Fed's credibility is the anchor for long-duration trades—any cracks there ripple through everything from bonds to growth tech to crypto. Cautious on rate-sensitive assets until political noise clears.

$BTC #Macro
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_llm_response(text: str) -> str:
    """
    Clean LLM response by removing reasoning traces.
    DeepSeek R1 outputs <think>...</think> tags with reasoning.
    This function strips those out to get the final answer.
    """
    if not text:
        return ""
    # Remove all content between <think> and </think> tags (including the tags)
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Clean up any extra whitespace left behind
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned).strip()
    return cleaned


# System prompt for AI headline curation
CURATION_PROMPT = """You are a Crypto Fund Manager responsible for filtering news for your investment team.

=== CRITICAL DATE CONTEXT ===
Today is {current_date}. The current year is {current_year}.
You must ONLY select news that was released in the last 24 hours.
REJECT any headlines that reference events from 2025 or earlier as if they are current news.
If a headline mentions "2025", "2024", or "2023", it is likely stale cached content - SKIP IT.

Your job is to identify the most CRITICAL headlines for institutional investors.
Prioritize TOPIC DIVERSITY - do not select multiple headlines on the same theme.

PRIORITY CATEGORIES (in order of importance):
1. **Fed & Central Bank Policy**: Interest rates, QT/QE, Fed communications, Treasury movements
2. **Global Crypto Regulation**: SEC, CFTC, EU MiCA, Asia policies, congressional hearings, legal rulings
3. **Stablecoins & Payments**: USDC/USDT news, CBDC developments, payment integrations
4. **Market Structure & Liquidity**: M2 supply, global liquidity, exchange events, whale movements
5. **Major Protocol Events**: Hard forks, major upgrades, security incidents, large hacks

=== ETF FATIGUE RULE (IMPORTANT) ===
ETF news should ONLY be selected if it represents a MAJOR STRUCTURAL CHANGE:
- ✅ SELECT: New ETF approval, record-breaking single-day flow, major issuer entering/exiting
- ❌ SKIP: Routine daily inflows/outflows, minor flow updates, standard trading volume
If the news is just "BTC ETF saw $X million inflow today", rank it LOWER than:
- A new regulatory bill or policy announcement
- A Fed statement or rate decision
- A stablecoin regulatory action
Do NOT post about ETF flows every single day unless a significant record is broken.

IGNORE:
- Minor altcoin news without institutional relevance
- General "price up/down" articles without substance
- Promotional content or partnership announcements
- Opinion pieces without new information
- Routine daily ETF flow updates (see ETF Fatigue Rule above)

OUTPUT FORMAT:
Return ONLY the numeric IDs of the top 5 most critical headlines, separated by commas.
Example: 3, 7, 12, 23, 41

Do NOT include any explanation. ONLY output the IDs."""


class NewsAnalyzer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        # Create httpx client without proxies to avoid Railway proxy issues
        http_client = httpx.Client()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            http_client=http_client
        )

    def select_top_headlines(self, headlines: List[Dict], top_k: int = 5, topic: str = None) -> List[int]:
        """
        Use AI to select the most important headlines for institutional investors.

        Args:
            headlines: List of {id, title, source} dictionaries
            top_k: Number of headlines to select
            topic: Optional keyword filter (case-insensitive)

        Returns:
            List of selected article IDs
        """
        if not headlines:
            logger.warning("No headlines to curate")
            return []

        # Apply topic filter if provided
        if topic:
            topic_lower = topic.lower()
            filtered = [h for h in headlines if topic_lower in h['title'].lower()]
            if filtered:
                logger.info(f"Topic filter '{topic}' matched {len(filtered)} headlines")
                headlines = filtered
            else:
                logger.warning(f"Topic '{topic}' not found in any headlines. Reverting to auto-mode.")

        # Format headlines for the LLM
        headlines_text = "\n".join([
            f"[{h['id']}] {h['title']} (Source: {h['source']})"
            for h in headlines
        ])

        user_prompt = f"""Review these {len(headlines)} headlines and select the TOP {top_k} most critical for institutional crypto investors.

{headlines_text}

Return ONLY the {top_k} IDs, separated by commas (e.g., 3, 7, 12, 23, 41):"""

        try:
            logger.info(f"AI curating {len(headlines)} headlines...")

            # Inject current date into curation prompt to prevent selecting stale news
            current_date = datetime.now().strftime("%A, %B %d, %Y")
            current_year = datetime.now().year
            dynamic_curation_prompt = CURATION_PROMPT.format(
                current_date=current_date,
                current_year=current_year
            )

            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                max_tokens=100,
                messages=[
                    {"role": "system", "content": dynamic_curation_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            raw_response = response.choices[0].message.content or ""

            # Clean LLM response (remove <think>...</think> reasoning traces)
            response_text = clean_llm_response(raw_response)
            logger.info(f"AI selected IDs: {response_text}")

            # Parse the IDs from response
            selected_ids = []
            for part in response_text.replace(" ", "").split(","):
                try:
                    selected_ids.append(int(part))
                except ValueError:
                    continue

            # Validate IDs exist in headlines
            valid_ids = {h["id"] for h in headlines}
            selected_ids = [id for id in selected_ids if id in valid_ids][:top_k]

            logger.info(f"AI selected {len(selected_ids)} articles: {selected_ids}")
            return selected_ids

        except Exception as e:
            logger.error(f"Error in AI curation: {e}")
            # Fallback: return first top_k IDs
            return [h["id"] for h in headlines[:top_k]]

    def analyze_news(self, articles: List[Dict]) -> List[str]:
        """
        Analyze news articles and generate institutional-grade tweets.

        Uses the Institutional Macro Strategist persona to synthesize
        market-moving information into actionable intelligence.

        Args:
            articles: List of news articles to analyze

        Returns:
            List of tweet texts (up to 3 tweets)
        """
        if not articles:
            logger.warning("No articles to analyze")
            return []

        # Format news content for LLM
        news_content = self._format_articles(articles)

        # Inject current date into system prompt to prevent temporal hallucinations
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        current_year = datetime.now().year
        date_context = f"""=== CRITICAL DATE CONTEXT (NON-NEGOTIABLE) ===

Today is {current_date}. The current year is {current_year}.

STRICT RULES:
1. You must ONLY analyze news provided in the context that was released in the last 24 hours.
2. Do NOT reference historical data from 2025, 2024, or 2023 as if it were current news.
3. If the news mentions "this year", it means {current_year}.
4. If any content seems to reference 2025 or 2024 events as recent, IGNORE that content.
5. All price references, market events, and analysis must be relevant to January {current_year}.

The bot previously posted outdated news causing critical errors. You are the last line of defense.

"""
        dynamic_system_prompt = date_context + SYSTEM_PROMPT

        # User message with the news data
        user_prompt = f"""Analyze this news story for our trading desk.

RULES:
- NO headers or labels (no [HEADLINE], no **Section**, no "Tweet 1:")
- Output clean paragraphs separated by blank lines
- End with your view as a natural sentence + 2 tags on the final line

**News Story:**
{news_content}

Write the analysis now. Start directly with the hook."""

        try:
            logger.info("Sending articles to LLM for institutional analysis...")

            # Call OpenRouter API with system prompt for persona
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                max_tokens=1024,
                messages=[
                    {
                        "role": "system",
                        "content": dynamic_system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            # Extract the response
            raw_response = response.choices[0].message.content or ""
            logger.info(f"LLM response received: {len(raw_response)} characters")

            # Clean LLM response (remove <think>...</think> reasoning traces)
            response_text = clean_llm_response(raw_response)

            # Parse tweets from response
            tweets = self._parse_tweets(response_text)

            return tweets

        except Exception as e:
            logger.error(f"Error calling LLM API: {e}")
            return []
    
    def _format_articles(self, articles: List[Dict]) -> str:
        """Format articles into a readable text block for LLM."""
        formatted = []
        
        for i, article in enumerate(articles, 1):
            formatted.append(f"{i}. **{article['title']}**")
            formatted.append(f"   Source: {article['source']}")
            if article.get('summary'):
                formatted.append(f"   Summary: {article['summary']}")
            formatted.append("")  # Blank line
        
        return "\n".join(formatted)
    
    def _parse_tweets(self, response: str) -> List[str]:
        """
        Parse LLM's response for X Premium long-form posts.

        For X Premium (4000 char limit), we keep the entire response as ONE post.
        """
        # Clean up the response but preserve structure (newlines for readability)
        cleaned = response.strip()

        # Skip if empty or too short
        if len(cleaned) < 50:
            return []

        # Truncate if exceeds X Premium limit
        if len(cleaned) > MAX_TWEET_LENGTH:
            cleaned = cleaned[:MAX_TWEET_LENGTH - 3] + "..."

        # Return as single post (X Premium deep-dive format)
        return [cleaned]
