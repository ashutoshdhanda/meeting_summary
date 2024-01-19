import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
import time
load_dotenv()

client = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2023-05-15",
)

async def main() -> None:
    stream = await client.chat.completions.create(
        model="sopa",
        messages=[{"role": "user", "content": "What is chatgpt?"}],
        stream=True,
    )

    message_content = ""  # Initialize an empty string to accumulate message content

    async for chunk in stream:
        for choice in chunk.choices:
            if hasattr(choice, 'delta') and hasattr(choice.delta, 'content') and choice.delta.content:
                # Add a space after the content if it's not a punctuation mark
                if choice.delta.content not in {".", ",", "!", "?", ";", ":"}:
                    message_content += choice.delta.content + " "
                else:
                    message_content += choice.delta.content

    print(message_content.strip())  # Print the entire message after accumulating all parts

asyncio.run(main())
