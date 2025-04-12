import asyncio
from app.workflow import RAGWorkflow
from llama_index.core.workflow import InputRequiredEvent, HumanResponseEvent


async def run_workflow(resume_file, application_form):
    w = RAGWorkflow(timeout=600, verbose=False)
    handler = w.run(resume_file=resume_file, application_form=application_form)

    async for event in handler.stream_events():
        if isinstance(event, InputRequiredEvent):
            print("Filled form:")
            print(event.result)
            response = input(event.prefix)
            handler.ctx.send_event(HumanResponseEvent(response=response))

    final_result = await handler
    print("Done!")
    print(str(final_result))

