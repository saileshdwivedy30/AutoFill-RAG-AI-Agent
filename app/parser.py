from llama_parse import LlamaParse
import os
from app.config import LLAMA_CLOUD_API_KEY, LLAMA_CLOUD_BASE_URL

def parse_resume(file_path):
    parser = LlamaParse(
        api_key=LLAMA_CLOUD_API_KEY,
        base_url=LLAMA_CLOUD_BASE_URL,
        result_type="markdown",
        content_guideline_instruction="This is a resume, gather related facts together and format it as bullet points with headers"
    )
    result = parser.load_data(file_path)
    print("LlamaParse result (resume):", result)
    return result

def parse_application_form(file_path):
    parser = LlamaParse(
        api_key=LLAMA_CLOUD_API_KEY,
        base_url=LLAMA_CLOUD_BASE_URL,
        result_type="markdown",
        content_guideline_instruction="This is a job application form. Create a list of all the fields that need to be filled in.",
        formatting_instruction="Return a bulleted list of the fields ONLY."
    )
    result = parser.load_data(file_path)
    print("LlamaParse result (application form):", result)
    return result