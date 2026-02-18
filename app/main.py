from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, ValidationError
from app.config import APP_NAME, APP_VERSION, APP_HOST, APP_PORT, HEALTH_CHECK_INTERVAL, MAX_FAILURES, CORS_ORIGINS
from app.logger import logger
import uvicorn
import asyncio
import httpx

# In-memory store: {agent_url: agent_card_dict}
agent_store: dict[str, dict] = {}

# Consecutive failure counter per agent
agent_failures: dict[str, int] = {}

# Lock to prevent race conditions on shared store
_store_lock = asyncio.Lock()


# Pydantic models
class RegisterRequest(BaseModel):
    url: HttpUrl

class AgentSkill(BaseModel):
    name: str
    description: str = ""
    tags: list[str] = []

class AgentCard(BaseModel):
    name: str
    description: str = ""
    skills: list[AgentSkill] = []


# Periodically check if registered agents are still reachable
# Deregisters agents after MAX_FAILURES consecutive failed checks
async def _healthcheck_loop():
    while True:
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)

        async with _store_lock:
            agent_urls = list(agent_store.keys())

        if not agent_urls:
            continue

        async with httpx.AsyncClient() as client:
            for url in agent_urls:
                try:
                    resp = await client.get(f"{url}/.well-known/agent-card.json", timeout=5.0)
                    resp.raise_for_status()

                    # Agent is alive: reset failure counter
                    async with _store_lock:
                        agent_failures[url] = 0

                except Exception:
                    async with _store_lock:
                        agent_failures[url] = agent_failures.get(url, 0) + 1
                        if agent_failures[url] >= MAX_FAILURES:
                            name = agent_store.get(url, {}).get("name", url)
                            agent_store.pop(url, None)
                            agent_failures.pop(url, None)

                            logger.info(f"Agent '{name}' at {url} deregistered (unreachable after {MAX_FAILURES} checks)")
                        else:
                            logger.info(f"Agent {url} healthcheck failed ({agent_failures[url]}/{MAX_FAILURES})")


# App lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_healthcheck_loop())
    logger.debug(f"Healthcheck started (interval={HEALTH_CHECK_INTERVAL}s, max_failures={MAX_FAILURES})")
    print_banner()
    yield
    task.cancel()


# App init
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Registry health status
@app.get("/")
async def health():
    async with _store_lock:
        count = len(agent_store)
    return {
        "status": "ok",
        "agents": count,
        "check_interval": HEALTH_CHECK_INTERVAL,
    }


# Register an agent by fetching its Agent Card from the well-known endpoint
@app.post("/register", responses={
    502: {"description": "Failed to fetch agent card from the agent's well-known endpoint"},
    422: {"description": "Invalid URL or agent card structure"},
})
async def register_agent(request: RegisterRequest):
    agent_url = str(request.url).rstrip("/")
    card_url = f"{agent_url}/.well-known/agent-card.json"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(card_url, timeout=10.0)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch agent card from {card_url}: {e}")

    # Validate agent card structure
    try:
        agent_card = AgentCard(**response.json())
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Invalid agent card: {e.errors()}")

    card_dict = agent_card.model_dump()

    async with _store_lock:
        agent_store[agent_url] = card_dict
        agent_failures[agent_url] = 0

    logger.info(f"Agent '{agent_card.name}' registered at {agent_url}")

    return {
        "status": "registered",
        "agent": agent_card.name
    }


# Discover agents by skill tag. Searches skill names, descriptions, and tags
@app.get("/discover")
async def discover_agents(skill: Annotated[str, Query(description="Skill tag to search for")]):
    skill_lower = skill.lower()
    results = []

    async with _store_lock:
        store_snapshot = dict(agent_store)

    for url, card in store_snapshot.items():
        for s in card.get("skills", []):
            tags = [t.lower() for t in s.get("tags", [])]
            name = s.get("name", "").lower()
            description = s.get("description", "").lower()

            if skill_lower in tags or skill_lower in name or skill_lower in description:
                results.append({"url": url, "card": card})
                break

    return results


# List all registered agents
@app.get("/agents")
async def list_agents():
    async with _store_lock:
        return [
            {"url": url, "card": card}
            for url, card in agent_store.items()
        ]


# Remove an agent from the registry
@app.delete("/unregister", responses={404: {"description": "Agent not found in registry"}})
async def unregister_agent(url: Annotated[str, Query(description="Agent URL to remove")]):
    agent_url = url.rstrip("/")

    async with _store_lock:
        if agent_url not in agent_store:
            raise HTTPException(status_code=404, detail="Agent not found")

        del agent_store[agent_url]
        agent_failures.pop(agent_url, None)

    return {
        "status": "unregistered",
        "url": agent_url
    }


# Banner
def print_banner():
    logger.info("####################################################################")
    logger.info("#            ___                            _     _                #")
    logger.info("#      /\\   |__ \\    /\\                    (_)   | |               #")
    logger.info("#     /  \\     ) |  /  \\     _ __ ___  __ _ _ ___| |_ _ __ _   _   #")
    logger.info("#    / /\\ \\   / /  / /\\ \\   | '__/ _ \\/ _` | / __| __| '__| | | |  #")
    logger.info("#   / ____ \\ / /_ / ____ \\  | | |  __/ (_| | \\__ \\ |_| |  | |_| |  #")
    logger.info("#  /_/    \\_\\____/_/    \\_\\ |_|  \\___|\\__, |_|___/\\__|_|   \\__, |  #")
    logger.info("#                                      __/ |                __/ |  #")
    logger.info("#                                     |___/                |___/   #")
    logger.info("#                                                                  #")
    logger.info("#              alessandro.orru <at> aleostudio.com                 #")
    logger.info("#                                                                  #")
    logger.info("####################################################################")


# App launch if invoked directly
if __name__ == "__main__":
    uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, log_level="warning")
