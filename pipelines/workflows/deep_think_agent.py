"""Gemma 4 Multistage Reasoning Pipeline for Open WebUI.

This module implements a multistage orchestration logic to handle intent detection,
web search, and deep reasoning using Gemma 4 models (e4b and 26b) within
a resource-constrained environment.
"""

import json
import os
from typing import Generator, Iterator, List, Union

import requests


class Pipeline:
    """Open WebUI Pipeline for multistage LLM reasoning."""

    def __init__(self):
        """Initializes the pipeline with service URLs and model identifiers."""
        self.name = "Gemma 4 Multistage Deep Think"
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.searxng_url = os.getenv("SEARXNG_BASE_URL", "http://searxng:8080")
        self.e4b_model = "gemma4:e4b"
        self.a4b_model = "gemma4:26b"

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
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.e4b_model,
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
            search_url = f"{self.searxng_url}/search?q={keywords}&format=json"
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
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.a4b_model,
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
                            chunk = json.loads(line)
                            if not chunk.get("done", False):
                                yield chunk.get("response", "")
            except requests.exceptions.RequestException as e:
                yield f"Error in Deep Inference Stage: {e}"

        return stream_response()
