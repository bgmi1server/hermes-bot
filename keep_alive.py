from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hermes AI Bot - Status</title>
        <style>
            body {
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                text-align: center;
                background: #1e293b;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
                border: 1px solid #334155;
            }
            h1 {
                color: #38bdf8;
                margin-bottom: 10px;
            }
            p {
                font-size: 1.1em;
                color: #94a3b8;
            }
            .status-dot {
                height: 15px;
                width: 15px;
                background-color: #22c55e;
                border-radius: 50%;
                display: inline-block;
                margin-right: 8px;
                box-shadow: 0 0 10px #22c55e;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
                70% { box-shadow: 0 0 0 10px rgba(34, 197, 94, 0); }
                100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Hermes AI Bot</h1>
            <p><span class="status-dot"></span><strong>System Status:</strong> Online & Active</p>
            <p style="font-size: 0.9em; margin-top: 20px;">The background intelligence server is running flawlessly.</p>
        </div>
    </body>
    </html>
    """
    return html_content

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
