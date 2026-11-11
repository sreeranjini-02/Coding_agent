
import os
import time
import logging

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

# --------------------------------------------------
# GEMINI CONFIGURATION
# --------------------------------------------------

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY missing in .env file")

client = genai.Client(api_key=API_KEY)

DEFAULT_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

MAX_OUTPUT_TOKENS = 2048
TEMPERATURE = 0.2


# --------------------------------------------------
# AVAILABLE MODELS
# --------------------------------------------------

AVAILABLE_MODELS = [
    {
        "name": "Gemini 3.8 Flash",
        "id": "gemini-3.8-flash"
    },
    {
        "name": "Gemini 3.7 Flash",
        "id": "gemini-3.7-flash"
    },
    {
        "name": "Gemini 3.6 Flash",
        "id": "gemini-3.6-flash"
    },
    {
        "name": "Gemini 3.5 Flash",
        "id": "gemini-3.5-flash"
    },
    {
        "name": "Gemini 3.5 Flash Lite",
        "id": "gemini-3.5-flash-lite"
    }
]


def get_models():
    return AVAILABLE_MODELS


# --------------------------------------------------
# FAST GEMINI RESPONSE
# --------------------------------------------------

def generate_response(
    prompt,
    selected_model=None,
    auto_fallback=False,
    context=""
):

    start_time = time.perf_counter()

    selected_model = selected_model or DEFAULT_MODEL

    final_prompt = (
        f"{context}\n\n{prompt}"
        if context
        else prompt
    )

    models_to_try = [selected_model]

    if auto_fallback:
        for item in AVAILABLE_MODELS:
            model_id = item["id"]

            if model_id not in models_to_try:
                models_to_try.append(model_id)

    errors = []

    for index, model in enumerate(models_to_try):

        try:
            response = client.models.generate_content(
                model=model,
                contents=final_prompt,
                config=types.GenerateContentConfig(
                    temperature=TEMPERATURE,
                    max_output_tokens=MAX_OUTPUT_TOKENS
                )
            )

            answer = response.text or "No response generated."

            elapsed = round(
                time.perf_counter() - start_time,
                2
            )

            logger.info(
                "Gemini response completed | Model=%s | Time=%ss",
                model,
                elapsed
            )

            return {
                "response": answer,
                "active_model": model,
                "fallback_used": index > 0,
                "errors": errors,
                "response_time": elapsed
            }

        except Exception as error:

            error_message = str(error)

            logger.warning(
                "Gemini model %s failed: %s",
                model,
                error_message
            )

            errors.append(error_message)

            if not auto_fallback:
                break

    elapsed = round(
        time.perf_counter() - start_time,
        2
    )

    return {
        "response": (
            "Unable to generate a response. "
            "Please check your model or API configuration."
        ),
        "active_model": selected_model,
        "fallback_used": False,
        "errors": errors,
        "response_time": elapsed
    }


# --------------------------------------------------
# STREAMING GEMINI RESPONSE
# --------------------------------------------------

def generate_response_stream(
    prompt,
    selected_model=None,
    context=""
):

    selected_model = selected_model or DEFAULT_MODEL

    final_prompt = (
        f"{context}\n\n{prompt}"
        if context
        else prompt
    )

    try:

        stream = client.models.generate_content_stream(
            model=selected_model,
            contents=final_prompt,
            config=types.GenerateContentConfig(
                temperature=TEMPERATURE,
                max_output_tokens=MAX_OUTPUT_TOKENS
            )
        )

        for chunk in stream:

            if chunk.text:
                yield chunk.text

    except Exception as error:

        logger.error(
            "Gemini streaming error: %s",
            error
        )

        yield "\n\nError: Unable to generate response."
