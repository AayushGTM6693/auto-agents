import aiohttp
import asyncio
from ..core.config import settings
from typing import List, Dict, Optional, Any

class NewsService:
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self.base_url = ""
        self.session:Optional[aiohttp.ClientSession] = None

        #rate limiting
        self.rate_limit_delay = 1
        self.last_req_time = 0
        #session object

    async def __aenter__(self):
        # async context manager ->
        self.session = aiohttp.ClientSession(
            timeout= aiohttp.ClientTimeout(total=30),
            headers = {
                "User-Agent": 'NewsService',
                'X-API-KEY' : ""
            }

        )
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # close http session
        if self.session:
            await self.session.close()

    async def __rate_limit_check__(self):
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_req_time
        if time_since_last < self.rate_limit_delay:
            sleepTime = self.rate_limit_delay - time_since_last
            await asyncio.sleep(sleepTime)
        self.last_req_time = time.time()

    async def fetch_everything_news(self, keywords:str,sources,language:str = "en", page_size:int = 10)-> List[Dict]:
        """
               Fetch news articles from NewsAPI /everything endpoint

               This is the core function - similar to how Cardano agents
               fetch blockchain data for analysis.

               Args:
                   keywords: Search terms (e.g., "AI OR machine learning")
                   sources: Specific news sources (e.g., "techcrunch,bbc-news")
                   language: Article language
                   page_size: Number of articles to fetch

               Returns:
                   List of article dictionaries
               """
        await self.__rate_limit_check__()
        params  = {
            "q":keywords,
            "language":language,
            "sortBy" : "publishedAt",
            "page_size" : min(page_size, 100),
            "api_key" : self.api_key
        }

        if sources:
            params['sources'] = sources


        try:
            if not self.session:
                raise RuntimeError("it needs to have context")

            async with self.session.get(f"{self.base_url}/everything",params=params) as response:
                #handle http codes
                if response.status == 200:
                    data = await response.json()
                    return data.get("articles",[])
                elif response.status == 429:
                    print("rate limit exceeded")
                    await asyncio.sleep(60)
                    return await self.fetch_everything_news(keywords,sources,language,page_size)
                elif response.status == 401:
                    print("invalid api key")
                    raise Exception("invalid api key")

                elif response.status == 400:
                    error_data = await response.json()
                    raise Exception(f"bad request {error_data}")
                else:
                    print("unexpected status code")
                    return []

        except aiohttp.ClientError as e:

            print(f"network error {e}")
            return[]
        except Exception as e:
            print(f"unkown error {e}")
            return []

    async def fetch_top_headline(self, category:Optional[str]=None, country:str ='us', page_size:int =10):
        await self.__rate_limit_check__()

        params = {
            "country": country,
            "page_size" : page_size,
            "api-key":""

        }
        if category:
            params["category"] = category

        try:
           #session check
           if not self.session:
               raise Exception("user context hunu parxa")

           async with self.session.get(f"{self.base_url}/top-headlines", params = params) as response:
             if response.status == 200:
               data = await response.json()
               return data.get("articles", [])
             else:
                 print(f"fetch failed {response.status}")
                 return []
        except Exception as e:
            print(f"unkown error {e}")
            return []

    def analyze_keywords_match(self, articles:Dict, keywords: List[str])->Dict[str,Any]:
        """
               Analyze how well an article matches our keywords

               This is crucial for agent decision-making:
               - Which articles are most relevant?
               - Should we trigger actions based on this article?
               - How confident are we in the match?

               Returns:
                   {
                       "matched_keywords": ["AI", "technology"],
                       "match_score": 0.75,  # 0-1 confidence score
                       "match_locations": {
                           "title": ["AI"],
                           "description": ["technology"]
                       }
                   }
               """


        title = (articles.get("title") or "").lower()
        description = (articles.get("description") or "").lower()
        content = (articles.get("content") or "").lower()

        matched_keyword = []
        matched_locations = {"title":[], "description":[], "content":[]}

        for keyword in keywords:
            keyword_lower = keyword.strip().lower()

            if (keyword_lower in title):
                matched_keyword.append(keyword)
                matched_locations["title"].append(keyword)

            elif (keyword_lower in description):
                matched_keyword.append(keyword)
                matched_locations["description"].append(keyword)
            elif(keyword_lower in content):
                matched_keyword.append(keyword)
                matched_locations['content'].append(keyword)

        # calc score

        title_matches = 0
        description_matches = 0
        content_matches = 0

        if not keywords:
            matched_score = 0

        else:
            title_matches = len(matched_locations["title"])
            description_matches = len(matched_locations['description'])
            content_matches = len(matched_locations['content'])

        weighted_score = (title_matches * 1 + description_matches * 0.7 + content_matches * 0.3)

        matched_score = min(weighted_score/len(keywords), 1.0)

        return {
            "matched_keywords": list(set(matched_keyword)), #remove duplicate
            "matched_score": round(matched_score,2),
            "total_matched": len(set(matched_keyword)),
            "matched_locations": matched_locations


        }
    def is_article_recent(self,article:dict , max_age_hours:int = 24):
        #check freshness of article
        from datetime import datetime , timezone, timedelta

        published_at = article.get("publishedAt")
        if not published_at:
            return False

        try:
            article_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

            max_time  = timedelta(hours =max_age_hours )


         #compare -> current - article time < max

            return (datetime.now(timezone.utc) - article_time <= max_time)

        except (ValueError, TypeError):
            return False

    def filter_quality_articles(self, articles: List[Dict]) -> List[Dict]:
        quality_articles = []

        for article in articles:
            if not article.get("title") or not article.get("url"):
                continue
            elif article.get("title") == ['removed']:
                continue
            elif len(article.get("description",""))< 30:
                continue
            elif not article.get("description"):
                continue
            else:
                quality_articles.append(article)



        return quality_articles
