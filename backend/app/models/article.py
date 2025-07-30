from sqlalchemy import Column,String, DateTime,Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.orm.properties import ForeignKey
from sqlalchemy.sql import func
from ..core.database import base

class Article(base):

      """
        Article Model - stores news articles found by agents

        This is like a filing cabinet:
        - Each article is a file
        - agent_id tells us which worker found it
        - All article details stored here
        """

      __tablename__ = "article"
      id = Column(Integer, primary_key=True, index=True)

      #foreign Key -> article.agent_id must match some agent.id in the agents table.
      agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)

      # article content, title,description, content, url.
      title = Column(String(500), nullable=False)
      description = Column(Text, nullable=True)
      content = Column(Text, nullable=True)
      url = Column(String, unique=True, nullable=False)

      # metadata - soruce, author, published at
      source = Column(String(100), nullable=True)
      author = Column(String(200), nullable=True)
      publishedAt = Column(DateTime(timezone = True), nullable=True)

      # Analysis result - keyword matched , relevance score
      keywordMatched = Column(String(200), nullable=True)
      relevanceScore = Column(Integer, default=0)

      # timestamps - created at,
      createdAt = Column(DateTime(timezone = True), server_default = func.now())
      # relationship - agent, llm analysis -> article.agent  # returns the Agent object for this article
      #  relationships reference the model class name, not the table name.
      agents = relationship("Agent", back_populates = "articles" )

      llmAnalyses = relationship("LLMAnalysis", back_populates= 'article')

      def __repr__(self):
          return f"-- Article( id={self.id}, title={self.title[:50]}, agent_id={self.agent_id} )"
          # Each Article belongs to one Agent.

          # Each Article can be linked to many LLMAnalysis records (e.g., multiple AI reviews).
