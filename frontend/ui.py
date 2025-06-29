import gradio as gr
import nest_asyncio
import asyncio
import shutil
import os
import uuid

from app.main import start_workflow, resume_workflow_with_feedback

nest_asyncio.apply()

# Shared variables
form_output_state = gr.State("")
feedback_prompt_state = gr.State("")

async def handle_run_form(resume, form):
    try:
        os.makedirs("uploads", exist_ok=True)

        resume_path = f"uploads/resume_{uuid.uuid4().hex}.pdf"
        form_path = f"uploads/form_{uuid.uuid4().hex}.pdf"
        shutil.copy(resume.name, resume_path)
        shutil.copy(form.name, form_path)

        result = await start_workflow(resume_path, form_path)
        return result, "Type feedback (or type 'done' to finish)"
    except Exception as e:
        return f"Error during form processing: {str(e)}", ""

async def handle_feedback_submit(feedback):
    try:
        result = await resume_workflow_with_feedback(feedback)
        return result
    except Exception as e:
        return f"Error during feedback processing: {str(e)}"

with gr.Blocks() as demo:
    gr.Markdown("## 🧠 Agentic Resume Filler")

    with gr.Row():
        resume = gr.File(label="Upload Resume (PDF)")
        form = gr.File(label="Upload Job Application Form (PDF)")

    run_button = gr.Button("🚀 Run Agent")
    form_display = gr.Markdown(label="📄 Filled Application Form")

    feedback_input = gr.Textbox(label="💬 Feedback (type 'done' when you're happy)", placeholder="e.g. Add link to portfolio...")
    submit_feedback_button = gr.Button("📤 Submit Feedback")

    run_button.click(
        fn=handle_run_form,
        inputs=[resume, form],
        outputs=[form_display, feedback_input],
    )

    submit_feedback_button.click(
        fn=handle_feedback_submit,
        inputs=[feedback_input],
        outputs=form_display,
    )

demo.launch()



