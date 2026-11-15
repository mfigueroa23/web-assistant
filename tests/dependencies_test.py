import re
import tomllib
from pathlib import Path

# Spec 015, RF-15: las dependencias que solo usaban Google Chat (token) y la lectura de adjuntos no se declaran.
PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
RETIRADAS = {"google-auth", "openpyxl", "python-docx", "python-pptx"}


def test_rf15_pyproject_no_declara_las_dependencias_de_los_canales():
    project = tomllib.loads(PYPROJECT.read_text())
    declared = [*project["project"]["dependencies"], *project["dependency-groups"]["dev"]]
    names = {re.split(r"[\[<>=~! ]", requirement, maxsplit = 1)[0].lower() for requirement in declared}

    assert RETIRADAS.isdisjoint(names)
