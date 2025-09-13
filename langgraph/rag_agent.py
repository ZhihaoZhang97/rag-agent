from typing import List, Optional
from typing_extensions import TypedDict
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import os
import chromadb
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.dashscope import DashScopeEmbeddings
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from dotenv import load_dotenv
from prompt import rag_prompt, grader_system_prompt, document_grade_prompt

load_dotenv()

### LLM
model = "gpt-4o"
llm = ChatOpenAI(model_name=model, temperature=0)

### Retriever (ChromaDB persisted in backend/data/vectordb)

# Use the same embeddings as the backend (DashScope) to ensure dimension match
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_EMBEDDINGS_MODEL", "text-embedding-v4")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
CHROMADB_API_KEY = os.getenv("CHROMADB_API_KEY")
embeddings = (
    DashScopeEmbeddings(model=DASHSCOPE_MODEL, dashscope_api_key=DASHSCOPE_API_KEY)
    if DASHSCOPE_API_KEY
    else DashScopeEmbeddings(model=DASHSCOPE_MODEL)
)
  
client = chromadb.CloudClient(
    api_key=CHROMADB_API_KEY,
    tenant='fab68d49-41be-47f4-9be3-0fdd622654a4',
    database='rag-agent'
)

vectorstore = Chroma(
    collection_name="documents",
    embedding_function=embeddings,
    client=client,
)
retriever = vectorstore.as_retriever(k=4)

### RAG Chain

rag_chain = rag_prompt | llm | StrOutputParser()

### Retrieval Grader


# Data model for the output
class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )


# LLM with tool call
structured_llm_grader = llm.with_structured_output(GradeDocuments)

retrieval_grader = document_grade_prompt | structured_llm_grader


def extract_question_from_messages(messages) -> str:
    """
    Extract the question text from the last human message.

    Args:
        messages: List of chat messages

    Returns:
        str: The question text from the last human message
    """
    print(f"DEBUG: Total messages received: {len(messages)}")

    # Find the last human message
    for i, message in enumerate(reversed(messages)):
        print(
            f"DEBUG: Message {len(messages)-1-i}: type={getattr(message, 'type', 'no type')}"
        )
        print(
            f"DEBUG: Message isinstance(HumanMessage): {isinstance(message, HumanMessage)}"
        )
        # Handle dict vs object access safely
        if isinstance(message, dict):
            msg_content = message.get("content", "no content")
            msg_type = message.get("type", "no type")
        else:
            msg_content = getattr(message, "content", "no content")
            msg_type = getattr(message, "type", "no type")

        print(f"DEBUG: Message content type: {type(msg_content)}")
        print(f"DEBUG: Message content: {msg_content}")
        print(f"DEBUG: Message type: {msg_type}")
        print(
            f"DEBUG: Message dict representation: {message.__dict__ if hasattr(message, '__dict__') else 'no dict'}"
        )

        # Check if it's a human message - use safe msg_type
        is_human = msg_type == "human"

        if is_human:
            print(f"DEBUG: Found human message!")

            # Handle both string content and complex content
            if isinstance(msg_content, str):
                question = msg_content.strip()
                print(f"DEBUG: Extracted question (string): '{question}'")
                return question
            elif isinstance(msg_content, list):
                # Extract text from content blocks
                text_parts = []
                for j, content_block in enumerate(msg_content):
                    print(
                        f"DEBUG: Content block {j}: {content_block} (type: {type(content_block)})"
                    )
                    if isinstance(content_block, dict):
                        if content_block.get("type") == "text":
                            text_parts.append(content_block.get("text", ""))
                        elif "text" in content_block:  # Alternative structure
                            text_parts.append(content_block["text"])
                    elif isinstance(content_block, str):
                        text_parts.append(content_block)

                question = " ".join(text_parts).strip()
                print(f"DEBUG: Extracted question (list): '{question}'")
                return question if question else "Empty question content"
            else:
                print(f"DEBUG: Unknown content type: {type(msg_content)}")
                # Try to convert to string as fallback
                try:
                    question = str(msg_content).strip()
                    print(f"DEBUG: Fallback string conversion: '{question}'")
                    return question
                except:
                    return f"Could not extract content from: {type(msg_content)}"

    print("DEBUG: No human message found")
    return "No human message found in the conversation"


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        messages: list of chat messages (required - provided as input from frontend)
        documents: list of retrieved documents (optional - retrieved during workflow)
        steps: list of processing steps taken (optional - built during workflow)
    """

    messages: List  # Can be BaseMessage objects or dicts
    documents: Optional[List[Document]]
    steps: Optional[List[str]]


def retrieve(state):
    """
    Retrieve documents

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    messages = state["messages"]
    question = extract_question_from_messages(messages)
    steps = state.get("steps", [])

    try:
        documents = retriever.invoke(question)
        print(f"DEBUG: Successfully retrieved {len(documents)} documents")

        # Filter out any documents with None content to prevent validation errors
        valid_documents = []
        for doc in documents:
            if hasattr(doc, "page_content") and doc.page_content is not None:
                valid_documents.append(doc)
            else:
                print(f"DEBUG: Filtered out document with None content: {doc}")

        documents = valid_documents
        print(f"DEBUG: After filtering, {len(documents)} valid documents remain")

    except Exception as e:
        print(f"DEBUG: Document retrieval failed: {str(e)}")
        print(f"DEBUG: Exception type: {type(e)}")
        documents = []  # Return empty list when retrieval fails

    steps.append("retrieve_documents")
    return {"messages": messages, "documents": documents, "steps": steps}


def generate(state):
    """
    Generate answer

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updated state with AI message added to messages
    """

    messages = state["messages"]
    question = extract_question_from_messages(messages)
    documents = state.get("documents", [])
    steps = state.get("steps", [])
    steps.append("generate_answer")

    # Check if no documents are available
    if not documents or len(documents) == 0:
        print("DEBUG: No documents available, returning 'No related document found.'")
        generation = "No related document found."
    else:
        print(f"DEBUG: Generating answer using {len(documents)} documents")
        docs_text = "\n\n".join(d.page_content for d in documents[:10])
        try:
            generation = rag_chain.invoke(
                {"documents": docs_text, "question": question}
            )
        except Exception as e:
            print(f"DEBUG: RAG generation failed: {str(e)}")
            generation = "No related document found."

    # Create AI message with the generated response
    ai_message = AIMessage(content=generation)

    # Add AI message to the messages list
    updated_messages = messages + [ai_message]

    return {
        "messages": updated_messages,
        "documents": documents,
        "steps": steps,
    }


def grade_documents(state):
    """
    Determines whether the retrieved documents are relevant to the question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates documents key with only filtered relevant documents
    """

    messages = state["messages"]
    question = extract_question_from_messages(messages)
    documents = state.get("documents", [])
    steps = state.get("steps", [])
    steps.append("grade_document_retrieval")

    # Handle empty documents list
    if not documents or len(documents) == 0:
        print("DEBUG: No documents to grade, returning empty list")
        return {
            "messages": messages,
            "documents": [],
            "steps": steps,
        }

    filtered_docs = []
    print(f"DEBUG: Grading {len(documents)} documents for relevance")

    for i, d in enumerate(documents):
        try:
            # Ensure document has valid content
            if not d.page_content or d.page_content.strip() == "":
                print(f"DEBUG: Skipping document {i} with empty content")
                continue

            score = retrieval_grader.invoke(
                {"question": question, "documents": d.page_content}
            )
            grade = score.binary_score
            print(f"DEBUG: Document {i} grade: {grade}")
            if grade == "yes":
                filtered_docs.append(d)
        except Exception as e:
            print(f"DEBUG: Failed to grade document {i}: {str(e)}")
            # Continue with other documents instead of failing completely
            continue

    print(f"DEBUG: After grading, {len(filtered_docs)} relevant documents remain")
    return {
        "messages": messages,
        "documents": filtered_docs,
        "steps": steps,
    }


## Web search removed; always proceed from grading to generation


# Graph
workflow = StateGraph(GraphState)

# Define the nodes
workflow.add_node("retrieve", retrieve)  # retrieve
workflow.add_node("grade_documents", grade_documents)  # grade documents
workflow.add_node("generate", generate)  # generatae

# Build graph
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "grade_documents")
workflow.add_edge("grade_documents", "generate")
workflow.add_edge("generate", END)

graph = workflow.compile()
