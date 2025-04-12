import os, json, re
from app.events import *
from app.parser import parse_resume, parse_application_form
from app.llm_utils import get_llm, get_embed_model
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.workflow import Workflow, step, Context, InputRequiredEvent, StopEvent, StartEvent, HumanResponseEvent


class RAGWorkflow(Workflow):
    storage_dir = "./storage"
    llm = get_llm()
    query_engine = None

    @step
    async def set_up(self, ctx: Context, ev: StartEvent) -> ParseFormEvent:
        if not ev.resume_file or not ev.application_form:
            raise ValueError("Missing resume or application form")

        print("📎 set_up called with StartEvent:")
        print("   resume_file:", ev.resume_file)
        print("   application_form:", ev.application_form)

        if os.path.exists(self.storage_dir):
            storage_context = StorageContext.from_defaults(persist_dir=self.storage_dir)
            index = load_index_from_storage(storage_context)
        else:
            documents = parse_resume(ev.resume_file)
            print("📄 Parsed resume:", documents)
            if not documents:
                print("❌ No documents returned from parse_resume!")
            else:
                for i, doc in enumerate(documents):
                    print(f"📝 Doc {i} Preview:", doc.text[:300])
            index = VectorStoreIndex.from_documents(documents, embed_model=get_embed_model())
            index.storage_context.persist(persist_dir=self.storage_dir)

            # Test query
            test_result = index.as_query_engine(llm=self.llm).query("What is the candidate's current job title?")
            print("🧪 Test query result:", test_result.response)

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

        print("🧠 LLM returned (raw):", raw_json.text)

        # Remove ```json or ``` from LLM response
        cleaned_json = re.sub(r"```.*?\n", "", raw_json.text).strip().replace("```", "")

        try:
            fields = json.loads(cleaned_json)["fields"]
            print("✅ Parsed fields:", fields)
        except Exception as e:
            print("❌ Failed to parse cleaned LLM response:", cleaned_json)
            raise ValueError(f"Could not parse JSON from LLM: {e}")

        await ctx.set("fields_to_fill", fields)
        return GenerateQuestionsEvent()

    @step
    async def generate_questions(self, ctx: Context, ev: GenerateQuestionsEvent | FeedbackEvent) -> QueryEvent:
        fields = await ctx.get("fields_to_fill")
        for field in fields:
            question = f"How would you answer this question about the candidate? <field>{field}</field>"
            if hasattr(ev, "feedback"):
                question += f"\nFeedback: <feedback>{ev.feedback}</feedback>"
            ctx.send_event(QueryEvent(field=field, query=question))
        await ctx.set("total_fields", len(fields))
        return

    @step
    async def ask_question(self, ctx: Context, ev: QueryEvent) -> ResponseEvent:
        response = self.query_engine.query(ev.query)
        return ResponseEvent(field=ev.field, response=response.response)

    @step
    async def fill_in_application(self, ctx: Context, ev: ResponseEvent) -> InputRequiredEvent:
        total_fields = await ctx.get("total_fields")
        responses = ctx.collect_events(ev, [ResponseEvent] * total_fields)
        if responses is None:
            return None
        responseList = "\n".join(f"Field: {r.field}\nResponse: {r.response}" for r in responses)
        result = self.llm.complete(f"""
        Combine the field-response pairs into a filled application form.
        <responses>
        {responseList}
        </responses>
        """)
        await ctx.set("filled_form", str(result))
        return InputRequiredEvent(prefix="Feedback?", result=result)

    # @step
    # async def get_feedback(self, ctx: Context, ev: HumanResponseEvent) -> FeedbackEvent | StopEvent:
    #     result = self.llm.complete(f"""
    #     Human feedback: <feedback>{ev.response}</feedback>
    #     Reply 'OKAY' if it's good, else 'FEEDBACK'.
    #     """)
    #     verdict = result.text.strip()
    #     print(f"🧠 LLM Feedback Verdict: '{verdict}'")
    #     if verdict == "OKAY":
    #         return StopEvent(result=await ctx.get("filled_form"))
    #     return FeedbackEvent(feedback=ev.response)

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
        print(f"🧠 LLM Feedback Verdict: '{verdict}'")

        if verdict == "OKAY":
            return StopEvent(result=filled_form)
        else:
            return FeedbackEvent(feedback=ev.response)




