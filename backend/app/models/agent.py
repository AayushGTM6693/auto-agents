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
    news_source = Column( String(200), nullable=True) #optional
    check_interval = Column(Integer, default=300)
    is_active = Column(Boolean, index=True, nullable=False)
    #timestamp
    created_at = Column( DateTime(timezone=True), server_default = func.now() )
    updated_at = Column(DateTime(timezone=True), onUpdate= func.now())
    last_checked = Column(DateTime(timezone=True), nullable=True)


    #relationship
    articles = relationship("article", back_populates="agent", cascade="all delete_orphan")
    #one agent -> multi article and backpopl->  Article model must have agent = relationship(...) too.
    llm_analyses = relationship("LLMAnalysis", back_populates="agent")
    #one agent -> multi llm anaysis

    def __repr__(self):
        return f"--AgentId ={self.id} name={self.name} active = {self.is_active}"
