"""
PDF Q&A Agent — AutoApply AI
Loads a PDF (JD, resume, or any doc), indexes it, and answers questions.
In pipeline mode: extracts structured job info from an uploaded JD PDF.

Fixes vs original:
  - Replaced OpenAI with Groq via llama-index-llms-groq
  - Replaced OpenAI embeddings with HuggingFace local embeddings (free, no key)
  - Added pipeline mode: extract_jd_info() for orchestrator use
  - Added --jd flag for one-shot JD extraction

Usage:
    # Interactive Q&A on any PDF
    python 03_pdf_qa_agent.py --pdf ./uploads/jd_pdfs/stripe_sde.pdf

    # Single question
    python 03_pdf_qa_agent.py --pdf doc.pdf --question "What skills are required?"

    # Pipeline mode: extract structured JD info (used by orchestrator)
    python 03_pdf_qa_agent.py --pdf ./uploads/jd_pdfs/stripe_sde.pdf --jd

Install:
    pip install llama-index llama-index-llms-groq llama-index-embeddings-huggingface
"""

import argparse
import json
import os

from dotenv import load_dotenv
from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq

load_dotenv()


# ── LLM + Embeddings setup ────────────────────────────────────────────────────
def get_llm() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    model   = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found in .env\n"
            "Get your free key at https://console.groq.com"
        )

    return Groq(
        model=model,
        api_key=api_key,
        temperature=0,
    )


def configure_settings():
    """
    Wire Groq as the LLM and HuggingFace as the embedding model.
    HuggingFace embeddings run locally — no API key, no cost.
    """
    Settings.llm = get_llm()
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-en-v1.5"  # small, fast, free
    )
    Settings.chunk_size    = 512
    Settings.chunk_overlap = 50


# ── Index builder ─────────────────────────────────────────────────────────────
def build_index(pdf_path: str) -> VectorStoreIndex:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    configure_settings()

    print(f"[pdf_qa] Loading: {pdf_path}")
    reader = SimpleDirectoryReader(input_files=[pdf_path])
    docs   = reader.load_data()
    index  = VectorStoreIndex.from_documents(docs)
    print(f"[pdf_qa] Indexed {len(docs)} chunk(s)")
    return index


# ── Pipeline mode: extract structured JD ─────────────────────────────────────
def extract_jd_info(pdf_path: str) -> dict:
    """
    Used by the orchestrator when a user uploads a JD PDF manually.
    Returns a structured dict matching the jobs table schema in applications.db.
    """
    index        = build_index(pdf_path)
    query_engine = index.as_query_engine(similarity_top_k=5)

    extraction_prompt = """
Extract the following information from this job description.
Return ONLY a valid JSON object with these exact keys — no extra text:

{
  "title": "Job title",
  "company": "Company name",
  "location": "City, country or Remote",
  "type": "fulltime or internship or contract",
  "hr_email": "HR/apply email if present, else null",
  "apply_url": "Application URL if present, else null",
  "description_snippet": "2-3 sentence summary of the role",
  "required_skills": ["skill1", "skill2", "skill3"],
  "nice_to_have_skills": ["skill1", "skill2"],
  "experience_years": "e.g. 2-4 years or null",
  "salary": "salary range if mentioned, else null",
  "source": "uploaded_pdf"
}
"""

    response = query_engine.query(extraction_prompt)
    raw      = response.response.strip()

    # Strip markdown fences if LLM adds them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
        print(f"[pdf_qa] Extracted JD: {result.get('title')} at {result.get('company')}")
        return result
    except json.JSONDecodeError:
        print(f"[pdf_qa] Warning: could not parse JSON, returning raw text")
        return {
            "title": None,
            "company": None,
            "description_snippet": raw,
            "source": "uploaded_pdf",
            "raw_extraction": raw,
        }


# ── Single question mode ──────────────────────────────────────────────────────
def single_question(index: VectorStoreIndex, question: str) -> str:
    query_engine = index.as_query_engine(similarity_top_k=5)
    response     = query_engine.query(question)

    print("\n" + "=" * 60)
    print("📋 ANSWER")
    print("=" * 60)
    print(response.response)

    if hasattr(response, "source_nodes"):
        print(f"\n📚 {len(response.source_nodes)} chunk(s) referenced")

    return response.response


# ── Interactive mode ──────────────────────────────────────────────────────────
def interactive_qa(index: VectorStoreIndex):
    memory = ChatMemoryBuffer.from_defaults(token_limit=4096)
    chat_engine = index.as_chat_engine(
        chat_mode="context",
        memory=memory,
        verbose=False,
    )
    # Settings.llm is already Groq — chat engine picks it up automatically

    print("\n💬 PDF Q&A ready. Ask anything about this document.")
    print("    Type 'quit' to exit.\n")

    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            print("[pdf_qa] Session ended.")
            break
        if not question:
            continue

        response = chat_engine.chat(question)
        print(f"\nAgent: {response.response}\n")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AutoApply — PDF Q&A Agent")
    parser.add_argument("--pdf",      required=True, help="Path to PDF file")
    parser.add_argument("--question", default=None,  help="Single question (skip for interactive)")
    parser.add_argument("--jd",       action="store_true",
                        help="Pipeline mode: extract structured job info from JD PDF")
    args = parser.parse_args()

    # ── Pipeline / JD extraction mode ─────────────────────────────────────────
    if args.jd:
        print(f"\n📄 Extracting job info from: {args.pdf}\n")
        result = extract_jd_info(args.pdf)
        print("\n" + "=" * 60)
        print("📋 EXTRACTED JOB INFO")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        return result

    # ── Build index for Q&A modes ──────────────────────────────────────────────
    index = build_index(args.pdf)

    # ── Single question mode ───────────────────────────────────────────────────
    if args.question:
        single_question(index, args.question)

    # ── Interactive mode ───────────────────────────────────────────────────────
    else:
        interactive_qa(index)


if __name__ == "__main__":
    main()