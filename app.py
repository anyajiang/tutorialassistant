import time
import openai
from shiny import App, Outputs, ui, reactive, render
import os
import requests
import io

from typing_extensions import override
from openai import AssistantEventHandler

import json

def show_json(obj):
    print(json.loads(obj.model_dump_json()))


os.environ["OPENAI_API_KEY"] = "XXXXXX"

# Create the assistant
assistant = openai.beta.assistants.create(
    name="Tutorial Assistant",
    instructions="You are an expert tutorial assistant. Use your knowledge base to answer questions about the tutorial provided.",
    model="gpt-4o",
    tools=[{"type": "file_search"}],
)

# Fetch the content from the provided link
url = "https://interactivereport.github.io/cellxgene_VIP/tutorial/docs/index.html"
response = requests.get(url)
tutorial_text = response.text

# Create a vector store
vector_store = openai.beta.vector_stores.create(name="Tutorial Vector Store")

# Convert the string content to a file-like object
file_like_object = io.BytesIO(tutorial_text.encode('utf-8'))
file_like_object.name = "tutorial.html"  # Name the file

# Upload the file-like object to the vector store
file_batch = openai.beta.vector_stores.file_batches.upload_and_poll(
    vector_store_id=vector_store.id, files=[file_like_object]
)

assistant = openai.beta.assistants.update(
    assistant_id=assistant.id,
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)

# Create a new thread
thread = openai.beta.threads.create()

app_ui = ui.page_fluid(
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.h2("Tutorial Assistant"), 
            ui.input_text_area("message", "Ask the assistant a Question", value = "", rows = 5), 
            ui.input_action_button("example", "Example Question"), 
            ui.input_action_button("run", "Run")
        ), 
        ui.panel_main(
            ui.h3("Response"), 
            ui.output_text_verbatim("assistant")
        )
    )
)

def server(input, output, session): 

    @reactive.effect
    @reactive.event(input.example)
    def _(): 
        ui.update_text_area("message", value = "What is the purpose of CellXgene VIP?")
    
    @reactive.effect
    @reactive.event(input.run)
    def _():

        # Define the EventHandler
        class EventHandler(AssistantEventHandler):
            @override
            def on_message_done(self, message) -> None:
                show_json(message)


                message_content = message.content[0].text

                print(message_content)
                annotations = message_content.annotations
                citations = []
                for index, annotation in enumerate(annotations):
                    message_content.value = message_content.value.replace(
                        annotation.text, f"[{index}]"
                    )
                    if file_citation := getattr(annotation, "file_citation", None):
                        cited_file = openai.files.retrieve(file_citation.file_id)
                        citations.append(f"[{index}] {cited_file.filename} {citations}")

                @render.text 
                def assistant(): 

                    citations_text = "\n".join(citations)
                    # Combine message content and citations with a newline between them
                    mc_string = f"{message_content.value}\n{citations_text}"
                    # mc_string = str(message_content.value) + "\n".join(citations)
                    return mc_string
                
                print("\n".join(citations))

        with ui.Progress() as p:
            p.set(message = "Generating response from tutorial")
            message = openai.beta.threads.messages.create(
                thread_id=thread.id,
                role ="user",
                content = input.message()
            )

            # Run the assistant with the thread
            with openai.beta.threads.runs.stream(
                thread_id=thread.id,
                assistant_id=assistant.id,
                instructions="Please address the user as Jane Doe. The user has a premium account.",
                event_handler=EventHandler(),
            ) as stream:
                stream.until_done()

app = App(app_ui, server)
