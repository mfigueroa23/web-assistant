from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
import main
from main import app
from src.agents.coordinator import TOOLS, coordinator_builder
from src.database.session import get_session
from src.routers import chat as chat_router
from src.utils.exceptions.agents import AgentNotFoundError
from src.utils.exceptions.database import DatabaseUnavailableError

NO_DISPONIBLE = {"respuesta": "Servicio no disponible. Intente de nuevo más tarde"}


@pytest.fixture
def fake_session(monkeypatch):
    async def session():
        yield None

    monkeypatch.setitem(app.dependency_overrides, get_session, session)
    monkeypatch.setattr(app.state, "graph", object(), raising = False)


def test_chat_rechaza_un_chat_id_que_no_es_uuid():
    response = TestClient(app).post("/chat", json={"chat_id": "otro-chat", "mensaje": "Hola"})

    assert response.status_code == 422


def test_rf01_chat_pregunta_al_agente_externo_en_el_hilo_del_chat(monkeypatch, fake_session):
    calls: list[tuple[str, str, str]] = []

    async def fake_ask(graph, session, coordinator, thread_id, mensaje):
        calls.append((coordinator, thread_id, mensaje))
        return "Hola"

    monkeypatch.setattr(chat_router, "ask", fake_ask)
    chat_id = str(uuid4())

    response = TestClient(app).post("/chat", json={"chat_id": chat_id, "mensaje": "Hola"})

    assert response.status_code == 200
    assert response.json() == {"respuesta": "Hola"}
    assert calls == [("Agente Externo", chat_id, "Hola")]


@pytest.mark.parametrize(("error", "status"), [
    (AgentNotFoundError("Agente Externo"), 500),
    (DatabaseUnavailableError("10.0.0.5 rechazó la conexión"), 503),
    (RuntimeError("detalle interno"), 500),
])
def test_rf04_errores_del_chat_responden_en_espanol_sin_detalles(monkeypatch, fake_session, error, status):
    async def fake_ask(graph, session, coordinator, thread_id, mensaje):
        raise error

    monkeypatch.setattr(chat_router, "ask", fake_ask)

    response = TestClient(app).post("/chat", json={"chat_id": str(uuid4()), "mensaje": "Hola"})

    assert response.status_code == status
    assert response.json() == NO_DISPONIBLE


@pytest.mark.parametrize("path", ["/api/v1/google-chat/events", "/api/v1/whatsapp/events"])
def test_rf05_rf06_los_canales_retirados_responden_404(path):
    response = TestClient(app).post(path, json={})

    assert response.status_code == 404


def test_rf07_el_coordinador_solo_delega_en_las_areas():
    assert [tool.name for tool in TOOLS] == ["delegar_area"]
    tools_node = coordinator_builder.nodes["tools"].runnable
    assert list(getattr(tools_node, "tools_by_name")) == ["delegar_area"]


def test_rf08_la_app_arranca_y_se_apaga_con_un_solo_grafo(monkeypatch):
    events: list[str] = []

    class FakePool:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            events.append("pool abierto")
            return self

        async def __aexit__(self, *args):
            events.append("pool cerrado")

    class FakeSaver(InMemorySaver):
        def __init__(self, pool):
            super().__init__()

        async def setup(self):
            events.append("checkpointer listo")

    class FakeEngine:
        async def dispose(self):
            events.append("engine cerrado")

    monkeypatch.setattr(main, "AsyncConnectionPool", FakePool)
    monkeypatch.setattr(main, "AsyncPostgresSaver", FakeSaver)
    monkeypatch.setattr(main, "engine", FakeEngine())
    monkeypatch.delattr(app.state, "graph", raising = False)

    with TestClient(app):
        assert hasattr(app.state, "graph")
        assert not hasattr(app.state, "whatsapp_graph")

    assert events == ["pool abierto", "checkpointer listo", "pool cerrado", "engine cerrado"]
