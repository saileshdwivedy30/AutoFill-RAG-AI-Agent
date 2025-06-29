import os, json, re, shutil, hashlib
from rapidfuzz import fuzz
from app.events import *
from app.parser import parse_resume, parse_application_form
from app.llm_utils import get_llm, get_embed_model
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.workflow import Workflow, step, Context, InputRequiredEvent, StopEvent, StartEvent, HumanResponseEvent


def get_file_hash(file_path):
    """Generate a SHA256 hash from the file contents."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

class RAGWorkflow(Workflow):
    storage_dir = "./storage"
    llm = get_llm()
    query_engine = None

    @step
    async def set_up(self, ctx: Context, ev: StartEvent) -> ParseFormEvent:
        if not ev.resume_file or not ev.application_form:
            raise ValueError("Missing resume or application form")

        print("   set_up called with StartEvent:")
        print("   resume_file:", ev.resume_file)
        print("   application_form:", ev.application_form)

        # Use resume hash as unique storage path
        resume_hash = get_file_hash(ev.resume_file)
        self.storage_dir = f"./storage/{resume_hash}"

        if os.path.exists(self.storage_dir):
            print("Using cached index for this resume")
            storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
            index = load_index_from_storage(storage_context)
        else:
            print("New resume detected — parsing and indexing")
            documents = parse_resume(ev.resume_file)
            if not documents:
                raise ValueError("Resume parsing returned no documents.")
            index = VectorStoreIndex.from_documents(documents, embed_model=get_embed_model())
            index.storage_context.persist(persist_dir=self.storage_dir)

            # # test query
            # test_result = index.as_query_engine(llm=self.llm).query("What is the candidate's current job title?")
            # print("🧪 Test query result:", test_result.response)

        self.query_engine = index.as_query_engine(llm=self.llm, similarity_top_k=5)
        return ParseFormEvent(application_form=ev.application_form)


    @step
    async def parse_form(self, ctx: Context, ev: ParseFormEvent) -> GenerateQuestionsEvent:
        result = parse_application_form(ev.application_form)[0]

        raw_json = self.llm.complete(f"""
        You are an assistant helping to extract fields from job application forms.
        This is a markdown-formatted list of fields in a job application form:

        <form>{result.text}</form>

        Respond with a valid JSON object in the following format:
        {{
          "fields": ["First Name", "Last Name", ...]
        }}

        Return **only** valid JSON — no markdown, no comments, no explanations.
        """)

        print("LLM returned (raw):", raw_json.text)
        cleaned_json = re.sub(r"```.*?\n", "", raw_json.text).strip().replace("```", "")

        try:
            fields = json.loads(cleaned_json)["fields"]
            print("Parsed fields:", fields)
        except Exception as e:
            print("Failed to parse cleaned LLM response:", cleaned_json)
            raise ValueError(f"Could not parse JSON from LLM: {e}")

        await ctx.set("fields_to_fill", fields)
        await ctx.set("field_answers", {})
        return GenerateQuestionsEvent()

    @step
    async def generate_questions(self, ctx: Context, ev: GenerateQuestionsEvent | FeedbackEvent) -> QueryEvent:
        fields = await ctx.get("fields_to_fill")
        feedback = ""
        matched_fields = []

        if isinstance(ev, FeedbackEvent):
            feedback = ev.feedback.lower()
            matched_fields = [
                field for field in fields
                if fuzz.partial_ratio(field.lower(), feedback) > 70
            ]
            print("Matched feedback to fields:", matched_fields)

        fields_to_query = matched_fields if matched_fields else fields

        for field in fields_to_query:
            question = f"How would you answer this question about the candidate? <field>{field}</field>"
            if feedback:
                question += f"\nFeedback: <feedback>{feedback}</feedback>"
            print(f"Sending query for field '{field}': {question}")
            ctx.send_event(QueryEvent(field=field, query=question))

        await ctx.set("total_fields", len(fields))
        await ctx.set("fields_to_query", fields_to_query)
        await ctx.set("latest_feedback", feedback)
        return

    @step
    async def ask_question(self, ctx: Context, ev: QueryEvent) -> ResponseEvent:
        response = self.query_engine.query(ev.query)
        return ResponseEvent(field=ev.field, response=response.response)

    @step
    async def fill_in_application(self, ctx: Context, ev: ResponseEvent) -> InputRequiredEvent:
        fields = await ctx.get("fields_to_fill")
        prev_answers = await ctx.get("field_answers", default={})
        fields_just_updated = await ctx.get("fields_to_query")

        print("🧪 Debug: fields to query:", fields_just_updated)
        print("🧪 Debug: previous answers BEFORE update:", prev_answers)

        # Collect only the new responses
        new_responses = ctx.collect_events(ev, [ResponseEvent] * len(fields_just_updated))
        if new_responses is None:
            print("No new responses collected.")
            return None

        # Update just the changed fields
        for r in new_responses:
            print(f"Updating field: {r.field} -> {r.response}")
            prev_answers[r.field] = r.response

        await ctx.set("field_answers", prev_answers)

        # Format final output in readable form
        formatted_form = "\n\n".join(
            f"{field}: {prev_answers[field]}" for field in fields if field in prev_answers
        )
        full_output = f"Application Form\n\n{formatted_form}"
        print("Final formatted form:\n", full_output)

        await ctx.set("filled_form", full_output)
        return InputRequiredEvent(prefix="Feedback?", result=full_output)

    @step
    async def get_feedback(self, ctx: Context, ev: HumanResponseEvent) -> FeedbackEvent | StopEvent:
        filled_form = await ctx.get("filled_form")

        result = self.llm.complete(f"""
        You have received human feedback on the application form you filled out for a candidate.
        Please carefully compare the feedback to the contents of the form and decide whether any changes are needed.

        <form>
        {filled_form}
        </form>

        <feedback>
        {ev.response}
        </feedback>

        Reply only with the word:
        - 'OKAY' if no change is needed
        - 'FEEDBACK' if the form must be updated based on this feedback
        """)

        verdict = result.text.strip()
        print(f"LLM Feedback Verdict: '{verdict}'")

        if verdict == "OKAY":
            return StopEvent(result=filled_form)
        else:
            return FeedbackEvent(feedback=ev.response)


