import os

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

load_dotenv()

docs = []

data_folders = [
    "data/python_docs",
    "data/realpython",
    "data/geeksforgeeks",
    "data/python_stdlib",
    "data/stackoverflow"
]

for folder in data_folders:
    for file in os.listdir(folder):
        if file.endswith(".txt"):

            path = os.path.join(folder, file)
            loader = TextLoader(path, encoding="utf-8")
            documents = loader.load()

            # load correct URL from .url file
            url_path = path.replace(".txt", ".url")
            url = ""

            if os.path.exists(url_path):
                with open(url_path, "r") as f:
                    url = f.read().strip()

            for doc in documents:

                # set clean source name
                if "realpython" in folder:
                    doc.metadata["source"] = "RealPython"

                elif "geeksforgeeks" in folder:
                    doc.metadata["source"] = "GeeksforGeeks"

                elif "python_docs" in folder:
                    doc.metadata["source"] = "Python Docs"

                elif "python_stdlib" in folder:
                    doc.metadata["source"] = "Python StdLib"

                elif "peps" in folder:
                    doc.metadata["source"] = "PEPs"

                elif "stackoverflow" in folder:
                    doc.metadata["source"] = "StackOverflow"

                else:
                    doc.metadata["source"] = "Unknown"

                # attach real URL
                doc.metadata["url"] = url

                # optional
                doc.metadata["file"] = file

            docs.extend(documents)

print("Total documents loaded:", len(docs))

# split documents
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", " "]
)

chunks = splitter.split_documents(docs)

print("Total chunks created:", len(chunks))

# embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Pinecone setup
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = "syntax"

# Upload chunks to Pinecone
vector_store = PineconeVectorStore.from_documents(
    chunks,
    embeddings,
    index_name=index_name
)

print("Vectors uploaded to Pinecone successfully!")
