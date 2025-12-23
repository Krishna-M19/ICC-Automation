import gradio as gr
import sys 
import time 
from pathlib import Path 
import tempfile
import shutil
from typing import Tuple


# langchain imports 
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import Chroma
from langchain.retrievers.multi_query import MultiQueryRetriever 
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.schema import Document 
from langchain_community.vectorstores import FAISS
from transformers import AutoTokenizer

TOKENIZER = AutoTokenizer.from_pretrained("google/gemma-3-4b-it", use_fast=True)

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract the text from uploaded PDF"""
    loader = PyPDFLoader(file_path=str(pdf_path))
    docs = loader.load()
    full_text = "\n\n".join(doc.page_content for doc in docs)
    return full_text, len(docs)

def check_token_limit(text: str, max_tokens: int = 128000) -> tuple:
    """for checking if text exceeds token limit"""
    token_ids = TOKENIZER.encode(text, add_special_tokens=False)
    token_count = len(token_ids)
    
    # Check if over the limit
    if token_count > max_tokens:
        truncated_ids = token_ids[:max_tokens]
        truncated_text = TOKENIZER.decode(truncated_ids, skip_special_tokens=True)
        return truncated_text, True, token_count

    return text, False, token_count


def create_direct_review_prompt():
    """Prompt for the No-RAG approach"""
    template = """
                You are a expert grant proposal reviewer. You will receive the COMPLETE text of a research proposal below. Your job is to provide a comprehensive, structured peer review.
PROPOSAL TEXT:
{full_document}

---

Based on the complete proposal above, provide a **STRUCTURED PEER REVIEW** with these exact sections:

## 1. SUMMARY
Provide a concise 4-5 sentence summary of the proposal's main objectives, approach, and significance.

## 2. KEY POINTS 
- List the major strengths and notable aspects in bullet points format 
- Focus on methodology, innovation, feasibility, and potential impact 

## 3. RECOMMENDATIONS 
- List specific weaknesses, concerns, and actionable suggestions for improvment in bullet points format 
- Be constructive and specific about what needs to be addressed

## 4. OVERALL EVALUATION
Provide a final assessment including:
- Overall quality assessment
- Funding recommendation (Strongly Recommend/Recommend/Conditional/Not Recommend)
- Brief justification for your recommendation

Ensure your review is comprehensive, balanced, and professional. Base your analysis on the ENTIRE document provided above.
"""
    return ChatPromptTemplate.from_template(template)

def generate_direct_review(full_text: str, llm: ChatOllama) -> tuple:
    """Generate the proposal review No-RAG approach"""
    start_time = time.time()
    processed_text, was_truncated, token_count = check_token_limit(full_text)
    warning ="Warning: Document was truncated to fit token limits" if was_truncated else ""

    prompt_template = create_direct_review_prompt()
    prompt = prompt_template.format(full_document=processed_text)
    review = llm.invoke(prompt)
    processing_time = time.time() - start_time

    return review.content, warning, token_count, processing_time

def chunk_text(text: str):
    """Chunk the text for RAG approach"""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = [Document(page_content=para) for para in text.split("\n\n")]
    return splitter.split_documents(docs)

def build_vectorstore(chunks):
    """FAISS vector store"""
    #embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    #ll-MiniLM-L6-v2 -> This also works as well but the dimension size is less compared to other. Ofcourse it is lightweight and memory efficient but we have to benchmark it and check the results. May be this will work better when we obtian a model from Huggingface workflow instead.
    embeddings = OllamaEmbeddings(model="nomic-embed-text")  #nomic-embed-text integrates smoothly with Ollama workflow and it scales well for large corpora. 
    db = FAISS.from_documents(
        chunks,
        embeddings,
    )
    return db 

def build_retriever(db, llm, chunks):
    """retriver for RAG approach"""
    query_prompt = PromptTemplate(
        input_variables=["question"],
        template="""You are a expert grant proposal reviewer. You will receive the COMPLETE text of a research proposal below. Your job is to provide a comprehensive, structured peer review.
PROPOSAL TEXT:
        
"Question": {question}        

---
"""
    )
    retriever = MultiQueryRetriever.from_llm(
        db.as_retriever(search_kwargs={"k": len(chunks)}),
        llm, 
        prompt=query_prompt
    )
    return retriever

def build_rag_chain(retriever, llm):
    """Build RAG chain"""
    rag_template = """Here are the most relevant excerpts from a grant proposal:
{context}

Based on the complete proposal above, provide a **STRUCTURED PEER REVIEW** with these exact sections:

## 1. SUMMARY
Provide a concise 4-5 sentence summary of the proposal's main objectives, approach, and significance.

## 2. KEY POINTS 
- List the major strengths and notable aspects in bullet points format 
- Focus on methodology, innovation, feasibility, and potential impact 

## 3. RECOMMENDATIONS 
- List specific weaknesses, concerns, and actionable suggestions for improvment in bullet points format 
- Be constructive and specific about what needs to be addressed

## 4. OVERALL EVALUATION
Provide a final assessment including:
- Overall quality assessment
- Funding recommendation (Strongly Recommend/Recommend/Conditional/Not Recommend)
- Brief justification for your recommendation

Ensure your review is comprehensive, balanced, and professional. Base your analysis on the ENTIRE document provided above.

Question (what to review): {question}
"""
    prompt = ChatPromptTemplate.from_template(rag_template)
    return (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

def generate_rag_review(full_text: str, llm: ChatOllama) -> tuple:
    """Generate review RAG approach"""

    start_time = time.time()
    chunks = chunk_text(full_text)
    vector_db = build_vectorstore(chunks)
    retriever = build_retriever(vector_db, llm, chunks)
    chain = build_rag_chain(retriever, llm)

    user_question = "Provide a full structured review of this grant proposal."
    review = chain.invoke(user_question)
    processing_time = time.time() - start_time

    return review, "", len(chunks), processing_time

def process_pdf(pdf_path_str: str, approach: str) -> Tuple[str, str]:
    """
    Given a path to a PDF (string) and an approach ("RAG" or "No-RAG"),
    run the peer review and return (review_text, metrics_text).
    """
    try:
        llm = ChatOllama(model="gemma3")

        pdf_path = Path(pdf_path_str)
        if not pdf_path.exists():
            return "", f"Error: PDF not found at {pdf_path}"

        full_text, page_count = extract_text_from_pdf(pdf_path)

        if approach == "No-RAG":
            review, warning, token_count, processing_time = generate_direct_review(full_text, llm)
            metrics = (
                f"Approach: No-RAG\n"
                f"Pages Processed: {page_count}\n"
                f"Estimated Tokens: {token_count:,}\n"
                f"Processing Time: {processing_time:.2f} seconds\n"
                f"{warning}"
            )
        else:  # "RAG"
            review, warning, chunk_count, processing_time = generate_rag_review(full_text, llm)
            metrics = (
                f"Approach: RAG\n"
                f"Pages Processed: {page_count}\n"
                f"Chunks Created: {chunk_count}\n"
                f"Processing Time: {processing_time:.2f} seconds\n"
                f"{warning}"
            )

        return review, metrics

    except Exception as e:
        return "", f"Error during processing: {e}"


def main():
    with gr.Blocks(title="Grant Proposal Peer Review Demo") as demo:
        gr.Markdown("# Grant Proposal Peer Review Demo")
        gr.Markdown("Upload a PDF grant proposal and choose an approach (RAG or No-RAG) to generate a structured peer review.")

        with gr.Row():
            pdf_input = gr.File(label="Upload PDF Proposal", file_types=[".pdf"], type="filepath")
            approach_input = gr.Dropdown(choices=["RAG", "No-RAG"], label="Select Approach", value="RAG")

        submit_button = gr.Button("Generate Review", variant="primary")

        with gr.Row():
            review_output = gr.Textbox(label="Generated Peer Review", lines=22)
            metrics_output = gr.Textbox(label="Processing Metrics", lines=10)

        submit_button.click(
            fn=process_pdf,
            inputs=[pdf_input, approach_input],
            outputs=[review_output, metrics_output]
        )

        demo.launch(share=True)


if __name__=="__main__":
    main()
