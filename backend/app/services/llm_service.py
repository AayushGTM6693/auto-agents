import json
import asyncio
from typing import Dict , List , Optional, Any
import aiohttp
from ..core.config import settings

class LLMService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name  = "gemini-1.5-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.session:Optional[aiohttp.ClientSession] = None

    #rate limit
        self.rate_limit_delay = 2
        self.last_req_time = 0

        #token usuage
        self.max_tokens_per_request = 1000
        self.daily_token_usage = 0
        self.daily_token_limit = 50000

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout = aiohttp.ClientTimeout(total = 60),
            headers= {
                "content-type":"application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        if self.session:
            await self.session.close()
        return self

    async def __rate_limit_check__(self):
            import time
            current_time = time.time()
            time_since_last = current_time - self.last_req_time
            if time_since_last < self.rate_limit_delay:
                sleepTime = self.rate_limit_delay - time_since_last
                await asyncio.sleep(sleepTime)
            self.last_req_time = time.time()

    async def analyze_article_relevance(self, article:Dict[str,Any], agent_keywords: List[str], agent_purpose:str = "Monitor technology news") -> Dict[str,Any]:
        #build prompt

        analysis_prompt = await self._build_analysis_prompt(article,agent_keywords,agent_purpose)
        #rate limiting check
        await self.__rate_limit_check__()

        try:
            #call api
            llm_response  = await self._call_llm_api(analysis_prompt)
            #parse
            analysis_result =  self._parse_llm_response(llm_response)
            #log
            self._update_token_usage_(llm_response.get("usage", {}))

            return analysis_result
        except Exception as e:
            print(f"error {e}")
            #fallback
            return self._fallback_keyword_analysis(article, agent_keywords)

    async def _build_analysis_prompt(self, article:Dict[str, Any], keywords: List[str], agent_purpose:str) -> str:



        #extract article content, title, desc, content, source
        title = article.get("title", "")
        description = article.get("description", "")
        content = article.get("content", "")[:2000]
        source = article.get("source", {}).get("name", "Unknown")

        # build a prompt
        prompt = f"""
       You are an intelligent news analysis agent with the following mission:
       PURPOSE: {agent_purpose}
       KEYWORDS OF INTEREST: {', '.join(keywords)}

       Please analyze this news article and provide a structured assessment:

       ARTICLE DETAILS:
       Title: {title}
       Source: {source}
       Description: {description}
       Content: {content}

       ANALYSIS REQUIRED:
       1. Relevance: Is this article relevant to the agent's purpose and keywords?
       2. Confidence: How confident are you in this assessment? (0-100)
       3. Reasoning: Why is this article relevant or not relevant?
       4. Key Points: What are the 3 most important points in this article?
       5. Sentiment: Is the overall tone positive, negative, or neutral?
       6. Urgency: How urgent/important is this news? (high/medium/low)
       7. Action: What should the agent do? (save_important/notify_user/ignore)

       RESPONSE FORMAT (JSON):
       {{
           "is_relevant": boolean,
           "confidence_score": number (0-1),
           "reasoning": "detailed explanation",
           "key_points": ["point1", "point2", "point3"],
           "sentiment": "positive|negative|neutral",
           "urgency": "high|medium|low",
           "suggested_action": "save_important|notify_user|ignore"
          }}

          Respond only with valid JSON.
          """
        # return prompt
        return prompt

    async def _call_llm_api(self, prompt:str)-> Dict[str,Any]:
        if not self.session:
            raise RuntimeError("LLMSerivce should use async context manager")

        #gemini format -> req data

        request_data = {
            "contents":[{
                "parts":[{
                    "text":prompt
                }]
            }],
            "generationConfig":{
                "maxOutputTokens": self.max_tokens_per_request,
                "temperature": 0.1,
                "topP": 0.8,
                "topK": 40
            }
        }



        # build api url -> api_url, params
        api_url = f"{self.base_url}/models/{self.model_name}:generateContent"
        params = {"key": self.api_key or ""}

        # post req inside try -> codes,

        try:
            async with self.session.post(api_url, json=request_data, params=params) as response:
                if response.status == 200:

                    data = await response.json()
                    return data
                elif response.status == 429: #rate limit -> sleep -> retry
                    print("llm rate limit excedeed")
                    await asyncio.sleep(60)
                    return await self._call_llm_api(prompt)
                elif response.status == 401:
                    error_data = response.json()
                    print("invalid api key", error_data)
                    raise Exception(f"invlid api key {error_data}")

                else:
                    raise Exception(f"llm api response, {response.status}")

        except aiohttp.ClientError as e:
            raise Exception(f"network error, {e}")

    def _parse_llm_response(self, llm_response:Dict[str,Any])-> Dict[str,Any]:
        # try-> extract the content from LLMService -> candidates, content, parts {check}

        try:
            candidates = llm_response.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in llm response")

            content =  candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise ValueError("No parts in llm repsonse")


            # get acutal text-> which is inside parts
            response_text = parts[0].get("text", "")

            # parse json from repsonse
            analysis_data = json.loads(response_text)

            # validate required fields
            required_fields = ["is_relevant", "confidence_score", "reasoning", "suggested_action"]
            for field in required_fields:
                if field not in analysis_data:
                    raise ValueError(f"Missing required field: {field}")


            # normalized confidence score
            confidence = analysis_data["confidence_score"]
            if confidence > 1:
                confidence = confidence / 100
            analysis_data["confidence_score"] = max(0,min(1,confidence))


            # validate action values
            valid_actions = ["save_important", "notify_user", "ignore"]
            if analysis_data["suggested_action"] not in valid_actions:
                analysis_data["suggested_action"] = "ignore" #safe default
            return analysis_data

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"failed to parse, {e}")
            return {
                "is_relevant": False,
                           "confidence_score": 0.0,
                           "reasoning": "Failed to analyze article",
                           "key_points": [],
                           "sentiment": "neutral",
                           "urgency": "low",
                           "suggested_action": "ignore"
            }

        # return safe default repsonse
    def _fallback_keyword_analysis(
        self,
        article:Dict[str, Any],
        keywords: List[str]
    ) -> Dict[str,Any]:

        title = (article.get("title") or "").lower()
        description=(article.get("description")or "").lower()

        #count keyword matches
        matched_keywords =[]
        for keyword in keywords:
            if keyword.lower() in title or keyword.lower() in description:
                matched_keywords.append(keyword)

        #calc
        relevance_score = len(matched_keywords) / len(keywords) if keywords else 0
        is_relevant = relevance_score > 0.3

        return {
                "is_relevant": is_relevant,
                "confidence_score": min(relevance_score, 0.8),  # Cap at 80% for keyword analysis
                "reasoning": f"Keyword analysis found {len(matched_keywords)} matches: {', '.join(matched_keywords)}",
                "key_points": matched_keywords,
                "sentiment": "neutral",  # Can't determine without LLM
                "urgency": "medium" if is_relevant else "low",
                "suggested_action": "save_important" if is_relevant else "ignore"
            }

    def _update_token_usage_(self, usuage_data:Dict[str,Any])-> None:

        input_tokens = usuage_data.get("promptTokenCount",0)
        output_tokens = usuage_data.get("candidatesTokenCount",0)
        total_tokens = input_tokens  + output_tokens

        self.daily_token_usage += total_tokens

        print(f"DAILY USUAGE input = {input_tokens} output = {output_tokens} total tokens ={total_tokens}")

            # Warn if approaching limits
        if self.daily_token_usage > self.daily_token_limit * 0.8:
                print("⚠️ WARNING: Approaching daily token limit!")

        if self.daily_token_usage >= self.daily_token_limit:
                print("🚫 Daily token limit reached! Switching to fallback mode.")
