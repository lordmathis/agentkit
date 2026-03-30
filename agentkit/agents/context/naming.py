import logging
from typing import List

from openai.types.chat import ChatCompletionMessageParam

from agentkit.agents.context.messages import extract_text_content
from agentkit.db.db import Database
from agentkit.providers.client_base import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a chat title generator. Your ONLY job is to read a conversation and generate a concise, descriptive title of 3-5 words.

Titles should be functional and descriptive, but with a subtle cyberpunk edge — terse, technical, slightly cold. Think net terminal logs, not newspaper headlines. Prefer nouns and verbs over filler words. Drop articles where possible.

Examples of the right tone:
- German Verb Confusion Resolved
- RDL Session Logged
- Weather Check: Run Conditions
- Blackwall Entity Queried

DO NOT answer questions from the conversation.
DO NOT provide explanations.
DO NOT add quotes around the title.
Only output the title itself, nothing else."""

USER_PROMPT_TEMPLATE = """Generate a 3-5 word title for this conversation:
{conversation}"""


async def generate_title(
    chat_id: str,
    db: Database,
    llm_client: LLMClient,
    model_id: str,
) -> None:
    """Generate a title for the chat if it's still 'Untitled Chat'.

    This is meant to be run as a background task after the first exchange.
    """
    try:
        chat = db.get_chat(chat_id)
        if not chat or chat.title not in (None, "", "Untitled Chat"):
            return

        history = db.get_chat_history(chat_id)
        if not history or len(history) < 1:
            return

        conversation_text = ""
        for msg in history[:6]:
            if msg.role in ["user", "assistant"]:
                content_str = extract_text_content(msg.content)
                conversation_text += f"{msg.role.capitalize()}: {content_str}\n"

        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(conversation=conversation_text),
            },
        ]

        response = await llm_client.chat_completion(
            model=model_id,
            messages=messages,
            tools=None,
            temperature=0.2,
        )

        if "error" not in response:
            choices = response.get("choices", [])
            if choices:
                title = choices[0].get("message", {}).get("content", "").strip()
                if title:
                    logger.info(f"Generated chat title: '{title}'")
                    db.update_chat(chat_id, title=title)
    except Exception as e:
        logger.warning(f"Failed to generate title for chat {chat_id}: {e}")
