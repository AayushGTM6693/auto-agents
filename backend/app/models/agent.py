from sqlalchemy import Column, Integer, String,DateTime, Boolean,Text
from sqlalchemy.orm import relationship
from ..core.database import base
from sqlalchemy.sql import func

class Agent(base):
    """
       Agent Model - represents a news monitoring worker

       Think of this as an employee record:
       - id: Employee ID
       - name: Employee name
       - keywords: What they specialize in
       - is_active: Are they currently working?
       - created_at: When were they hired?
       """
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    keywords = Column(Text, nullable=False)
    newsSource = Column( String(200), nullable=True) #optional
    checkInterval = Column(Integer, default=300)
    isActive = Column(Boolean, index=True, Optional=True)
    #timestamp
    createdAt = Column( DateTime(timezone=True), server_default = func.now() )
    updatedAt = Column(DateTime(timezone=True), onUpdate= func.now())
    lastChecked = Column(DateTime(timezone=True), nullable=True)

    #relationship
    articles = relationship("article", back_populates="agent", cascade="all delete_orphan")
    #one agent -> multi article and backpopl->  Article model must have agent = relationship(...) too.

    llmAnalyses = relationship("LLMAnalysis", back_populates="agent")
    #one agent -> multi llm anaysis

    def __repr__(self):
        return f"--AgentId ={self.agentid} name={self.name} active = {self.active}"
