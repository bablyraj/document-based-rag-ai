from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        }

        .container {
            width: 100vw;
            margin: 0 auto;
            background: white;
            overflow: hidden;
            display: grid;
            grid-template-columns: 350px 1fr;
            height: 100vh;
        }

        .sidebar {
            background: rgb(240, 242, 246);
            padding: 30px;
            color: #000000;
            overflow-y: auto;
        }

        .sidebar h1 {
            font-size: 24px;
            margin-bottom: 10px;
        }

        .sidebar p {
            font-size: 14px;
        }

        .api-section {
            background: #0f3460;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        .api-section h3 {
            font-size: 14px;
            margin-bottom: 10px;
            color: #4285f4;
        }

        .api-section input {
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 5px;
            background: #1a1a2e;
            color: white;
            font-size: 14px;
        }

        .api-section button {
            width: 100%;
            margin-top: 10px;
            padding: 10px;
            border: none;
            border-radius: 5px;
            background: #4285f4;
            color: white;
            font-weight: 600;
            cursor: pointer;
        }

        .api-section button:hover {
            background: #1967d2;
        }

        .upload-section {
            background: rgba(28, 131, 225, 0.1);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        .upload-section h3 {
            font-size: 14px;
            margin-bottom: 10px;
            color: rgb(0, 66, 128);
        }

        .upload-btn {
            width: 100%;
            padding: 12px;
            border: 2px dashed rgb(0, 66, 128);
            border-radius: 5px;
            background: transparent;
            color: rgb(0, 66, 128);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .upload-btn:hover {
            background: rgba(66, 133, 244, 0.1);
        }

        .documents {
            background: rgba(28, 131, 225, 0.1);
            padding: 20px;
            border-radius: 10px;
            max-height: 300px;
            overflow-y: auto;
        }

        .documents h3 {
            font-size: 14px;
            margin-bottom: 10px;
            color: rgb(0, 66, 128);
        }

        .doc-item {
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 12px;
            border-radius: 5px;
        }

        .doc-item h4 {
            font-size: 13px;
            margin-bottom: 5px;
        }

        .doc-item p {
            font-size: 11px;
            color: #808080;
        }

        .chat-area {
            display: flex;
            flex-direction: column;
            background: #FFFFFF;
            overflow: scroll;
        }

        .chat-header {
            background: white;
            padding: 20px 30px;
            border-bottom: 1px solid #e0e0e0;
        }

        .chat-header h2 {
            font-size: 20px;
            color: #000000;
        }

        .messages {
            flex: 1;
            padding: 30px;
            overflow-y: auto;
        }

        .message {
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
        }

        .message.user {
            flex-direction: row-reverse;
        }

        .message-content {
            max-width: 70%;
            padding: 15px 20px;
            border-radius: 15px;
            line-height: 1.5;
        }

        .message.user .message-content {
            background: rgba(28, 131, 225, 0.1);
            color: #31333F;
        }

        .message.assistant .message-content {
            background: rgba(240, 242, 246, 0.5);
            color: #31333F;
        }

        .sources {
            font-size: 12px;
            color: #666;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #e0e0e0;
        }

        .input-area {
            padding: 20px 30px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }

        .input-wrapper {
            display: flex;
            gap: 10px;
        }

        .input-wrapper input {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 14px;
        }

        .input-wrapper input:focus {
            outline: none;
            border-color: #4285f4;
        }

        .input-wrapper button {
            padding: 15px 30px;
            background: rgb(0, 66, 128);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
        }

        .input-wrapper button:hover {
            opacity: 0.8;
        }

        .empty-state {
            display: flex;
            height: 100%;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 12px;
            text-align: center;
            color: #000000;
            padding: 50px;
        }

        .status {
            font-size: 12px;
            color: #4285f4;
            margin-top: 10px;
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>RAG AI Assistant</h1>
            <br />
            <div class="upload-section">
                <h3>Upload Documents</h3>
                <input type="file" id="fileInput" multiple accept=".pdf" style="display:none" onchange="uploadFiles()">
                <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                    Choose PDF Files
                </button>
                <div class="status" id="uploadStatus"></div>
            </div>

            <div class="documents">
                <h3>Documents (<span id="docCount">0</span>)</h3>
                <div id="documentsList"></div>
            </div>
        </div>

        <div class="chat-area">
            <div class="chat-header">
                <h2>Chat</h2>
            </div>

            <div class="messages" id="messages">
                <div class="empty-state">
                    <h3>Welcome!</h3>
                    <p>Upload PDF documents and start asking questions</p>
                </div>
            </div>

            <div class="input-area">
                <div class="input-wrapper">
                    <input type="text" id="questionInput" placeholder="Ask a question about your documents..." onkeypress="if(event.key==='Enter') askQuestion()">
                    <button onclick="askQuestion()">Send</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const BACKEND_URL = 'http://localhost:8000';
        let ws = null;
        let apiKey = '';

        function setApiKey() {
            apiKey = document.getElementById('apiKey').value;
            if (apiKey) {
                fetch(`${BACKEND_URL}/api/set-api-key`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({api_key: apiKey})
                });
                document.getElementById('apiStatus').textContent = '✓ API Key saved';
                setTimeout(() => document.getElementById('apiStatus').textContent = '', 3000);
            }
        }

        async function uploadFiles() {
            const files = document.getElementById('fileInput').files;
            const status = document.getElementById('uploadStatus');
            status.textContent = 'Uploading...';

            for (let file of files) {
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch(`${BACKEND_URL}/api/upload`, {
                        method: 'POST',
                        body: formData
                    });
                    const result = await response.json();
                    
                    if (result.success) {
                        addDocumentToList(result.metadata);
                        status.textContent = '✓ Upload complete!';
                    }
                } catch (error) {
                    status.textContent = '✗ Upload failed';
                }
            }

            document.getElementById('fileInput').value = '';
            setTimeout(() => status.textContent = '', 3000);
        }

        function addDocumentToList(doc) {
            const list = document.getElementById('documentsList');
            const div = document.createElement('div');
            div.className = 'doc-item';
            div.innerHTML = `
                <h4>${doc.filename}</h4>
                <p>${(doc.size / 1024).toFixed(1)} KB • ${doc.chunks} chunks</p>
            `;
            list.appendChild(div);
            
            const count = document.getElementById('docCount');
            count.textContent = parseInt(count.textContent) + 1;
        }

        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8000/ws/chat');
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'token') {
                    appendToLastMessage(data.content);
                } else if (data.type === 'sources') {
                    addSources(data.sources);
                } else if (data.type === 'answer') {
                    addMessage('assistant', data.answer);
                } else if (data.type === 'complete') {
                    markComplete();
                } else if (data.type === 'error') {
                    addMessage('assistant', 'Error: ' + data.message);
                }
            };

            ws.onerror = () => {
                addMessage('system', 'Connection error. Refresh page.');
            };
        }

        function askQuestion() {
            const input = document.getElementById('questionInput');
            const question = input.value.trim();
            
            if (!question) return;

            if (!ws || ws.readyState !== WebSocket.OPEN) {
                connectWebSocket();
                setTimeout(() => askQuestion(), 1000);
                return;
            }

            addMessage('user', question);
            addMessage('assistant', 'Thinking...');

            ws.send(JSON.stringify({
                type: 'question',
                content: question
            }));

            input.value = '';
        }

        function addMessage(role, content) {
            const messages = document.getElementById('messages');
            const empty = messages.querySelector('.empty-state');
            if (empty) empty.remove();

            const div = document.createElement('div');
            div.className = `message ${role}`;
            if(role === 'assistant') {
                const prevMsg = messages.querySelector('.message.assistant:last-child');
                if (prevMsg) {
                    prevMsg.remove();
                } 
                const html = marked.parse(content);
                div.innerHTML = `
                <div class="message-content">
                    ${html}
                </div>`;
            } else {
                div.innerHTML = `
                <div class="message-content">
                    <div class="text">${content || '<span style="color:#ccc">...</span>'}</div>
                </div>
                `;
            }
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        function appendToLastMessage(token) {
            const messages = document.getElementById('messages');
            const lastMsg = messages.querySelector('.message.assistant:last-child .text');
            if (lastMsg) {
                if (lastMsg.textContent === '...') {
                    lastMsg.textContent = token;
                } else {
                    lastMsg.textContent += token;
                }
                messages.scrollTop = messages.scrollHeight;
            }
        }

        function addSources(sources) {
            const messages = document.getElementById('messages');
            const lastMsg = messages.querySelector('.message.assistant:last-child .message-content');
            if (lastMsg && sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'sources';
                sourcesDiv.textContent = '📚 Sources: ' + sources.join(', ');
                lastMsg.appendChild(sourcesDiv);
            }
        }

        function markComplete() {
            // Message is complete
        }

        connectWebSocket();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    print("Starting Flask Frontend on http://localhost:3000")
    app.run(host='0.0.0.0', port=3000, debug=True)