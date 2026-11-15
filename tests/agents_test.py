from types import SimpleNamespace
from typing import Any, cast
import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.context import AgentContext, CoordinatorContext
from src.agents.tools import delegate
from src.services import faq as faq_service
from src.services.agents import SubAgentConfig, list_sub_agents
from src.services.faq import search_faqs

pytestmark = pytest.mark.anyio


class FakeResult:
    def __init__(self, rows: list[tuple]):
        self.rows = rows

    def all(self) -> list[tuple]:
        return self.rows


class FakeSession:
    def __init__(self, rows: list[tuple]):
        self.rows = rows
        self.statements: list[Any] = []

    async def execute(self, statement):
        self.statements.append(statement)
        return FakeResult(self.rows)


def sql(statement) -> str:
    return str(statement.compile(dialect = postgresql.dialect()))


async def test_rf01_lista_todos_los_sub_agentes_sin_filtrar_por_audiencia():
    session = FakeSession([("Agente Ventas", "prompt", "Ventas", "Planes y precios")])

    sub_agents = await list_sub_agents(cast(AsyncSession, session))

    assert sub_agents == [SubAgentConfig("Agente Ventas", "prompt", "Ventas", "Planes y precios")]
    statement = sql(session.statements[0])
    assert "audiencia" not in statement
    assert "WHERE" not in statement


async def test_rf02_search_faqs_filtra_solo_por_area(monkeypatch):
    properties = {"top_k": "3", "max_distance": "0.4"}

    async def fake_property(session, key):
        return properties[key]

    monkeypatch.setattr(faq_service, "get_property", fake_property)
    session = FakeSession([("Planes", "¿Cuánto cuesta?", "Depende del plan", 0.1)])

    faqs = await search_faqs(cast(AsyncSession, session), [0.0] * 768, area = "Ventas")

    assert [faq.question for faq in faqs] == ["¿Cuánto cuesta?"]
    statement = session.statements[0]
    compiled = sql(statement)
    assert "audiencia" not in compiled
    assert "areas.name = " in compiled
    params = statement.compile(dialect = postgresql.dialect()).params.values()
    assert "Ventas" in params and 0.4 in params and 3 in params


def coordinator_runtime() -> SimpleNamespace:
    sub_agent = SubAgentConfig("Agente Ventas", "prompt de ventas", "Ventas", "Planes y precios")
    context = CoordinatorContext(
        llm = "llm",  # pyright: ignore[reportArgumentType]  (no se invoca)
        system_prompt = "coordinador",
        embeddings = "embeddings",  # pyright: ignore[reportArgumentType]  (no se invoca)
        sub_agents = {"Ventas": sub_agent}
    )
    return SimpleNamespace(context = context)


async def test_rf01_delegar_area_invoca_al_sub_agente_del_area(monkeypatch):
    contexts: list[AgentContext] = []

    class FakeGraph:
        async def ainvoke(self, state, context):
            contexts.append(context)
            return {"messages": [AIMessage("Respuesta de ventas")]}

    monkeypatch.setattr(delegate, "sub_agent_graph", FakeGraph())
    coroutine = cast(StructuredTool, delegate.delegar_area).coroutine
    assert coroutine is not None

    answer = await coroutine("Ventas", "¿Cuánto cuesta?", coordinator_runtime())

    assert answer == "Respuesta de ventas"
    assert contexts == [AgentContext("llm", "prompt de ventas", "embeddings", "Ventas")]  # pyright: ignore[reportArgumentType]  (marcadores en vez de modelos reales)


async def test_rf01_delegar_area_avisa_si_el_area_no_existe(monkeypatch):
    coroutine = cast(StructuredTool, delegate.delegar_area).coroutine
    assert coroutine is not None

    answer = await coroutine("Soporte", "Hola", coordinator_runtime())

    assert answer == "El área 'Soporte' no existe. Áreas disponibles: Ventas."
