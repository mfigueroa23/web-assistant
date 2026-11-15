# web-assistant

Backend de asistente virtual, construido con FastAPI, SQLAlchemy (async), LangGraph, Gemini y PostgreSQL.

## Arquitectura

- El chat web (`/chat`) lo atiende el coordinador `Agente Externo`, que delega cada consulta en el sub-agente del área que corresponde (un sub-agente por área).
- Cada sub-agente busca en las preguntas frecuentes de su propia área con similitud coseno (pgvector) antes de responder.
- Los prompts, áreas y sub-agentes se configuran en la base de datos (ver [Administrar el conocimiento](#administrar-el-conocimiento)). El historial de cada conversación se guarda en PostgreSQL con el checkpointer de LangGraph.

## Requisitos

- Python 3.15, fijado en `.python-version` (uv lo usa automáticamente y lo descarga si no está instalado)
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL

> `pyyaml`, `zstandard` y `websockets` todavía no publican wheels para Python 3.15, así que `uv sync` las compila desde el código fuente y necesita un compilador de C (en macOS, las Xcode Command Line Tools: `xcode-select --install`; en Linux, `build-essential` o `build-base`). `pyyaml` queda sin libyaml, en su implementación pura.

## Configuración

La configuración se divide en dos lugares:

| Dónde | Qué contiene |
|---|---|
| `.env` | Solo la conexión a la base de datos (`DB_*`) y `LOG_LEVEL` |
| Tabla `property` | Todo el resto de la configuración de la aplicación (pares `key` / `value`) |

Crea el `.env` a partir del ejemplo y completa los valores:

```bash
cp .env.example .env
```

| Variable | Descripción | Por defecto |
|---|---|---|
| `DB_HOST` | Host de PostgreSQL | — |
| `DB_PORT` | Puerto de PostgreSQL | — |
| `DB_USER` | Usuario | — |
| `DB_PASSWORD` | Contraseña | — |
| `DB_NAME` | Nombre de la base de datos | — |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL` (en mayúsculas) | `INFO` |

Las properties se leen de la base de datos en cada petición (sin caché), así que un cambio en la tabla se aplica desde la siguiente petición sin reiniciar la aplicación.

Properties usadas actualmente:

| Key | Uso |
|---|---|
| `service_name` | Nombre del servicio que devuelve `/health` |
| `google_api_key` | API key de Gemini |
| `google_model` | Modelo de chat de Gemini |
| `google_embedding_model` | Modelo de embeddings de las preguntas frecuentes |
| `top_k` | Cantidad máxima de preguntas frecuentes que recibe el sub-agente en cada búsqueda |
| `max_distance` | Distancia coseno máxima para que una pregunta frecuente cuente como relacionada |

> Los valores de la tabla `property` se guardan en texto plano. Revisa [SECURITY.md](SECURITY.md) antes de guardar secretos.

## Instalación

```bash
uv sync
uv run alembic upgrade head
```

Si `uv sync` falla compilando alguna dependencia, revisa que el entorno virtual use Python 3.15 (`uv run python --version`) y que tengas un compilador de C. Si se creó con otra versión (por ejemplo, después de que Homebrew actualizara `python3`), recréalo:

```bash
rm -rf .venv
uv sync
```

## Ejecución

```bash
uv run fastapi dev   # desarrollo, con recarga automática
uv run fastapi run   # producción
```

Documentación interactiva de la API: <http://127.0.0.1:8000/docs>

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Liveness: responde `true` si el proceso está vivo, sin consultar la base de datos |
| `GET` | `/health` | Verifica la base de datos. `200` si está disponible, `503` si no |
| `POST` | `/chat` | Chat web con el coordinador `Agente Externo`. Recibe `chat_id` (UUID generado por el cliente) y `mensaje` |

## Base de datos

| Tabla | Qué contiene |
|---|---|
| `property` | Configuración de la aplicación (`key` / `value`) |
| `agents` | Prompts de los agentes. Con `area_id` vacío es un coordinador, con `area_id` es el sub-agente de esa área |
| `areas` | Áreas del conocimiento con su descripción, que el coordinador usa para elegir a qué sub-agente delegar. El nombre es único |
| `faq_categories` | Categorías de preguntas frecuentes de cada área |
| `faqs` | Preguntas frecuentes con su embedding. `status` es `re-index` si falta generar el embedding e `index` si ya está indexada |
| `cors_origins` | Orígenes que pueden consumir la API desde el navegador (CORS). `enabled` es `true` por defecto |

### Orígenes CORS

La API solo emite cabeceras CORS a los orígenes registrados y habilitados en `cors_origins`. La tabla se consulta en cada petición que trae la cabecera `Origin` (sin caché), así que un cambio aplica desde la siguiente petición sin reiniciar la aplicación. Las peticiones sin `Origin` (por ejemplo, las probes de Kubernetes) no la consultan.

El origen se compara de forma exacta con el que envía el navegador: `esquema://host[:puerto]`, en minúsculas, sin barra final ni ruta y sin el puerto por defecto (`https://app.ejemplo.com`, `http://localhost:5173`). No se admiten comodines ni subdominios: cada origen va en su propia fila, y para deshabilitar un origen sin borrarlo se pone `enabled = false`.

Un origen no permitido recibe la respuesta sin cabeceras CORS (el navegador la bloquea) y su preflight se responde con `400`. Si la base de datos falla al consultar, el origen se trata como no permitido. No se envían credenciales (`Access-Control-Allow-Credentials`).

> No registres el origen `null`: lo envían iframes con sandbox y archivos locales (`file://`), y habilitarlo abriría la API a cualquiera de ellos.

Las tablas del checkpointer las crea LangGraph al arrancar la aplicación y no se versionan con alembic.

### Administrar el conocimiento

Las áreas, sus sub-agentes y sus preguntas frecuentes se administran directamente en la base de datos. El coordinador lee las áreas en cada mensaje, así que un área nueva queda disponible sin reiniciar.

```sql
-- Área y su sub-agente
INSERT INTO areas (name, description) VALUES ('Ventas', 'Planes, precios y contratación');
INSERT INTO agents (name, prompt, area_id)
VALUES ('Agente Ventas', '<prompt del sub-agente>', (SELECT id FROM areas WHERE name = 'Ventas'));

-- Categoría y pregunta frecuente
INSERT INTO faq_categories (area_id, name) VALUES ((SELECT id FROM areas WHERE name = 'Ventas'), 'Planes');
INSERT INTO faqs (category_id, question, answer)
VALUES ((SELECT id FROM faq_categories WHERE name = 'Planes'), '¿Qué planes hay?', '<respuesta>');
```

- El prompt del sub-agente debe pedirle que busque siempre con `search_faq` y responda solo con lo que encuentra. El coordinador ve el nombre y la descripción del área, así que la descripción debe decir qué cubre.
- Una pregunta nueva queda con `status = 're-index'` y el sub-agente no la encuentra hasta generar su embedding. Al editar la pregunta o la respuesta, vuelve a poner `status = 're-index'`.
- Borrar un área borra en cascada sus categorías y preguntas, pero antes hay que borrar su sub-agente de `agents`.

Para generar los embeddings de las preguntas frecuentes en estado `re-index`:

```bash
uv run python -m src.rag.reindex
```

## Migraciones

```bash
uv run alembic revision --autogenerate -m "descripción del cambio"
uv run alembic upgrade head
uv run alembic downgrade -1
```

Revisa siempre el archivo generado en `alembic/versions/` antes de aplicarlo.

## Tests

```bash
uv run pytest
```

Los tests nunca se conectan a la base de datos ni a Gemini: reemplazan la sesión con `app.dependency_overrides` o responden antes de consultarla. Igual necesitan las variables `DB_*` (del `.env` o del entorno) porque `Settings` las exige al importar la app.

## CI/CD

| Workflow | Cuándo | Qué hace |
|---|---|---|
| `.github/workflows/testing.yaml` | PR a `main` | `pyright` + `pytest` |
| `.github/workflows/security.yaml` | PR a `main`, diario (08:30 UTC), manual y desde `Release` | SAST (CodeQL y SonarQube Cloud con cobertura), SCA (OSV-Scanner sobre `uv.lock` y Dependency Review en los PR) y análisis de la imagen con Docker Scout. Reporta todo en *Security > Code scanning* y falla solo con hallazgos críticos o altos |
| `.github/workflows/release.yaml` | Push a `main` | Construye la imagen y la despliega (ver abajo) |

El `Release` corre en este orden:

1. **package**: construye cada plataforma en su runner nativo (`amd64` en `ubuntu-24.04` y `arm64` en `ubuntu-24.04-arm`, sin QEMU) y la sube a Docker Hub solo por digest.
2. **merge**: junta ambas en un índice multiplataforma con el tag `sha-<commit>`.
3. **scan**: llama a `security.yaml` para analizar con Docker Scout exactamente ese digest.
4. **promote**: si el análisis pasa, agrega los tags `<versión>` (de `pyproject.toml`) y `latest` sin reconstruir. Si la versión ya está publicada con otro digest, falla: falta subir la versión con `uv version --bump <major|minor|patch>`.
5. **migrate**: aplica `alembic upgrade head` contra la base de datos de producción a través de Twingate. Durante el rollout la versión anterior corre sobre el esquema nuevo, así que las migraciones deben ser compatibles hacia atrás.
6. **deploy**: despliega por digest en Kubernetes (`deployment/web`, contenedor `web`, namespace `virtual-assistant`) y espera el rollout.

Configuración necesaria en GitHub:

| Tipo | Nombre | Uso |
|---|---|---|
| Variable | `DOCKERHUB_USERNAME` | Usuario de Docker Hub |
| Variable | `DOCKERHUB_ORGANIZATION` | Organización de Docker Hub donde se publica la imagen |
| Variable | `DOCKER_IMAGE` | Nombre de la imagen en Docker Hub |
| Secret | `DOCKERHUB_TOKEN` | Token de Docker Hub (también lo usa Docker Scout) |
| Secret | `SONAR_TOKEN` | Token de SonarQube Cloud |
| Secret | `TWINGATE_SERVICE_KEY` | Service key de Twingate para llegar al cluster y a la base de datos |
| Secret | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Conexión a la base de datos de producción para las migraciones |
| Secret (environment `production`) | `KUBE_CONFIG` | kubeconfig del cluster |

Además, en los ajustes del repositorio: el ruleset de `main` con los checks de `Testing` y `Security`, y el environment `production` restringido a `main`.

### Dependencias e imagen

`uv.lock` es la única fuente de las versiones instaladas: la imagen y el CI usan `uv sync --locked` y el repo no versiona un `requirements.txt`.

Las imágenes base van fijadas como `tag@sha256:…`. La API corre sobre `python:3.15-alpine`: la etapa `build` instala `build-base` para compilar `pyyaml`, `zstandard` y `websockets`, y la etapa final no lo hereda, corre con un usuario sin privilegios y levanta la API con `fastapi run` en el puerto `8000`. uv tiene su propia etapa `FROM … AS uv`; al actualizarla, alinea el `version:` de `astral-sh/setup-uv` en los workflows (lo verifica `tests/runtime_test.py`).

La imagen no ejecuta migraciones: las aplica el job `migrate` del `Release` antes del deploy. Si dos ejecuciones coinciden, un advisory lock de PostgreSQL en `alembic/env.py` hace que solo una las aplique a la vez.

## Estructura

```
main.py                     App FastAPI, lifespan y configuración de logs
Dockerfile                  Imagen de la API (Python 3.15 Alpine, multi-etapa)
src/
├── config.py               Settings leídos del .env
├── agents/                 Coordinador, sub-agente, modelo de IA y tools (LangGraph)
├── database/session.py     Engine y sesión por request (SessionDep)
├── models/                 Modelos ORM de SQLAlchemy
├── interfaces/             Modelos Pydantic de request y respuesta
├── middlewares/            Middlewares ASGI (CORS con los orígenes de la base de datos)
├── rag/                    Re-indexación de los embeddings de preguntas frecuentes
├── routers/                Endpoints HTTP
├── services/               Lógica de negocio y acceso a datos
└── utils/exceptions/       Excepciones propias del proyecto
alembic/                    Migraciones de la base de datos
tests/                      Tests con pytest
```

## Autor

Marco Antonio Figueroa Sanchez

## Licencia

Distribuido bajo la licencia Apache 2.0. Ver [LICENSE](LICENSE).
