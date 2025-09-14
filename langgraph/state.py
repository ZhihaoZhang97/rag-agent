from typing import List, Optional
from typing_extensions import TypedDict
from langchain.schema import Document


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        messages: list of chat messages (required - provided as input from frontend)
        documents: list of retrieved documents (optional - retrieved during workflow)
        steps: list of processing steps taken (optional - built during workflow)
        rewrite_count: number of times the query has been rewritten (optional - tracks rewrites)
        should_rewrite: boolean indicating if query should be rewritten (optional - for routing)
        current_question: current question being used for retrieval (optional - internal working question)
    """

    messages: List  # Can be BaseMessage objects or dicts
    documents: Optional[List[Document]]
    steps: Optional[List[str]]
    rewrite_count: Optional[int]
    should_rewrite: Optional[bool]
    current_question: Optional[str]