"""
PDF Q&A Agent - Extracts text from PDFs and images.

Uses pypdf for PDF extraction and LLM for image-based JD parsing.
Adapted from user's LlamaIndex agent to work within Applyr pipeline.
"""
import os
import sys
import re
import logging
from typing import Optional, Dict, Any

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import get_llm, chat, parse_json_response

logger = logging.getLogger(__name__)


class PDFQAAgent:
    """Extracts job descriptions from PDF/image files.

    Pipeline interface: orchestrator calls extract methods directly.
    """

    def __init__(self):
        pass

    def extract_jd_from_pdf(self, pdf_path: str) -> str:
        """Extract job description text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text content
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return ""

        try:
            import pypdf
            with open(pdf_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                text = "\n".join(
                    page.extract_text() or "" for page in reader.pages
                )
            logger.info(f"Extracted {len(text)} chars from PDF: {pdf_path}")
            return text.strip()
        except ImportError:
            logger.error("pypdf not installed. Run: pip install pypdf")
            return ""
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return ""

    def extract_jd_from_image(self, image_path: str) -> str:
        """Extract job description text from image using LLM vision or OCR.

        Args:
            image_path: Path to image file (PNG, JPG)

        Returns:
            Extracted text content
        """
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return ""

        # Try pytesseract OCR first
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            if text.strip():
                logger.info(f"OCR extracted {len(text)} chars from image")
                return text.strip()
        except ImportError:
            logger.warning("pytesseract not available, using LLM fallback")
        except Exception as e:
            logger.warning(f"OCR failed: {e}")

        # Fallback: read image and describe via LLM prompt
        return f"[Image-based JD from: {image_path} - OCR not available. Please install pytesseract.]"

    def extract_jd_from_url(self, url: str) -> str:
        """Extract job description from a URL.

        Args:
            url: URL of job posting

        Returns:
            Extracted JD text
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)

            # Use LLM to extract just the JD from the page text
            if len(text) > 500:
                jd = chat(
                    prompt=f"Extract ONLY the job description from this webpage text. "
                           f"Return the job title, company, requirements, and responsibilities:\n\n{text[:3000]}",
                    system_prompt="You are a job description extractor. Return only the relevant job posting content.",
                    temperature=0
                )
                return jd
            return text

        except Exception as e:
            logger.error(f"URL extraction failed: {e}")
            return ""

    def extract_hr_contact_info(self, jd_text: str) -> Dict[str, str]:
        """Extract HR contact info from JD text.

        Args:
            jd_text: Full job description text

        Returns:
            Dict with hr_email, hr_phone, apply_url
        """
        result = {"hr_email": "", "hr_phone": "", "apply_url": ""}

        if not jd_text:
            return result

        # Regex extraction
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', jd_text)
        phones = re.findall(r'[\+]?[\d]{1,3}[-.\s]?[\d]{3,4}[-.\s]?[\d]{3,4}[-.\s]?[\d]{0,4}', jd_text)
        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', jd_text)

        if emails:
            result["hr_email"] = emails[0]
        if phones:
            result["hr_phone"] = phones[0]
        if urls:
            # Prefer apply/career URLs
            apply_urls = [u for u in urls if any(kw in u.lower() for kw in ["apply", "career", "jobs", "greenhouse", "lever"])]
            result["apply_url"] = apply_urls[0] if apply_urls else urls[0]

        return result

    def analyze_jd(self, jd_text: str) -> Dict[str, Any]:
        """Use LLM to analyze a job description and extract structured data.

        Args:
            jd_text: Raw job description text

        Returns:
            Structured job data dict
        """
        if not jd_text or len(jd_text) < 30:
            return {}

        try:
            response = chat(
                prompt=f"Analyze this job description:\n\n{jd_text[:2000]}",
                system_prompt="""Extract job details and return JSON:
{
  "title": "Job Title",
  "company": "Company Name",
  "location": "Location",
  "salary": "Salary range or empty",
  "requirements": ["req1", "req2"],
  "skills_needed": ["skill1", "skill2"],
  "experience_years": "X+ years or empty",
  "job_type": "full-time|part-time|contract|internship",
  "apply_method": "email|url|form",
  "hr_email": "email or empty"
}
Return only valid JSON.""",
                temperature=0
            )
            return parse_json_response(response)
        except Exception as e:
            logger.error(f"JD analysis failed: {e}")
            return {}


# ─── Standalone CLI ─────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="PDF Q&A Agent")
    parser.add_argument("--pdf", help="Path to PDF file")
    parser.add_argument("--image", help="Path to image file")
    parser.add_argument("--url", help="URL of job posting")
    parser.add_argument("--text", help="Plain text JD")
    args = parser.parse_args()

    agent = PDFQAAgent()

    if args.pdf:
        text = agent.extract_jd_from_pdf(args.pdf)
    elif args.image:
        text = agent.extract_jd_from_image(args.image)
    elif args.url:
        text = agent.extract_jd_from_url(args.url)
    elif args.text:
        text = args.text
    else:
        print("Usage: python pdf_qa_agent.py --pdf <file> | --image <file> | --url <url>")
        return

    print(f"\n📄 Extracted text ({len(text)} chars):\n")
    print(text[:500])

    if text:
        print("\n" + "=" * 60)
        info = agent.extract_hr_contact_info(text)
        print(f"📧 HR Email: {info.get('hr_email', 'Not found')}")
        print(f"📞 Phone: {info.get('hr_phone', 'Not found')}")
        print(f"🔗 Apply URL: {info.get('apply_url', 'Not found')}")

        analysis = agent.analyze_jd(text)
        if analysis:
            print(f"\n📊 Job Title: {analysis.get('title', 'N/A')}")
            print(f"🏢 Company: {analysis.get('company', 'N/A')}")
            print(f"📍 Location: {analysis.get('location', 'N/A')}")


if __name__ == "__main__":
    main()
