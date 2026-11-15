from typing import cast
from sqlalchemy import Table
from src.models import agents, cors_origins, faq_categories, faqs, property  # noqa: F401  (registran sus tablas)
from src.models.areas import Area
from src.models.base import Base

RETIRADAS = {"whatsapp_conversations", "whatsapp_messages", "whatsapp_notices", "whatsapp_events", "knowledge_proposals"}


def test_rf10_areas_no_tiene_audiencia():
    table = cast(Table, Area.__table__)

    assert "audiencia" not in table.columns
    assert all(constraint.name != "ck_areas_audiencia" for constraint in table.constraints)


def test_rf09_los_modelos_no_declaran_las_tablas_retiradas():
    assert RETIRADAS.isdisjoint(Base.metadata.tables)
    assert {"areas", "agents", "faq_categories", "faqs", "property", "cors_origins"} <= set(Base.metadata.tables)
