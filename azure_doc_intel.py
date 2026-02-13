import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv('AZURE_DOC_INTELLIGENCE_ENDPOINT')
key = os.getenv('AZURE_DOC_INTELLIGENCE_KEY')

client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))

def extract_text_from_bytes(file_bytes, mime_type):
    poller = client.begin_analyze_document(
        model_id="prebuilt-read",
        document=file_bytes,
        content_type=mime_type
    )
    result = poller.result()
    text = "\n".join([page.content for page in result.pages])
    return text
