from llama_index.core.workflow import Event

class ParseFormEvent(Event):
    application_form: str

class QueryEvent(Event):
    query: str
    field: str = ""

class ResponseEvent(Event):
    field: str
    response: str

class FeedbackEvent(Event):
    feedback: str

class GenerateQuestionsEvent(Event):
    pass
