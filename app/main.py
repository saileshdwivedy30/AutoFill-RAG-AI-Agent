from app.workflow import RAGWorkflow
from llama_index.core.workflow import InputRequiredEvent, HumanResponseEvent
import time

# Shared state
workflow_handler = None
latest_result = None

def merge_results(original, updated):
    """
    Merge new results into existing ones, preserving unchanged fields.
    Logs which fields are being updated.
    """
    if not isinstance(original, dict) or not isinstance(updated, dict):
        return updated

    print("Updating fields from feedback:")
    for k in updated:
        if k not in original or original[k] != updated[k]:
            print(f" - {k}")

    merged = original.copy()
    merged.update(updated)
    return merged

async def start_workflow(resume_file, application_form):
    global workflow_handler, latest_result
    w = RAGWorkflow(timeout=1200, verbose=False)
    workflow_handler = w.run(resume_file=resume_file, application_form=application_form)

    async for event in workflow_handler.stream_events():
        print("Received event:", type(event).__name__)
        if isinstance(event, InputRequiredEvent):
            latest_result = event.result
            print("Form generated. Awaiting feedback.")
            return str(latest_result)

    print("No feedback step triggered.")
    return "Something went wrong, no form was generated."

async def resume_workflow_with_feedback(feedback_text):
    global workflow_handler, latest_result

    if workflow_handler is None:
        return "No active session. Please run the agent first."

    if not feedback_text or feedback_text.strip() == "":
        return str(latest_result)

    feedback = feedback_text.strip().lower()

    if feedback in ["done", "ok", "okay", "looks good", "final", "good to go"]:
        print("User confirmed final result.")
        workflow_handler.ctx.send_event(HumanResponseEvent(response="done"))
    else:
        print("Received feedback:", feedback_text)
        workflow_handler.ctx.send_event(HumanResponseEvent(response=feedback_text))

    async for event in workflow_handler.stream_events():
        print("Follow-up event:", type(event).__name__)
        if isinstance(event, InputRequiredEvent):
            latest_result = merge_results(latest_result, event.result)
            return str(latest_result)

    final_result = await workflow_handler
    return str(final_result)

