import io
import openai
import requests
from shiny import App, ui, reactive, render
import os
from typing_extensions import override
from openai import AssistantEventHandler

os.environ["OPENAI_API_KEY"] = "XXXXXX"

# create new assistant when needed
# assistant = openai.beta.assistants.create(
#     name="Tutorial Assistant",
#     instructions="You are an expert of 'CellXgene VIP' application. If the question is not related to  'CellXgene VIP' application then answer with 'Please ask me question about the CellXgene VIP Application!' ",
#     model="gpt-4o",
#     tools=[{"type": "file_search"}],
# )

# retrieve lastest assistant id 
# my_assistants = openai.beta.assistants.list(    
#     order="desc",
#     limit="20",
# )

# get latest assistant id which is the first one in the list
# print(my_assistants)

# my_assistant = openai.beta.assistants.retrieve("asst_NXjq46TI9BetZS4StOrMAf1i")
assistant_id = "asst_NXjq46TI9BetZS4StOrMAf1i"

urls = [
    "https://interactivereport.github.io/cellxgene_VIP/tutorial/docs/index.html", 
    "https://interactivereport.github.io/cellxgene_VIP/tutorial/docs/how-to-use-cellxgene-vip.html", 
    "https://interactivereport.github.io/cellxgene_VIP/tutorial/docs/methods.html", 
    "https://interactivereport.github.io/cellxgene_VIP/tutorial/docs/helpful-tips.html", 
    "https://interactivereport.github.io/cellxgene_VIP/tutorial/docs/web-resource.html"
]

# Initialize a list to hold file-like objects
file_like_objects = []

# Fetch and prepare content from each URL
for url in urls:
    response = requests.get(url)
    tutorial_text = response.text
    
    # Convert the content to a file-like object
    file_like_object = io.BytesIO(tutorial_text.encode('utf-8'))
    file_like_object.name = url.split("/")[-1]  # Name the file based on the URL
    # print(file_like_object.name)
    file_like_objects.append(file_like_object)

# create a vector store when needed
# vector_store = openai.beta.vector_stores.create(name="Tutorial Vector Store")
# get vector store id
# print(vector_store)

vector_store_id =  "vs_RYTqHdROEXKxbV2z8ZPiIw34"

# Upload all files to the same vector store when needed
# file_batch = openai.beta.vector_stores.file_batches.upload_and_poll(
#     vector_store_id=vector_store_id, files=file_like_objects
# )

assistant = openai.beta.assistants.update(
    assistant_id,
    tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
)

thread = openai.beta.threads.create()

app_ui = ui.page_fluid(
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.h2("Tutorial Assistant"), 
            ui.input_text_area("message", "Ask the assistant a Question", value = "", rows = 5), 
            ui.input_action_button("example", "Example Question"), 
            ui.input_action_button("clear", "Clear"),
            ui.input_action_button("run", "Run")
        ), 
        ui.panel_main(
            ui.h3("Response"), 
            ui.output_text_verbatim("assistant"), 
            ui.h5("Token Usage"),
            ui.output_text_verbatim("token_usage")
        )
    )
)

def server(input, output, session): 

    @reactive.effect
    @reactive.event(input.example)
    def _(): 
        ui.update_text_area("message", value = "What statistical methods are being used in Differential Expressed Genes?")

    @reactive.effect
    @reactive.event(input.clear)
    def _(): 
        ui.update_text_area("message", value = "")

        @output
        @render.text 
        def assistant(): 
            return "" 
        
        @output
        @render.text 
        def token_usage(): 
            return ""
        
    
    @reactive.effect
    @reactive.event(input.run)
    def _():

        # Define the EventHandler
        class EventHandler(AssistantEventHandler):
            
            @override
            def on_message_done(self, message) -> None:
                # show_json(message)


                message_content = message.content[0].text
                

                # print(message_content)
                # annotations = message_content.annotations
                # citations = []
                # for index, annotation in enumerate(annotations):
                #     message_content.value = message_content.value.replace(
                #         annotation.text, f"[{index}]"
                #     )
                #     if file_citation := getattr(annotation, "file_citation", None):
                #         cited_file = openai.files.retrieve(file_citation.file_id)
                #         citations.append(f"[{index}] {cited_file.filename} {citations}")

                @render.text 
                def assistant(): 

                    # citations_text = "\n".join(citations)
                    # # Combine message content and citations with a newline between them
                    # mc_string = f"{message_content.value}\n{citations_text}"
                    # mc_string = str(message_content.value) + "\n".join(citations)
                    return message_content.value
                    # return mc_string
                
                # print("\n".join(citations))

        with ui.Progress() as p:
            p.set(message = "Generating response from tutorial")
            message = openai.beta.threads.messages.create(
                thread_id=thread.id,
                role ="user",
                content = input.message()
            )

            with openai.beta.threads.runs.stream(
                thread_id=thread.id,
                assistant_id=assistant.id,
                instructions="You are an expert of 'CellXgene VIP' application. If the question is not related to  'CellXgene VIP' application then answer with 'Please ask me question about the CellXgene VIP Application!' ",
                event_handler=EventHandler(),
            ) as stream:
                stream.until_done()

        runs = openai.beta.threads.runs.list(
            thread_id=thread.id
        )
        # print(runs)

        tokens = stream.get_final_run().usage

        token_usage_text = (
            f"Completion Tokens: {tokens.completion_tokens}\n"
            f"Prompt Tokens: {tokens.prompt_tokens}\n"
            f"Total Tokens: {tokens.total_tokens}"
        )
         
        @render.text 
        def token_usage(): 
            return token_usage_text

app = App(app_ui, server)
