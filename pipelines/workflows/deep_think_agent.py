"""
title: Gemma 4 Multi-Agent Deep Think
id: gemma_4_multi_agent
description: 4 e4b agents in parallel + 26b-a4b finalizer with chain-of-thinking.
author: csning1998
version: 2.0
"""

import asyncio
import json
import os
import re
from typing import AsyncGenerator, Generator, Iterator, List, Union

import httpx
import requests
from pydantic import BaseModel, Field


class Pipeline:
    """Open WebUI Pipeline for 4-agent multi-stage reasoning."""

    id: str = "gemma_4_multi_agent"
    name: str = "Gemma 4 Multi-Agent Deep Think"

    class Valves(BaseModel):
        """Configuration options for the pipeline."""

        pipelines: List[str] = Field(
            default=["*"],
            description="Target pipeline IDs for this valve configuration.",
        )
        ollama_url: str = Field(
            default=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
            description="Base URL for the Ollama API.",
        )
        searxng_url: str = Field(
            default=os.getenv("SEARXNG_BASE_URL", "http://searxng:8080"),
            description="Base URL for the SearXNG API.",
        )
        e4b_model: str = Field(
            default="gemma4:e4b",
            description="Model identifier for all e4b agents.",
        )
        a4b_model: str = Field(
            default="gemma4:26b",
            description="Model identifier for finalizer.",
        )

    def __init__(self):
        """Initializes the pipeline with default valves."""
        self.valves = self.Valves()

    async def on_startup(self):
        """Lifecycle event triggered when the pipeline starts."""
        print(f"Pipeline {self.name} started.")

    async def on_shutdown(self):
        """Lifecycle event triggered when the pipeline shuts down."""
        print(f"Pipeline {self.name} shutting down.")

    def _clean_keywords(self, text: str) -> str:
        """Removes markdown code blocks, JSON artifacts, and noise from keywords."""
        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<thought>[\s\S]*?</thought>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<reasoning>[\s\S]*?</reasoning>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```(?:json)?\s*[\s\S]*?```", "", text)
        text = re.sub(r"\{.*\}", "", text)
        text = re.sub(r"[\"\'\[\]\(\)]", "", text)
        words = re.findall(r"\w+", text)
        return " ".join(words[:5]).strip()

    async def _async_call_e4b(self, prompt: str) -> str:
        """Single asynchronous e4b call."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.valves.ollama_url}/api/generate",
                    json={
                        "model": self.valves.e4b_model,
                        "prompt": prompt,
                        "stream": False,
                        "keep_alive": "5m",
                    },
                    timeout=300,
                )
                response.raise_for_status()
                return response.json().get("response", "").strip()
            except httpx.HTTPError as e:
                print(f"E4B Call failed: {e}")
                return "ERROR: Agent timeout."

    async def _researcher_agent(self, user_message: str) -> str:
        """Agent 2: Researcher - generate keywords and fetch + align facts."""
        keywords_prompt = (
            "You must output ONLY 3-5 search keywords for web search. Do NOT use markdown. "
            "DO NOT use any emojis. "
            "If you need to think, put it inside <think>...</think> tags FIRST, then output just the keywords. "
            "Query: " + user_message
        )
        raw_keywords = await self._async_call_e4b(keywords_prompt)
        keywords = self._clean_keywords(raw_keywords)

        if not keywords or "NO_SEARCH" in keywords:
            return "No search results."
        try:
            search_url = f"{self.valves.searxng_url}/search?q={keywords}&format=json"
            async with httpx.AsyncClient() as client:
                response = await client.get(search_url, timeout=60)
                response.raise_for_status()
                results = response.json().get("results", [])[:10]
                facts = "\n".join([f"Source: {r.get('url', '')}\nContent: {r.get('content', '')}" for r in results])
                align_prompt = f"Align the following facts:\n{facts}"
                return await self._async_call_e4b(align_prompt)
        except httpx.HTTPError as e:
            return f"Search failed: {e}"

    async def _logic_agent(self, user_message: str, facts: str) -> str:
        """Agent 3: Logic Verifier - check consistency."""
        prompt = f"Verify logical consistency for query: {user_message}\nFACTS: {facts}\nDO NOT use any emojis."
        return await self._async_call_e4b(prompt)

    async def _contrarian_agent(self, user_message: str, facts: str) -> str:
        """Agent 4: Contrarian - challenge assumptions."""
        prompt = f"List counter-arguments for query: {user_message}\nFACTS: {facts}\nDO NOT use any emojis."
        return await self._async_call_e4b(prompt)

    async def _coordinator_agent(self, user_message: str) -> str:
        """Agent 1: Coordinator - initial task breakdown."""
        prompt = f"Break down the query: {user_message}\nDO NOT use any emojis."
        return await self._async_call_e4b(prompt)

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """Main pipeline: 4 e4b agents parallel + 26b finalizer with UI thinking blocks."""

        __event_emitter__ = body.get("__event_emitter__")

        def stream_response():
            yield "<thought>\n"
            yield "#### Agents Initializing...\n"

            # Stage 1: Run Coordinator and Researcher in parallel
            async def run_stage_1():
                if __event_emitter__:
                    await __event_emitter__({"type": "status", "data": {"description": "Stage 1: Coordinator and Research starting", "done": False}})
                coordinator_task = asyncio.create_task(self._coordinator_agent(user_message))
                researcher_task = asyncio.create_task(self._researcher_agent(user_message))
                return await asyncio.gather(coordinator_task, researcher_task)

            coordinator_output, researcher_facts = asyncio.run(run_stage_1())
            yield "</thought>\n\n"

            yield "<thought>\n"
            yield f"#### Coordinator\n{coordinator_output}\n\n"
            yield "</thought>\n\n"

            yield "<thought>\n"
            yield f"#### Research\n{researcher_facts[:300]}...\n\n"
            yield "</thought>\n\n"

            # Stage 2: Run Logic and Contrarian in parallel
            async def run_stage_2(facts):
                if __event_emitter__:
                    await __event_emitter__({"type": "status", "data": {"description": "Stage 2: Logic and Contrarian starting", "done": False}})
                logic_task = asyncio.create_task(self._logic_agent(user_message, facts))
                contrarian_task = asyncio.create_task(self._contrarian_agent(user_message, facts))
                res = await asyncio.gather(logic_task, contrarian_task)
                if __event_emitter__:
                    await __event_emitter__({"type": "status", "data": {"description": "Agents execution completed", "done": True}})
                return res

            logic_output, contrarian_output = asyncio.run(run_stage_2(researcher_facts))

            yield "<thought>\n"
            yield f"#### Logic\n{logic_output}\n\n"
            yield "</thought>\n\n"

            yield "<thought>\n"
            yield f"#### Contrarian\n{contrarian_output}\n"
            yield "</thought>\n\n"

            aligned_context = (
                f"COORDINATOR: {coordinator_output}\n"
                f"RESEARCH FACTS: {researcher_facts}\n"
                f"LOGIC CHECK: {logic_output}\n"
                f"CONTRARIAN: {contrarian_output}"
            )

            final_prompt = (
                "You are the finalizer. "
                "CRITICAL: If you use <think> tags for reasoning, you MUST output your final answer OUTSIDE and AFTER the </think> tag. "
                "Do NOT place your final answer inside the thinking process. "
                "DO NOT use any emojis. "
                f"ALIGNED CONTEXT: {aligned_context} \n USER QUERY: {user_message}"
            )

            try:
                with requests.post(
                    f"{self.valves.ollama_url}/api/generate",
                    json={
                        "model": self.valves.a4b_model,
                        "prompt": final_prompt,
                        "stream": True,
                        "options": {"num_ctx": 16384},
                    },
                    stream=True,
                    timeout=300,
                ) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                if not chunk.get("done", False):
                                    yield chunk.get("response", "")
                            except (json.JSONDecodeError, ValueError):
                                continue
            except requests.exceptions.RequestException as e:
                yield f"Error: {e}"

        return stream_response()
