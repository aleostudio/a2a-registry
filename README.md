# A2A registry — Agent-to-Agent discovery & coordination service

A2A registry is a central discovery and metadata service for **multi-agent** systems,
providing a single endpoint where agents can dynamically register themselves,
discover other agents by role, capability, or tags, and publish their skills
such as tools, models, and domains.

## Index

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Run A2A registry](#run-a2a-registry)
- [Endpoints](#endpoints)
- [Testing](#testing)
- [Debug in VSCode](#debug-in-vscode)
- [License](#license)

---

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation) and [pip](https://pip.pypa.io/en/stable/installation) installed

[↑ index](#index)

---

## Configuration

Init **virtualenv** and install dependencies with:

```bash
uv venv
source .venv/bin/activate
uv sync
```

If you prefer, there is a `Makefile` that do the job for you (follow the instructions):

```bash
make setup
```

Now create your ```.env``` file by copying:

```bash
cp env.dist .env
```

[↑ index](#index)

---

## Run A2A registry

To run **A2A registry** you can use **uvicorn**:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9300
```

or through the shortcut (with default port):

```bash
make dev
```

[↑ index](#index)

---

## Endpoints

### `GET /` - Health check

Returns the registry status and the number of registered agents.

```bash
curl http://localhost:9300/
```

**Response**: `200 OK`

```json
{
  "status": "ok",
  "agents": 2,
  "check_interval": 30
}
```

---

### `POST /register` - Register an agent

Registers an agent by fetching its Agent Card from `{url}/.well-known/agent-card.json`.

```bash
curl -X POST http://localhost:9300/register \
  -H "Content-Type: application/json" \
  -d '{"url": "https://my-agent.example.com"}'
```

**Request body**:

| Field | Type   | Required | Description           |
|-------|--------|----------|-----------------------|
| `url` | string | yes      | Base URL of the agent |

**Response**:`200 OK`

```json
{
  "status": "registered",
  "agent": "My Agent"
}
```

**Response**: `502 Bad Gateway`

```json
{
  "detail": "Failed to fetch agent card from https://my-agent.example.com/.well-known/agent-card.json: <error>"
}
```

---

### `GET /discover` - Discover agents by skill

Searches registered agents by matching the query against skill `tags`, `name`, and `description` (case-insensitive).

```bash
curl "http://localhost:9300/discover?skill=translation"
```

**Query parameters**:

| Param | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `skill` | string | yes | Skill tag to search for |

**Response**: `200 OK`

```json
[
  {
    "url": "https://my-agent.example.com",
    "card": { "name": "My Agent", "skills": [...] }
  }
]
```

Returns `[]` if no agents match.

---

### `GET /agents` - List all agents

Returns all currently registered agents with their full Agent Card.

```bash
curl http://localhost:9300/agents
```

**Response**: `200 OK`

```json
[
  {
    "url": "https://my-agent.example.com",
    "card": { "name": "My Agent", "skills": [...] }
  }
]
```

Returns `[]` if no agents are registered.

---

### `DELETE /unregister` - Remove an agent

Manually removes an agent from the registry by its URL.

```bash
curl -X DELETE "http://localhost:9300/unregister?url=https://my-agent.example.com"
```

**Query parameters**:

| Param | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `url` | string | yes | Base URL of the agent to remove |

**Response**: `200 OK`

```json
{
  "status": "unregistered",
  "url": "https://my-agent.example.com"
}
```

**Response**: `404 Not Found`

```json
{
  "detail": "Agent not found"
}
```

[↑ index](#index)

---

## Testing

Ensure you have ```pytest``` installed, otherwise:

```bash
uv pip install pytest
```

Then, launch tests with:

```bash
pytest tests/
```

or through shortcut:

```bash
make test
```

[↑ index](#index)

---

## Debug in VSCode

To debug your Python microservice you need to:

- Install **VSCode**
- Ensure you have **Python extension** installed
- Ensure you have selected the **right interpreter with virtualenv** on VSCode
- Click on **Run and Debug** menu and **create a launch.json file**
- From dropdown, select **Python debugger** and **FastAPI**
- Change the ```.vscode/launch.json``` created in the project root with this (customizing host and port if changed):

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "A2A registry debug",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", "9300",
                "--reload"
            ],
            "envFile": "${workspaceFolder}/.env",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "justMyCode": true
        }
    ]
}
```

- Put some breakpoint in the code, then press the **green play button**
- Call the API to debug

[↑ index](#index)

---

## License

This project is licensed under the MIT License.

[↑ index](#index)

---

Made with ♥️ by Alessandro Orrù
