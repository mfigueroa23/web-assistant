from langchain_core.messages import HumanMessage
from langgraph.graph import MessagesState
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.context import CoordinatorContext
from src.agents.llm import LLM
from src.services.agents import get_prompt, list_sub_agents
from src.utils.exceptions.agents import AgentNotFoundError

async def ask(
  graph: CompiledStateGraph[MessagesState, CoordinatorContext],
  session: AsyncSession,
  coordinator: str,
  thread_id: str,
  mensaje: str
) -> str:
  """Ejecuta un turno del coordinador en el hilo indicado y devuelve el texto de su respuesta."""
  llm = await LLM.create(session)
  prompt = await get_prompt(session, coordinator)
  # Se leen en cada turno: un área nueva en la BD queda disponible sin reiniciar.
  sub_agents = await list_sub_agents(session)
  if not sub_agents:
    raise AgentNotFoundError("sub-agentes")
  result = await graph.ainvoke(
    { "messages": [HumanMessage(mensaje)] },
    config = { "configurable": { "thread_id": thread_id } },
    context = CoordinatorContext(
      llm = llm.llm,
      system_prompt = prompt,
      embeddings = llm.embeddings,
      sub_agents = { sub_agent.area: sub_agent for sub_agent in sub_agents }
    )
  )
  return result["messages"][-1].text
