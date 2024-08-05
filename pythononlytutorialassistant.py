from openai import OpenAI
import requests
import time

# Initialize the OpenAI client
client = OpenAI(api_key="XXXXXX")

# Create the assistant
assistant = client.beta.assistants.create(
    name="Tutorial Assistant",
    instructions="You are an expert tutorial assistant. Use your knowledge base to answer questions about the tutorial provided.",
    model="gpt-4o",
    tools=[{"type": "file_search"}],
)

# Fetch the content from the provided link
url = "https://interactivereport.github.io/cellxgene_VIP/tutorial/docs/index.html"
response = requests.get(url)
tutorial_text = response.text

# Save the content to a file
with open("tutorial.html", "w") as file:
    file.write(tutorial_text)

# Create a vector store
vector_store = client.beta.vector_stores.create(name="Tutorial Vector Store")

# Upload the file to the vector store
file_streams = [open("tutorial.html", "rb")]
file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
    vector_store_id=vector_store.id, files=file_streams
)

# Update the assistant with the vector store
assistant = client.beta.assistants.update(
    assistant_id=assistant.id,
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)

from typing_extensions import override
from openai import AssistantEventHandler

# Define the EventHandler
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
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f"[{index}]"
            )
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")

        print(message_content.value)
        # print("\n".join(citations))

# Function to handle user input and assistant response
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
        
        # Start the assistant response stream
        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=assistant.id,
            instructions="Please address the user as Jane Doe. The user has a premium account.",
            event_handler=EventHandler(),
        ) as stream:
            stream.until_done()
        
        # Sleep to ensure the current run has completed before continuing
        time.sleep(1)

# Create a thread without hardcoding the initial question
thread = client.beta.threads.create(
    messages=[]
)

# Start the interactive session
interactive_session()
