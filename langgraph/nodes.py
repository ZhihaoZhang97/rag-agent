from langchain_core.messages import AIMessage
from utils import format_documents_with_metadata, format_sources_list, extract_question_from_messages


def retrieve(state, retriever):
    """
    Retrieve documents

    Args:
        state (dict): The current graph state
        retriever: The document retriever instance

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    messages = state["messages"]
    # Use current_question if available (from rewrite), otherwise extract from messages
    current_question = state.get("current_question")
    if current_question:
        question = current_question
        # Using rewritten question for retrieval
    else:
        question = extract_question_from_messages(messages)
        # Using original question for retrieval
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
    rewrite_count = state.get("rewrite_count", 0)
    # Preserve current_question if it exists
    current_question = state.get("current_question", question)
    return {
        "messages": messages,
        "documents": documents,
        "steps": steps,
        "rewrite_count": rewrite_count,
        "current_question": current_question
    }


def generate(state, rag_chain):
    """
    Generate answer

    Args:
        state (dict): The current graph state
        rag_chain: The RAG chain for generation

    Returns:
        state (dict): Updated state with AI message added to messages
    """

    messages = state["messages"]
    question = extract_question_from_messages(messages)
    documents = state.get("documents", [])
    steps = state.get("steps", [])
    rewrite_count = state.get("rewrite_count", 0)
    steps.append("generate_answer")

    # Check if no documents are available
    if not documents or len(documents) == 0:
        # Check if we've already tried rewriting
        if rewrite_count > 0:
            print("DEBUG: No documents found after rewriting, returning specialized message")
            generation = "No documents found with user query and agent re-writing, there is likely no related documents in the current vector database."
        else:
            print("DEBUG: No documents available, returning 'No related document found.'")
            generation = "No related document found."
    else:
        print(f"DEBUG: Generating answer using {len(documents)} documents")
        # Format documents with metadata for better LLM processing
        docs_used = documents[:10]  # Store the documents we're actually using
        formatted_docs, filename_to_citation = format_documents_with_metadata(docs_used)
        try:
            generation = rag_chain.invoke(
                {"documents": formatted_docs, "question": question}
            )
            # Append sources list to the generated response
            sources_list = format_sources_list(filename_to_citation)
            generation += sources_list
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
        "rewrite_count": rewrite_count,
        "current_question": state.get("current_question"),
    }


def grade_documents(state, retrieval_grader):
    """
    Determines whether the retrieved documents are relevant to the question.
    Updates the state with filtered relevant documents.

    Args:
        state (dict): The current graph state
        retrieval_grader: The document grading chain

    Returns:
        state (dict): Updated state with filtered documents and routing info
    """

    messages = state["messages"]
    # Use current_question if available (from rewrite), otherwise extract from messages
    current_question = state.get("current_question")
    if current_question:
        question = current_question
    else:
        question = extract_question_from_messages(messages)
    documents = state.get("documents", [])
    steps = state.get("steps", [])
    rewrite_count = state.get("rewrite_count", 0)
    steps.append("grade_document_retrieval")

    # Handle empty documents list
    if not documents or len(documents) == 0:
        print("DEBUG: No documents to grade")
        return {
            "messages": messages,
            "documents": [],
            "steps": steps,
            "rewrite_count": rewrite_count,
            "should_rewrite": True,
            "current_question": current_question,
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
            # Removed debug print to avoid exposing grading info to frontend
            if grade == "yes":
                filtered_docs.append(d)
        except Exception as e:
            print(f"DEBUG: Failed to grade document {i}: {str(e)}")
            # Continue with other documents instead of failing completely
            continue

    print(f"DEBUG: After grading, {len(filtered_docs)} relevant documents remain")

    # Determine if we should rewrite based on document relevance and rewrite count
    should_rewrite = len(filtered_docs) == 0 and rewrite_count < 1

    return {
        "messages": messages,
        "documents": filtered_docs,
        "steps": steps,
        "rewrite_count": rewrite_count,
        "should_rewrite": should_rewrite,
        "current_question": current_question,
    }


def route_after_grading(state):
    """
    Routing function to decide next step after document grading.

    Args:
        state (dict): The current graph state

    Returns:
        str: "generate" or "rewrite" based on document relevance and rewrite count
    """
    should_rewrite = state.get("should_rewrite", False)
    rewrite_count = state.get("rewrite_count", 0)

    # Check if we've already tried rewriting once
    max_rewrites = 1
    if rewrite_count >= max_rewrites:
        print(f"DEBUG: Max rewrite attempts ({max_rewrites}) reached, routing to generate")
        return "generate"

    if should_rewrite:
        print("DEBUG: No relevant documents found, routing to rewrite")
        return "rewrite"
    else:
        print("DEBUG: Relevant documents found, routing to generate")
        return "generate"


def rewrite_question(state, query_rewriter):
    """
    Rewrite the original user question to improve retrieval.
    Keep original messages intact for frontend, store rewritten question internally.

    Args:
        state (dict): The current graph state
        query_rewriter: The query rewriting chain

    Returns:
        state (dict): Updated state with rewritten question stored internally
    """

    messages = state["messages"]
    # Use current_question if available, otherwise extract from messages
    current_question = state.get("current_question")
    if current_question:
        question = current_question
    else:
        question = extract_question_from_messages(messages)

    documents = state.get("documents", [])
    steps = state.get("steps", [])
    rewrite_count = state.get("rewrite_count", 0)
    steps.append("rewrite_question")

    # Increment rewrite count
    rewrite_count += 1

    # Rewriting question internally (not exposed to frontend)

    try:
        rewritten_question = query_rewriter.invoke({"question": question})
        # Rewritten question generated successfully
    except Exception as e:
        print(f"DEBUG: Question rewriting failed: {str(e)}")
        rewritten_question = question  # Fall back to original if rewriting fails

    return {
        "messages": messages,  # Keep original messages unchanged for frontend
        "documents": documents,
        "steps": steps,
        "rewrite_count": rewrite_count,
        "current_question": rewritten_question,  # Store rewritten question internally
    }