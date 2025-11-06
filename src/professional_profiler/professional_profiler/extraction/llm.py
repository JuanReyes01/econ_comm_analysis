from .pydantic_class import AuthorDegrees
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_vertex import GoogleVertexProvider

from pydantic_ai import Agent
from httpx import AsyncClient
import os
import dotenv
import json
from professional_profiler.config import load_app_config
from professional_profiler.logging.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
dotenv.load_dotenv()
# Load the configuration
config = load_app_config()

# Global accumulator for total cost across calls
total_cost_accumulator = 0.0

async def extract_degrees_async(sentences: str) -> AuthorDegrees:
    # Read and prepare prompt
    with open(config.extraction.paths.prompt_path, encoding="utf-8") as f:
        prompt = f.read()
    prompt += f"\n{sentences}"

    # Prepare hook to capture usage from DeepSeek response
    token_usage = {"input": 0, "output": 0}
    async def capture_usage(response):
        try:
            # Ensure full body is loaded
            raw = await response.aread()
            data = json.loads(raw)
            usage = data.get("usage", {})
            token_usage["input"] = usage.get("input_tokens", 0)
            token_usage["output"] = usage.get("output_tokens", 0)
        except Exception as e:
            logger.warning("Failed to parse usage: %s", e)

        
        # Create custom HTTP client with response hook
    custom_http_client = AsyncClient(
        timeout=30,
        event_hooks={"response": [capture_usage]}
    )

    # Initialize DeepSeek model via pydantic_ai
    deepseek_model = OpenAIModel(
        'deepseek-chat',
        provider=DeepSeekProvider(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            http_client=custom_http_client
        ),
    )
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    gemini_model = GeminiModel(
        model_name="gemini-2.5-flash-preview-04-17",
        provider="google-gla",     
    )
    agent = Agent(gemini_model, output_type=AuthorDegrees, max_result_retries=3)

    # Run the agent and await the result
    result: AuthorDegrees = await agent.run(prompt)

    # Compute cost based on DeepSeek pricing (standard)
    input_tokens = token_usage.get("input", 0)
    output_tokens = token_usage.get("output", 0)
    cost_input = (input_tokens / 1_000_000) * 0.07
    cost_output = (output_tokens / 1_000_000) * 1.10
    query_cost = cost_input + cost_output

    # Log per-query cost
    logger.debug(
        "Query cost: input=%d tokens ($%.6f) + output=%d tokens ($%.6f) = $%.6f",
        input_tokens, cost_input,
        output_tokens, cost_output,
        query_cost
    )

    # Update and log total accumulated cost
    global total_cost_accumulator
    total_cost_accumulator += query_cost
    logger.debug("Total cost so far: $%.6f", total_cost_accumulator)

    return result
