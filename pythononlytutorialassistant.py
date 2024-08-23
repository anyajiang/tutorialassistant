from openai import OpenAI
import requests
import time
from typing_extensions import override
from openai import AssistantEventHandler
import io

client = OpenAI(api_key="XXXXXX")

# assistant = client.beta.assistants.create(
#     name="Tutorial Assistant",
#     instructions="You are an expert tutorial assistant. Use your knowledge base to answer questions about the tutorial provided.",
#     model="gpt-4o",
#     tools=[{"type": "file_search"}],
# )

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

vector_store_id =  "vs_RYTqHdROEXKxbV2z8ZPiIw34"

# vector_store = client.beta.vector_stores.create(name="Tutorial Vector Store")

# file_streams = [open("tutorial.html", "rb")]
# file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
#     vector_store_id=vector_store.id, files=file_streams
# )

assistant = client.beta.assistants.update(
    assistant_id, 
    tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
)

class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > {text}", end="", flush=True)

    @override
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    @override
    def on_message_done(self, message) -> None:
        # print a citation to the file searched
        message_content = message.content[0].text
        # annotations = message_content.annotations
        # citations = []
        # for index, annotation in enumerate(annotations):
        #     message_content.value = message_content.value.replace(
        #         annotation.text, f"[{index}]"
        #     )
        #     if file_citation := getattr(annotation, "file_citation", None):
        #         cited_file = client.files.retrieve(file_citation.file_id)
        #         citations.append(f"[{index}] {cited_file.filename}")

        print(message_content.value)
        # print("\n".join(citations))

def interactive_session():
    while True:
        user_input = input("\nYou > ")
        if user_input.lower() in ['exit', 'quit']:
            break
        
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )
        
        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=assistant.id,
            instructions="You are an expert of 'CellXgene VIP' application. If the question is not related to  'CellXgene VIP' application then answer with 'Please ask me question about the CellXgene VIP Application!' ",
            event_handler=EventHandler(),
        ) as stream:
            stream.until_done()
        time.sleep(1)

thread = client.beta.threads.create(
    messages=[]
)

interactive_session()
