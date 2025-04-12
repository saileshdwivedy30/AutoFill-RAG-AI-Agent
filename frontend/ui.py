import gradio as gr
import nest_asyncio
import asyncio
from app.main import run_workflow
import os, shutil, uuid

nest_asyncio.apply()

def run_form(resume, form):
    try:
        # Safely copy uploaded files to a local accessible path
        os.makedirs("uploads", exist_ok=True)
        resume_path = f"uploads/resume_{uuid.uuid4().hex}.pdf"
        form_path = f"uploads/form_{uuid.uuid4().hex}.pdf"

        shutil.copy(resume.name, resume_path)
        shutil.copy(form.name, form_path)

        # Run async logic
        asyncio.get_event_loop().run_until_complete(
            run_workflow(resume_path, form_path)
        )

        return "✅ Form processed successfully!"
    except Exception as e:
        return f"❌ Error: {str(e)}"

with gr.Blocks() as demo:
    resume = gr.File(label="Upload Resume")
    form = gr.File(label="Upload Job Application")
    output = gr.Textbox(label="Output")
    btn = gr.Button("Run")
    btn.click(fn=run_form, inputs=[resume, form], outputs=output)

demo.launch()
