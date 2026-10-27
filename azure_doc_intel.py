import os
import io
import logging
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentContentFormat
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

endpoint = os.getenv('AZURE_DOC_INTELLIGENCE_ENDPOINT')
key = os.getenv('AZURE_DOC_INTELLIGENCE_KEY')

_client = None

def get_client():
    global _client
    if _client is None and endpoint and key:
        try:
            _client = DocumentIntelligenceClient(endpoint.rstrip("/"), AzureKeyCredential(key))
        except Exception as e:
            logger.error(f"Failed to initialize DocumentIntelligenceClient: {e}")
            _client = None
    return _client


def extract_text_from_bytes(file_bytes: bytes, mime_type: str) -> str:
    """
    Extracts high-fidelity structured text and markdown from documents (PDFs, images)
    using Azure Document Intelligence 'prebuilt-layout'.
    Preserves tables, checkboxes, and reading order.
    """
    client = get_client()
    if client:
        try:
            poller = client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=file_bytes,
                content_type=mime_type,
                output_content_format=DocumentContentFormat.MARKDOWN
            )
            result = poller.result()
            if result and result.content:
                logger.info(f"ADI prebuilt-layout extracted {len(result.content)} chars of markdown.")
                return result.content
        except Exception as e:
            logger.warning(f"ADI prebuilt-layout analysis failed: {e}. Attempting fallback...")

    # Fallback for PDFs if ADI service is unavailable or credentials need refresh
    if mime_type == 'application/pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = [page.extract_text() or '' for page in reader.pages]
            extracted = "\n\n".join(pages_text).strip()
            if extracted:
                logger.info(f"PDF fallback extracted {len(extracted)} chars.")
                return extracted
        except Exception as fallback_err:
            logger.error(f"PDF fallback failed: {fallback_err}")

    return None

