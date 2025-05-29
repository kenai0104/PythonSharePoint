import os
import tempfile
import requests
from msal import PublicClientApplication
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.document import Document


# 🔐 Microsoft App Credentials
CLIENT_ID = "354e1512-776d-47b9-9278-3dc4c5e62e66"
TENANT_ID = "787beb16-0600-4e9e-b636-9993f8d4b23a"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Files.Read.All", "Sites.Read.All"]

# 🌐 SharePoint Info
SHAREPOINT_HOST = "kenaiusa.sharepoint.com"
SITE_NAME = "ATeam"
DOC_LIB_PATH = "SharePoint/Docs1"

# 🔎 Embeddings
EMBEDDINGS_MODEL = "sentence-transformers/all-mpnet-base-v2"
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)


def authenticate():
    """Authenticate via Microsoft Device Code Flow."""
    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise ValueError("❌ Failed to initiate device code flow.")

    print(f"🔐 Go to: {flow['verification_uri']} and enter the code: {flow['user_code']}")
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise Exception(f"❌ Authentication failed: {result.get('error_description')}")

    print("✅ Authentication successful.")
    return result["access_token"]


def fetch_txt_files_from_sharepoint():
    """Download .txt files from SharePoint."""
    token = authenticate()
    headers = {"Authorization": f"Bearer {token}"}

    # ➤ Site ID
    site_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_HOST}:/sites/{SITE_NAME}"
    site_id = requests.get(site_url, headers=headers).json()["id"]

    # ➤ Drive ID
    drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    drive_resp = requests.get(drives_url, headers=headers)
    drive_resp.raise_for_status()
    drive_id = next((d["id"] for d in drive_resp.json()["value"] if d["name"] == "Documents"), None)
    if not drive_id:
        raise Exception("❌ Could not find 'Documents' drive.")

    # ➤ List .txt files
    encoded_path = DOC_LIB_PATH.replace(" ", "%20")
    files_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{encoded_path}:/children"
    files_resp = requests.get(files_url, headers=headers)
    files_resp.raise_for_status()

    docs = []
    for item in files_resp.json().get("value", []):
        if item["name"].endswith(".txt"):
            content_resp = requests.get(item["@microsoft.graph.downloadUrl"])
            content_resp.raise_for_status()
            docs.append(Document(page_content=content_resp.text, metadata={"source": item["name"]}))

    return docs


def index_documents():
    """Index and store documents locally."""
    print("📥 Indexing from SharePoint...")
    documents = fetch_txt_files_from_sharepoint()
    if not documents:
        raise Exception("❌ No .txt files found.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)

    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("./vector_index")
    print("✅ Indexing complete.")


def get_similar_answer_from_documents(query: str):
    """Run similarity search on local FAISS index. Auto-indexes if missing."""
    print(f"🧐 Query received: {query}")

    if not os.path.exists("./vector_index"):
        print("⚠️ Vector index not found. Re-indexing...")
        index_documents()

    try:
        vectorstore = FAISS.load_local("./vector_index", embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        print(f"⚠️ Error loading index: {e}. Rebuilding...")
        index_documents()
        vectorstore = FAISS.load_local("./vector_index", embeddings, allow_dangerous_deserialization=True)

    docs_with_scores = vectorstore.similarity_search_with_score(query, k=3)

    if not docs_with_scores:
        return "❓ I'm sorry, I couldn't find any relevant information.", None

    for doc, score in docs_with_scores:
        if score < 0.6:
            return f"❌ Sorry, we do not offer information on '{query.lower()}' at this time.", None

        return f"🔍 **Answer:** We found information related to '{query.lower()}'.", None

    return f"❌ Sorry, we do not offer information on '{query.lower()}' at this time.", None
