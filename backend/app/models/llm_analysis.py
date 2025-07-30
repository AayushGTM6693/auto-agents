from sqlalchemy import String, Text,Integer, DateTime, JSON, Float, ForeignKey, Column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import base

class LLMAnalysis(base):
    """
        LLM Analysis Model - stores AI analysis of articles

        This is where the magic happens:
        - LLM reads the article
        - Provides intelligent analysis
        - Suggests actions
        """
    __tablenames__ = "llmanalyses"

    id = Column(Integer, primary_key=True, index=True)

    #foreign key, -> here, agent_id and article_id
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("article.id"), nullable=False)

    #results
    summary = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)
    confidenceScore = Column(Float, nullable=True)

    #analysis
    key_entities = Column(JSON, nullable=True)
    topics = Column(JSON, nullable=True)

    #action suggestion
    suggestedAction = Column(String, nullable=True)
    action_reasoning = Column(Text, nullable=True)

    # llm metadata
    modelUsed = Column(String(50), nullable=True)
    promptVersion = Column(String(30), nullable=True)
    processingTime = Column(Float, nullable=True)
    # timestamp
    createdAt = Column(DateTime(timezone = True), server_default= func.now())
    # relationship
    agent = relationship("Agent", back_populates="llm_analyses")
    article = relationship("Article", back_populates = "llm_analyses")

# details
# | Model         | Links to                | Purpose                                           |
# | ------------- | ----------------------- | ------------------------------------------------- |
# | `Agent`       | → Articles, LLMAnalyses | One agent may find articles and analyze them      |
# | `Article`     | ← Agent, → LLMAnalyses  | Articles are found by agents and analyzed by LLMs |
# | `LLMAnalysis` | ← Agent, ← Article      | Stores AI analysis about articles with references |

# flow
# Agent ID 1 reads an article and stores it → Article ID 101.

# Later, the LLM reads Article 101 and stores a new LLMAnalysis record.

# That LLMAnalysis will:

# have article_id = 101

# have agent_id = 1

# return relationships like:

# python
# Copy
# Edit
# analysis.article.title
# analysis.agent.name
