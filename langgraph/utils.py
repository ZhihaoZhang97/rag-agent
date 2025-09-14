from langchain_core.messages import HumanMessage


def format_documents_with_metadata(documents) -> tuple[str, dict]:
    """
    Format documents with metadata for LLM processing.
    Groups documents by filename and assigns consistent citation numbers.

    Args:
        documents: List of Document objects with metadata

    Returns:
        tuple: (formatted_string, filename_to_citation_mapping)
    """
    if not documents:
        return "No documents available.", {}

    # Create filename to citation number mapping
    filename_to_citation = {}
    citation_counter = 1

    # First pass: assign citation numbers to unique filenames
    for doc in documents:
        metadata = getattr(doc, 'metadata', {})
        filename = metadata.get('filename', 'Unknown source')
        if filename not in filename_to_citation:
            filename_to_citation[filename] = citation_counter
            citation_counter += 1

    # Second pass: format documents with consistent citation numbers
    formatted_docs = []
    for doc in documents:
        metadata = getattr(doc, 'metadata', {})
        filename = metadata.get('filename', 'Unknown source')
        citation_num = filename_to_citation[filename]

        # Format document with consistent citation number
        formatted_doc = f"[{citation_num}] Source: {filename}\nContent: {doc.page_content}\n"
        formatted_docs.append(formatted_doc)

    return "\n".join(formatted_docs), filename_to_citation


def format_sources_list(filename_to_citation) -> str:
    """
    Format a sources list to append to the AI message.

    Args:
        filename_to_citation: Dict mapping filename to citation number

    Returns:
        str: Formatted sources list with [index]: filename per line
    """
    if not filename_to_citation:
        return ""

    # Sort by citation number to maintain consistent order
    sorted_sources = sorted(filename_to_citation.items(), key=lambda x: x[1])
    sources = [f"[{citation_num}]: {filename}" for filename, citation_num in sorted_sources]

    return "\n\nSources:\n" + "\n".join(sources)


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