from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from src.agents.context import AgentContext
from src.agents.nodes import TOOLS, build_assistant

def build_sub_agent() -> CompiledStateGraph[MessagesState, AgentContext]:
  builder = StateGraph(MessagesState, context_schema=AgentContext)
  builder.add_node("assistant", build_assistant(TOOLS))
  builder.add_node("tools", ToolNode(TOOLS))
  builder.add_edge(START, "assistant")
  builder.add_conditional_edges("assistant", tools_condition)
  builder.add_edge("tools", "assistant")
  return builder.compile(checkpointer=False)

sub_agent_graph = build_sub_agent()
