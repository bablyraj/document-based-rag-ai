from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from typing import List, Dict
import os
from datetime import datetime
import uuid
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import PyPDFLoader
from langchain.prompts import PromptTemplate
from langchain.callbacks.base import BaseCallbackHandler

# Initialising FastAPI 
app = FastAPI(title="RAG AI Assistant Backend")

# Enable CORS for Flask frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage
vector_stores: Dict[str, Chroma] = {}
documents_metadata: List[Dict] = []
UPLOAD_DIR = "uploaded_pdfs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

load_dotenv()

# WebSocket streaming callback
class WebSocketStreamCallback(BaseCallbackHandler):
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        
    async def llm_new_token(self, token: str, **kwargs) -> None:
        try:
            await self.websocket.send_json({
                "type": "token",
                "content": token
            })
        except:
            pass

# Process PDF function
async def process_pdf(file: UploadFile, user_id: str, api_key: str) -> Dict:
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    print("File path: "+file_path, flush=True)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        print("Content:", flush=True)
        f.write(content)
    
    try:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        print("Documents:", flush=True)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)
        print("Chunks:", flush=True)
        for chunk in chunks:
            chunk.metadata['source'] = file.filename
            chunk.metadata['upload_time'] = datetime.now().isoformat()
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=api_key
        )
        
        if user_id not in vector_stores:
            vector_stores[user_id] = Chroma(
                embedding_function=embeddings,
                collection_name=f"user_{user_id}"
            )
        print("Vector store: ", flush=True)
        vector_stores[user_id].add_documents(chunks)
        print("Vector store after adding documents: ", flush=True)
        
        doc_metadata = {
            "id": str(uuid.uuid4()),
            "filename": file.filename,
            "size": len(content),
            "chunks": len(chunks),
            "upload_time": datetime.now().isoformat(),
            "user_id": user_id
        }
        documents_metadata.append(doc_metadata)
        
        return {
            "success": True,
            "metadata": doc_metadata
        }
    except Exception as e:
        print("Exception: ", e, flush=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# API Endpoints
@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    user_id = "default"
    print(user_id, flush=True)
    api_key = os.environ.get("GOOGLE_API_KEY")
    print(api_key, flush=True)
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    result = await process_pdf(file, user_id, api_key)
    print(result, flush=True)
    return result

@app.get("/api/documents")
async def get_documents():
    return {"documents": documents_metadata}

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    global documents_metadata
    documents_metadata = [d for d in documents_metadata if d['id'] != doc_id]
    return {"success": True}

# WebSocket endpoint
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    user_id = "default"
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message['type'] == 'question':
                question = message['content']
                api_key = os.environ.get("GOOGLE_API_KEY")
                
                if user_id not in vector_stores:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Please upload documents first"
                    })
                    continue
                
                try:
                    stream_callback = WebSocketStreamCallback(websocket)
                    
                    llm = ChatGoogleGenerativeAI(
                        model="gemini-2.5-pro",
                        google_api_key=api_key,
                        streaming=True,
                        callbacks=[stream_callback],
                        temperature=0.7,
                        convert_system_message_to_human=True
                    )
                    
                    prompt_template = """Use the following context to answer the question.
                    Cite source documents when providing information.

                    Context: {context}

                    Question: {question}

                    Answer: (in clean Markdown with proper line breaks and bullet points.)"""
                    
                    PROMPT = PromptTemplate(
                        template=prompt_template,
                        input_variables=["context", "question"]
                    )
                    
                    qa_chain = RetrievalQA.from_chain_type(
                        llm=llm,
                        chain_type="stuff",
                        retriever=vector_stores[user_id].as_retriever(
                            search_kwargs={"k": 3}
                        ),
                        chain_type_kwargs={"prompt": PROMPT},
                        return_source_documents=True
                    )
                    
                    result = await asyncio.to_thread(
                        qa_chain.invoke,
                        {"query": question}
                    )
                    
                    sources = list(set([doc.metadata['source'] 
                                      for doc in result['source_documents']]))
                    
                    await websocket.send_json({
                        "type": "answer",
                        "answer": result['result']
                    })
                    
                    await websocket.send_json({
                        "type": "sources",
                        "sources": sources
                    })
                    
                    await websocket.send_json({"type": "complete"})
                    
                except Exception as e:
                    print("Exception: ", e, flush=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
    
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI Backend on http://localhost:8000", flush=True)
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)