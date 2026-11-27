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

# How many times to retry the same model when it is overloaded
OVERLOAD_ATTEMPTS = 3


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
# OVERLOAD DETECTION
# --------------------------------------------------

def _is_overloaded(error):
    """True when Gemini reports the model is busy (503 / UNAVAILABLE)."""

    message = str(error)

    return "503" in message or "UNAVAILABLE" in message


# --------------------------------------------------
# FAST GEMINI RESPONSE (NON-STREAMING)
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
# STREAMING GEMINI RESPONSE (NO FALLBACK)
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


# --------------------------------------------------
# START A STREAM WITH RETRY ON OVERLOAD
# --------------------------------------------------

def _start_stream_with_retry(model, prompt, attempts=OVERLOAD_ATTEMPTS):
    """
    Opens a stream and reads its first text chunk.
    Retries the same model when it is overloaded (503 / UNAVAILABLE),
    waiting 1 second, then 2 seconds, between attempts.
    Other errors are raised immediately so the caller can try another model.

    Returns (iterator, first_text).
    """

    last_error = None

    for attempt in range(attempts):

        try:

            stream = client.models.generate_content_stream(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=TEMPERATURE,
                    max_output_tokens=MAX_OUTPUT_TOKENS
                )
            )

            iterator = iter(stream)

            for chunk in iterator:
                if chunk.text:
                    return iterator, chunk.text

            raise RuntimeError("Model returned no text.")

        except Exception as error:

            last_error = error

            if not _is_overloaded(error):
                raise

            logger.warning(
                "Model %s overloaded (attempt %s of %s)",
                model,
                attempt + 1,
                attempts
            )

            if attempt < attempts - 1:
                time.sleep(2 ** attempt)

    raise last_error


# --------------------------------------------------
# STREAMING WITH FALLBACK
# --------------------------------------------------

def open_stream_with_fallback(
    prompt,
    selected_model=None,
    auto_fallback=False
):
    """
    Tries models in order until one returns text.
    Overloaded models are retried first. Nothing is sent to the
    browser until a model has produced its first chunk, so the
    reply can report the model that actually answered.
    """

    selected_model = selected_model or DEFAULT_MODEL

    models_to_try = [selected_model]

    if auto_fallback:
        for item in AVAILABLE_MODELS:
            if item["id"] not in models_to_try:
                models_to_try.append(item["id"])

    errors = []

    for index, model in enumerate(models_to_try):

        try:

            iterator, first_text = _start_stream_with_retry(model, prompt)

            def rest_of_stream(first=first_text, remaining=iterator):

                yield first

                for chunk in remaining:
                    if chunk.text:
                        yield chunk.text

            logger.info(
                "Streaming started | Model=%s | Fallback=%s",
                model,
                index > 0
            )

            return {
                "stream": rest_of_stream(),
                "active_model": model,
                "fallback_used": index > 0,
                "errors": errors
            }

        except Exception as error:

            logger.warning(
                "Gemini model %s failed before streaming: %s",
                model,
                error
            )

            errors.append(str(error))

            if not auto_fallback:
                break

    raise RuntimeError(
        "Unable to start a response from any model."
    )