from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate

# RAG Chain Prompt
rag_prompt = PromptTemplate(
    template="""You are an assistant for question-answering tasks.
    <task>
    1. Base your answer exclusively on the information within the 'DOCUMENTS' section. Do not use any external knowledge or make assumptions.
    2. You MUST cite sources for every statement. Each document is numbered with [i] and shows its Source filename.
       - Cite using the document number: append `[i]` at the end of each sentence, where `i` is the document number
       - If a sentence is supported by multiple documents, list all indices, like `[2] [5]`
       - You can also reference the source filename for clarity: "According to document.pdf [1], ..."
    3. If the documents do not contain the information needed to answer the enquiry, you MUST explicitly state that you don't know. Do not attempt to guess.
    4. Each document includes its source filename and content. Multiple chunks from the same file may be present with the same filename.
    </task>
    <question>
    Question: {question}
    </question>
    <documents>
    {documents}
    </documents>
    Answer:
    """,
    input_variables=["question", "documents"],
)

# Retrieval Grader System Prompt
grader_system_prompt = """You are a teacher grading a quiz. You will be given:
1/ a QUESTION
2/ a set of comma separated FACTS provided by the student

You are grading RELEVANCE RECALL:
A score of 1 means that ANY of the FACTS are relevant to the QUESTION.
A score of 0 means that NONE of the FACTS are relevant to the QUESTION.
1 is the highest (best) score. 0 is the lowest score you can give.

Explain your reasoning in a step-by-step manner. Ensure your reasoning and conclusion are correct.

Avoid simply stating the correct answer at the outset."""

# Document Grading Prompt
document_grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", grader_system_prompt),
        ("human", "FACTS: \n\n {documents} \n\n QUESTION: {question}"),
    ]
)

# Query Rewriting Prompt
query_rewrite_prompt = PromptTemplate(
    template="""<Task> Look at the input and try to reason about the underlying semantic intent / meaning, then formulate an improved question: </Task>
<question>
{question}
</question>
""",
    input_variables=["question"],
)
