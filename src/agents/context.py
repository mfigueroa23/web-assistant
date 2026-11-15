from dataclasses import dataclass
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from src.services.agents import SubAgentConfig

@dataclass
class AgentContext:
  llm: ChatGoogleGenerativeAI
  system_prompt: str
  embeddings: GoogleGenerativeAIEmbeddings
  area: str

@dataclass
class CoordinatorContext:
  llm: ChatGoogleGenerativeAI
  system_prompt: str
  embeddings: GoogleGenerativeAIEmbeddings
  sub_agents: dict[str, SubAgentConfig]
