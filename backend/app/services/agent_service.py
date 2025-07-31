
import asyncio
from datetime import datetime, timezone
from typing import  Dict , Optional,Any
from sqlalchemy.orm import Session
from ..models.agent import Agent
from ..models.article import Article
from ..models.llm_analysis import LLMAnalysis
from  ..services.llm_service import LLMService
from ..services.news_service import NewsService




class AgentService:
    """
       Agent Service - The Intelligent News Monitoring Orchestrator

       This service mirrors your existing Cardano AgentService but for news intelligence:

       Your Cardano Agent:                    Our News Agent:
       - Monitors blockchain events    →      - Monitors news sources
       - Triggers on transactions     →      - Triggers on relevant articles
       - Executes governance actions  →      - Executes intelligent actions
       - Uses probabilistic triggers  →      - Uses LLM-based triggers

       Key Responsibilities:
       1. Agent lifecycle management (create, update, delete)
       2. News monitoring coordination
       3. LLM analysis orchestration
       4. Intelligent action triggering
       5. Database state management
       """

    def __init__(self, db:Session):
        self.db = db
        #external serivces
        self.news_service = None
        self.llm_service = None

        #agent ko execution state
        self.running_agents:Dict[int, bool]= {}
        self.agent_tasks:Dict[int,asyncio.Task] ={}


    async def create_agent(self,agent_data:Dict[str,Any])->Agent:
        """
          Create intelligent news monitoring agent

          Similar to your create_agent() but sets up news monitoring instead of blockchain governance

          Your flow: Agent → Wallet → Template Triggers → Kafka notification
          Our flow:  Agent → Keywords → LLM Config → News Monitoring → Intelligent Actions
          """
        #create agent record
        agent = Agent(
            name = agent_data['name'],
            keywords = agent_data['keywords'],
            news_source=agent_data.get("news_source"),
            check_interval = agent_data.get("check_interval", 300),
            llm_enabled = agent_data.get("llm_enabled", True),
            min_confidence  = agent_data.get("min_confidence", 0.7),
            user_id = agent_data.get("user_id"),


        )

        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)

        #start agent immediately
        if bool(agent.is_active):
            await self.start_agent_monitoring(int(agent.id))  # type: ignore[arg-type]

        return agent

    async def start_agent_monitoring(self,agent_id:int):
        #check if its already running

        if agent_id in self.running_agents or self.running_agents[agent_id]:
            print(f"falano agent is running , {agent_id}")

            self.running_agents[agent_id] = True

        #creating background tasks

        tasks  = asyncio.create_task(self.agent_monitoring_loop(agent_id))

        self.agent_tasks[agent_id] = tasks
        print(f"started monitoring for the agent {agent_id}")

    async def agent_monitoring_loop(self,agent_id:int):
        while self.running_agents.get(agent_id, False):
            try:
                #get agent config

                agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent:
                    print(f"No agent found for ID {agent_id}")
                    return  # or handle appropriately
                #start one cycle

                await self.execute_monitoring_cycle(agent)

                #wait before next check

                await asyncio.sleep(int(agent.check_interval)) # type: ignore[arg-type]
            except Exception as e:
                print(f"exception occured , {e}")
                await asyncio.sleep(60)

            #cleanup
        if agent_id in self.running_agents:
         del self.running_agents[agent_id]
        if agent_id  in self.agent_tasks:
         del self.agent_tasks[agent_id]

    async def execute_monitoring_cycle(self, agent:Agent):
        #Check news → LLM analysis → Intelligent action


            print(f"🔍 Executing monitoring cycle for agent: {agent.name}")


            async with NewsService() as news_service:
                keywords = [k.strip() for k in agent.keywords.split(",")]

                articles = await news_service.fetch_everything_news(keywords = " OR ".join(keywords),sources = agent.news_source, page_size=20)

                quality_articles = news_service.filter_quality_articles(articles)

                recent_articles = [
                    article for article in quality_articles
                    if news_service.is_article_recent(article, max_age_hours = 24)

                ]

                print(f"we found this , recent articles  = {len(recent_articles)}")

                #2 -> process the article with intelligence

                for article in recent_articles:
                    if self.is_article_already_processed(article['url']):
                     continue

                    analysis_result  = await self.analyze_article_with_intelligence(agent,article)

                    if analysis_result["should_take_action"]:
                        await self.execute_intelligent_action(agent,article,analysis_result)


    async def analyze_article_with_intelligence(self, agent: Agent, article:Dict[str, Any]) -> Dict[str,Any]:

       """
    Apply intelligent analysis to determine if action should be taken

    THIS IS THE CORE DIFFERENCE FROM YOUR PROBABILISTIC SYSTEM:

    Old way (probabilistic):
    if random() < 0.8:  # 80% chance
        take_action()

    New way (intelligent):
    analysis = llm.analyze(article)
    if analysis.confidence > 0.8 and analysis.suggests_action:
        take_action(analysis.reasoning)
       """


       keywords  = [k.strip() for k in agent.keywords.split(",")]

       if agent.llm_enabled:
            try:
                async with LLMService() as llm_service:
                  llm_analysis = await llm_service.analyze_article_relevance(article = article, agent_keywords = keywords, agent_purpose= f"Monitor {agent.name} topics")

               #save the analysis
                  await self.save_llm_analysis(agent.id, article, llm_analysis) #type:ignore

               #make analysis now

                  should_act = (
                    llm_analysis['is_relevant'] and llm_analysis['confidence_score'] >=agent.min_confidence
                      )

                  return {
                   "should_take_action":should_act,
                   "method":"llm_analysis",
                   "confidence": llm_analysis["confidence_score"],
                   "reasoning": llm_analysis['reasoning'],
                   "suggested_action": llm_analysis["suggested_action"],
                   "analysis_data": llm_analysis

                     }
            except Exception as e:
                print(f"the analysis is failed {agent.id}:{e}")

                #fallback -> keyword analysis



       async with NewsService() as news_service:

        keyword_analysis = news_service.analyze_keywords_match(article,keywords)

        should_act = keyword_analysis["matched_score"] > 0.5

        return {

            "should_take_action":should_act,
            "method":"fall_back analysis",
            "confidence": keyword_analysis["matched_score"],
            "reasoning":f"Keyword analysis: {keyword_analysis['total_matches']} matches",
            "suggested_action": "save_important" if should_act else "ignore",
            "analysis_data": keyword_analysis

        }


    async def  execute_intelligent_action(self, agent:Agent, article:Dict[str,Any], analysis:Dict[str,Any]):

        #save useful article to database first
        article_record  = await self.save_article(agent,article,analysis)



        #execute some action
        action = analysis.get("suggested_action, save_important")
        if action== "notify_user":
             self.notify_user_urgent_news(agent, article_record,analysis)
        elif action == "track_trend":
             self.track_developing_story(agent, article_record, analysis)
        elif action == "save_important":
             self.mark_as_important(article_record,analysis)


        print(f"executed action {action} for a article {article["title"][:50]}..")
        print(f"resoning : {analysis["reasoning"][:100]}..")


    async def save_article(self, agent:Agent, article:Dict[str,Any], analysis:Dict[str,Any])-> Article:

        article_record = Article(
                agent_id=agent.id,
                title=article.get("title"),
                description=article.get("description"),
                content=article.get("content"),
                url=article.get("url"),
                source=article.get("source", {}).get("name"),
                author=article.get("author"),
                published_at=self.parse_published_date(str(article.get("published_at"))),
                keywords_matched=",".join(analysis.get("analysis_data", {}).get("matched_keywords", [])),
                relevance_score=int(analysis.get("confidence", 0) * 100),  # Convert to 0-100 scale
                analysis_method=analysis.get("method", "unknown")
            )

        self.db.add(article_record)
        self.db.commit()
        self.db.refresh(article_record)

        return article_record

    async def save_llm_analysis(self,agent_id:int,article, llm_result:Dict[str,Any]):
        llm_analysis = LLMAnalysis(
                agent_id=agent_id,
                article_id="no article",
                summary=llm_result.get("reasoning"),
                sentiment=llm_result.get("sentiment"),
                confidence_score=llm_result.get("confidence_score"),
                key_entities=llm_result.get("entities", []),
                topics=llm_result.get("key_points", []),
                suggested_action=llm_result.get("suggested_action"),
                action_reasoning=llm_result.get("action_reasoning"),
                model_used="gemini-1.5-flash",  # Track which model was used
                processing_time=None  # Could track this for performance monitoring
            )

        self.db.add(llm_analysis)
        self.db.commit()


#Agent Management Functions
    async def update_agent(self, agent_id:int,update_data:Dict[str,Any])->Agent:
        agent = self.db.query(Agent).filter(Agent.id== agent_id).first()

        if not agent:
            raise ValueError(f"agent does not exist with this id: {agent_id} ")

        #update the agent

        for key,value in update_data.items():
            if hasattr (agent,key):
                setattr(agent,key,value)


        agent.updated_at  = datetime.now(timezone.utc) #type: ignore
        self.db.commit()

        if agent.is_active: #type: ignore
            await self.stop_agent_monitoring(agent_id)
            await self.start_agent_monitoring(agent_id)

        return agent


    async def stop_agent_monitoring(self,agent_id:int):

        self.running_agents[agent_id] = False

        if agent_id in self.agent_tasks:
            tasks = self.agent_tasks[agent_id]
            tasks.cancel()

            try:
                await tasks

            except asyncio.CancelledError:
                pass

            del self.agent_tasks[agent_id]

    async  def get_agent_status(self, agent_id:int)-> Dict[str,Any]:


        #query agent from db
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()

        if not agent:
            ValueError(f"agent does not exist, {agent_id}")

        #count the article from last 24 hour


        from datetime import timedelta

        last24h = datetime.now(timezone.utc) - timedelta(hours=24)

        #get recent article


        recent_articles_count = self.db.query(Article).filter(Article.agent_id==agent_id, Article.created_at >=last24h).count()

        latest_llm_analysis  =  self.db.query(LLMAnalysis).filter(LLMAnalysis.agent_id == agent_id).order_by(LLMAnalysis.created_at.desc()).first()

        return {
            "agent": agent,
                    "is_monitoring": self.running_agents.get(agent_id, False),
                    "articles_last_24h": recent_articles_count,
                    "last_check": agent.last_checked, #type:ignore
                    "latest_analysis": {
                        "confidence": latest_llm_analysis.confidence_score if latest_llm_analysis else None,
                        "sentiment": latest_llm_analysis.sentiment if latest_llm_analysis else None,
                        "created_at": latest_llm_analysis.created_at if latest_llm_analysis else None
                    } if latest_llm_analysis else None
        }



#Helper function
    async def is_article_already_processed(self, url:str)-> bool:
        existing_article = self.db.query(Article).filter(Article.url == url).first()

        return existing_article is not None



    def parse_published_date(self,date_str:str)-> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z","+00:00"))
        except (ValueError,AttributeError):
            return None

    def notify_user_urgent_news(self, agent:Agent, article:Article, analysis:Dict):
        print(f"urgent news for {agent.name}:{article.title}") #TODO

    def track_developing_story(self,agent:Agent, article:Article, analysis:Dict):
        print(f"tracking trend for {agent.name}:{article.title}")


    def mark_as_important(self,  article:Article, analysis:Dict):
        article.relevance_score = min(article.relevance_score + 20, 100)
        self.db.commit()
        print(f"marked as important {article.title}")
