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
        <title>Hermes AI | Status</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #0ea5e9;
                --bg-dark: #020617;
                --panel-bg: rgba(15, 23, 42, 0.6);
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
            }
            body {
                background-color: var(--bg-dark);
                background-image: 
                    radial-gradient(at 0% 0%, rgba(14, 165, 233, 0.15) 0px, transparent 50%),
                    radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.15) 0px, transparent 50%);
                color: var(--text-main);
                font-family: 'Inter', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                overflow: hidden;
            }
            .glass-panel {
                background: var(--panel-bg);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 24px;
                padding: 3rem 4rem;
                text-align: center;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
                position: relative;
                max-width: 500px;
                width: 90%;
            }
            .glass-panel::before {
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0; height: 1px;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            }
            h1 {
                margin: 0 0 0.5rem 0;
                font-size: 2.5rem;
                font-weight: 700;
                letter-spacing: -1px;
                background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle {
                color: var(--text-muted);
                font-size: 1.1rem;
                font-weight: 300;
                margin-bottom: 2.5rem;
            }
            .status-badge {
                display: inline-flex;
                align-items: center;
                background: rgba(34, 197, 94, 0.1);
                border: 1px solid rgba(34, 197, 94, 0.2);
                padding: 0.75rem 1.5rem;
                border-radius: 9999px;
                font-weight: 600;
                color: #4ade80;
                letter-spacing: 0.5px;
            }
            .pulse-dot {
                width: 10px;
                height: 10px;
                background-color: #22c55e;
                border-radius: 50%;
                margin-right: 12px;
                box-shadow: 0 0 12px #22c55e;
                animation: pulse-animation 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
            }
            @keyframes pulse-animation {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(1.2); }
            }
            .footer-info {
                margin-top: 3rem;
                font-size: 0.85rem;
                color: #64748b;
                display: flex;
                justify-content: space-between;
                border-top: 1px solid rgba(255,255,255,0.05);
                padding-top: 1.5rem;
            }
        </style>
    </head>
    <body>
        <div class="glass-panel">
            <h1>Hermes Core</h1>
            <div class="subtitle">Next-Generation AI Aggregator</div>
            
            <div class="status-badge">
                <div class="pulse-dot"></div>
                SYSTEM ONLINE
            </div>
            
            <div class="footer-info">
                <span>Location: Cloud</span>
                <span>Latency: < 50ms</span>
            </div>
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
