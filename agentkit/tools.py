from smolagents import RunResult

def to_chat_completion(result: RunResult, model_name: str) -> dict:
    """Convert a RunResult to OpenAI chat completion format.

    Args:
        result: The RunResult from an agent run
        model_name: The name of the model used

    Returns:
        A dictionary in OpenAI chat completion format
    """
    import time

    print(type(result))

    content = str(result.output) if result.output is not None else ""
    finish_reason = "stop" if result.state == "success" else "length"

    return {
        "id": f"chatcmpl-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(result.timing.start_time),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "logprobs": None,
                "finish_reason": finish_reason
            }
        ],
        "usage": {
            "prompt_tokens": result.token_usage.input_tokens if result.token_usage else 0,
            "completion_tokens": result.token_usage.output_tokens if result.token_usage else 0,
            "total_tokens": result.token_usage.total_tokens if result.token_usage else 0,
            "prompt_tokens_details": {
                "cached_tokens": 0,
                "audio_tokens": 0
            },
            "completion_tokens_details": {
                "reasoning_tokens": 0,
                "audio_tokens": 0,
                "accepted_prediction_tokens": 0,
                "rejected_prediction_tokens": 0
            }
        },
        "service_tier": "default"
    }