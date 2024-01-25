from langchain.chat_models import AzureChatOpenAI
from langchain.memory import ConversationBufferWindowMemory

from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain

from langchain.callbacks.base import BaseCallbackHandler

import os


class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs):
        self.text += token
        self.container.markdown(self.text)


# The LLM
llm = AzureChatOpenAI(
    streaming=True,
    callbacks=CallbackManager([StreamingStdOutCallbackHandler()]),
    temperature=0.0,
    deployment_name=os.getenv("OPENAI_DEPLOYMENT_NAME"),
)

# The Prompt
template = """You are a helpful assistant...."""
QA_CHAIN_PROMPT = PromptTemplate.from_template(template)


# The Memory
buffer_window_memory = ConversationBufferWindowMemory(
    memory_key="chat_history", return_messages=True, k=4
)
