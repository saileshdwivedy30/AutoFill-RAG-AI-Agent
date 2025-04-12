import os

def get_openai_api_key():
    return os.getenv("OPENAI_API_KEY")

def get_llama_cloud_api_key():
    return os.getenv("LLAMA_CLOUD_API_KEY")
