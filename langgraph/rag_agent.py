from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
import os
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.dashscope import DashScopeEmbeddings
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from dotenv import load_dotenv
from prompt import rag_prompt, document_grade_prompt, query_rewrite_prompt
from state import GraphState
from nodes import retrieve as retrieve_node, generate as generate_node, grade_documents as grade_documents_node, route_after_grading, rewrite_question as rewrite_question_node

load_dotenv()

### LLM
model = "gpt-4o"
llm = ChatOpenAI(model_name=model, temperature=0)

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

# Query Rewriter
query_rewriter = query_rewrite_prompt | llm | StrOutputParser()

# Wrapper functions to inject dependencies
def retrieve(state):
    return retrieve_node(state, retriever)


def generate(state):
    return generate_node(state, rag_chain)


def grade_documents(state):
    return grade_documents_node(state, retrieval_grader)


def rewrite_question(state):
    return rewrite_question_node(state, query_rewriter)


# Graph
workflow = StateGraph(GraphState)

# Define the nodes
workflow.add_node("retrieve", retrieve)  # retrieve
workflow.add_node("grade_documents", grade_documents)  # grade documents
workflow.add_node("generate", generate)  # generate
workflow.add_node("rewrite_question", rewrite_question)  # rewrite question

# Build graph
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "grade_documents")

# Add conditional edges based on document grading
workflow.add_conditional_edges(
    "grade_documents",
    route_after_grading,
    {
        "generate": "generate",
        "rewrite": "rewrite_question",
    },
)

# After rewriting, go back to retrieve with the new question
workflow.add_edge("rewrite_question", "retrieve")
workflow.add_edge("generate", END)

graph = workflow.compile()
