from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

def get_llm(model="gpt-4o-mini"):
    return OpenAI(model=model)

def get_embed_model():
    return OpenAIEmbedding(model_name="text-embedding-3-small")
