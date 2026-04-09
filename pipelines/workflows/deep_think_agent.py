"""
title: Gemma 4 Multistage Deep Think
id: gemma_4_multistage
description: Multistage orchestration for intent detection, web search, and deep reasoning.
author: csning1998
version: 1.0
"""

import json
import os
from typing import Generator, Iterator, List, Union

import requests
from pydantic import BaseModel, Field


class Pipeline:
    """Open WebUI Pipeline for multistage LLM reasoning."""

    id: str = "gemma_4_multistage"
    name: str = "Gemma 4 Multistage Deep Think"

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
            description="Model identifier for intent and keywords generation.",
        )
        a4b_model: str = Field(
            default="gemma4:26b",
            description="Model identifier for deep reasoning (thinking mode).",
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

    def _generate_search_query(self, user_message: str) -> str:
        """Uses E4B model to determine if search is needed and generate keywords.

        Args:
            user_message: The raw message from the user.

        Returns:
            A string of keywords or 'NO_SEARCH'.
        """
        prompt = (
            "Determine if this query needs a web search. If yes, output ONLY 3-5 "
            f"search keywords. If no, output 'NO_SEARCH'. Query: {user_message}"
        )
        try:
            response = requests.post(
                f"{self.valves.ollama_url}/api/generate",
                json={
                    "model": self.valves.e4b_model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": 0,
                },
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.exceptions.RequestException as e:
            print(f"E4B Call failed: {e}")
            return "NO_SEARCH"

    def _fetch_web_context(self, keywords: str) -> str:
        """Fetches search results from SearXNG based on keywords.

        Args:
            keywords: Keywords for searching.

        Returns:
            A summarized context string from search results.
        """
        if "NO_SEARCH" in keywords:
            return ""

        try:
            search_url = f"{self.valves.searxng_url}/search?q={keywords}&format=json"
            response = requests.get(search_url, timeout=15)
            response.raise_for_status()
            results = response.json().get("results", [])[:5]
            return "\n".join(
                [f"Source: {r['url']}\nContent: {r['content']}" for r in results]
            )
        except requests.exceptions.RequestException as e:
            print(f"SearXNG Call failed: {e}")
            return ""

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """Main pipeline execution entry point.

        Args:
            user_message: The current user message.
            model_id: The requested model ID.
            messages: Conversation history.
            body: Full request body from Open WebUI.

        Returns:
            A generator for the streamed response.
        """
        print(f"Processing query: {user_message}")

        # Stage 1: Intent & Search Key Generation
        keywords = self._generate_search_query(user_message)

        # Stage 2: Web Search
        context = self._fetch_web_context(keywords)

        # Stage 3: Deep Inference with Thinking Trigger
        final_prompt = (
            "<|think|> You are a meticulous deep-thinking analyst. Use the "
            "following facts to answer the user query step-by-step. "
            f"FACTS: {context} \n USER QUERY: {user_message}"
        )

        def stream_response():
            """Streams the response from the 26B model."""
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
                yield f"Error in Deep Inference Stage: {e}"

        return stream_response()
