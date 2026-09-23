from flask import Flask, send_from_directory
from threading import Thread
import os

app = Flask(__name__)
WORKSPACE_DIR = os.path.join(os.getcwd(), "agent_workspace")

@app.route('/preview/<path:filename>')
def serve_preview(filename):
    """Serve generated files directly from the agent_workspace."""
    if not os.path.exists(WORKSPACE_DIR):
        return "Workspace directory not found. Please run Claude first.", 404
    return send_from_directory(WORKSPACE_DIR, filename)

@app.route('/')
def home():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hermes AI | Status</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;500;700&display=swap" rel="stylesheet">
    <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
    <style>
        :root {
            --primary: #ff3366;    /* Vibrant Coral/Rose */
            --secondary: #4361ee;  /* Deep Sapphire Blue */
            --tertiary: #4cc9f0;   /* Bright Cyan */
            --bg: #030305;         /* Ultra dark obsidian */
        }
        body {
            background-color: transparent;
            color: #fff;
            font-family: 'Space Grotesk', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            margin: 0;
            perspective: 1000px;
        }
        
        .app-bg {
            background-color: var(--bg);
            background-image: 
                radial-gradient(circle at 100% 0%, rgba(67, 97, 238, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 0% 100%, rgba(255, 51, 102, 0.1) 0%, transparent 50%);
            border-radius: 28px;
            width: 100%;
            height: 400px;
            max-width: 600px;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 0 50px rgba(112, 0, 255, 0.2);
            border: 1px solid rgba(255,255,255,0.05);
        }

        /* Canvas for Neural Network Particles */
        #neural-canvas {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
        }

        /* 3D Floating Glass Card */
        .glass-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-top: 1px solid rgba(255, 255, 255, 0.3);
            border-left: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 28px;
            padding: 3rem;
            text-align: center;
            z-index: 10;
            width: 80%;
            transform-style: preserve-3d;
            transform: translateZ(50px);
            box-shadow: 0 30px 60px rgba(0,0,0,0.8), inset 0 0 20px rgba(255,255,255,0.05);
            transition: transform 0.1s ease;
        }

        .title-wrapper {
            transform: translateZ(30px);
        }

        h1 {
            margin: 0;
            font-size: 3rem;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
            background: linear-gradient(120deg, #ffffff 0%, #e0e0e0 40%, var(--primary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 40px rgba(255, 51, 102, 0.2);
        }

        .subtitle {
            color: #94a3b8;
            font-size: 1rem;
            letter-spacing: 5px;
            text-transform: uppercase;
            margin-top: 0.5rem;
            margin-bottom: 2.5rem;
            transform: translateZ(20px);
        }

        .status-container {
            transform: translateZ(50px);
            display: inline-block;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 0.85rem 1.75rem;
            border-radius: 12px;
            font-weight: 700;
            color: #f8fafc;
            letter-spacing: 2px;
            text-transform: uppercase;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }

        .core-pulse {
            width: 12px;
            height: 12px;
            background: var(--tertiary);
            border-radius: 50%;
            margin-right: 15px;
            box-shadow: 0 0 15px var(--tertiary), 0 0 30px var(--tertiary);
            animation: core-beat 2s ease-in-out infinite alternate;
        }

        @keyframes core-beat {
            0% { transform: scale(0.8); opacity: 0.6; }
            100% { transform: scale(1.2); opacity: 1; box-shadow: 0 0 25px var(--tertiary), 0 0 50px var(--tertiary); }
        }

        /* Ambient glowing orbs */
        .orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            z-index: 0;
            opacity: 0.7;
            animation: float 12s infinite ease-in-out alternate;
        }
        .orb-1 {
            width: 350px; height: 350px;
            background: var(--primary);
            top: -100px; left: -100px;
        }
        .orb-2 {
            width: 400px; height: 400px;
            background: var(--secondary);
            bottom: -150px; right: -100px;
            animation-delay: -6s;
        }

        @keyframes float {
            0% { transform: translate(0, 0) scale(1); }
            100% { transform: translate(30px, 40px) scale(1.2); }
        }
    </style>
</head>
<body>
    
    <div class="app-bg" id="scene" style="width: 100vw; height: 100vh; max-width: none; border-radius: 0;">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <canvas id="neural-canvas"></canvas>
        
        <div class="glass-card" id="card">
            <div class="title-wrapper">
                <h1>Hermes</h1>
                <div class="subtitle">Autonomous Intelligence</div>
            </div>
            
            <div class="status-container">
                <div class="status-badge">
                    <div class="core-pulse"></div>
                    Core Online
                </div>
            </div>
        </div>
    </div>

    <script>
        // 3D Parallax Tilt Effect
        const scene = document.getElementById('scene');
        const card = document.getElementById('card');
        
        let mouseX = 0;
        let mouseY = 0;
        let isClicking = false;

        scene.addEventListener('mousemove', (e) => {
            const rect = scene.getBoundingClientRect();
            mouseX = e.clientX - rect.left;
            mouseY = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = ((mouseY - centerY) / centerY) * -15; // Max 15 deg tilt
            const rotateY = ((mouseX - centerX) / centerX) * 15;
            
            card.style.transform = `translateZ(50px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });

        scene.addEventListener('mouseleave', () => {
            card.style.transform = 'translateZ(50px) rotateX(0) rotateY(0)';
            mouseX = -1000;
            mouseY = -1000;
        });
        
        scene.addEventListener('mousedown', () => isClicking = true);
        scene.addEventListener('mouseup', () => isClicking = false);
        scene.addEventListener('touchstart', (e) => {
            const rect = scene.getBoundingClientRect();
            mouseX = e.touches[0].clientX - rect.left;
            mouseY = e.touches[0].clientY - rect.top;
            isClicking = true;
        });
        scene.addEventListener('touchend', () => {
            isClicking = false;
            mouseX = -1000;
            mouseY = -1000;
        });

        // Neural Network Particle System
        const canvas = document.getElementById('neural-canvas');
        const ctx = canvas.getContext('2d');
        
        let width, height;
        const particles = [];
        
        function resize() {
            width = scene.clientWidth;
            height = scene.clientHeight;
            canvas.width = width;
            canvas.height = height;
        }
        
        window.addEventListener('resize', resize);
        resize();

        class Particle {
            constructor() {
                this.x = Math.random() * width;
                this.y = Math.random() * height;
                this.vx = (Math.random() - 0.5) * 1.5;
                this.vy = (Math.random() - 0.5) * 1.5;
                this.radius = Math.random() * 2 + 1;
                this.baseVx = this.vx;
                this.baseVy = this.vy;
            }

            update() {
                // Friction / return to base speed
                this.vx = this.vx * 0.95 + this.baseVx * 0.05;
                this.vy = this.vy * 0.95 + this.baseVy * 0.05;
                
                // Speed limit
                const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
                if (speed > 10) {
                    this.vx = (this.vx / speed) * 10;
                    this.vy = (this.vy / speed) * 10;
                }

                this.x += this.vx;
                this.y += this.vy;

                // Bounce off edges (and teleport inside to prevent getting trapped)
                if (this.x <= 0) { this.x = 0.1; this.vx *= -1; }
                if (this.x >= width) { this.x = width - 0.1; this.vx *= -1; }
                if (this.y <= 0) { this.y = 0.1; this.vy *= -1; }
                if (this.y >= height) { this.y = height - 0.1; this.vy *= -1; }
            }

            draw() {
                ctx.fillStyle = 'rgba(76, 201, 240, 0.7)'; // Tertiary cyan
                ctx.shadowBlur = 10;
                ctx.shadowColor = 'rgba(76, 201, 240, 1)';
                // Draw as a floating pixel (square) instead of a circle
                ctx.fillRect(this.x - this.radius, this.y - this.radius, this.radius * 2, this.radius * 2);
                ctx.shadowBlur = 0; // Reset for lines
            }
        }

        for (let i = 0; i < 70; i++) { // Increased number of pixels
            particles.push(new Particle());
        }

        function animate() {
            ctx.clearRect(0, 0, width, height);
            
            for (let i = 0; i < particles.length; i++) {
                particles[i].update();
                particles[i].draw();
                
                // Draw connections between particles
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    
                    if (distance < 100) {
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.strokeStyle = `rgba(255, 51, 102, ${0.4 - distance / 250})`; // Primary rose
                        ctx.lineWidth = 1.2;
                        ctx.stroke();
                    }
                }
            }
            requestAnimationFrame(animate);
        }
        animate();
    </script>
</body>
</html>
"""
    return html_content

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def self_ping():
    """Ping our own URL every 10 minutes to prevent Render from spinning down."""
    import time, urllib.request
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not render_url:
        return
    while True:
        time.sleep(600)  # 10 minutes
        try:
            urllib.request.urlopen(render_url, timeout=10)
        except Exception:
            pass  # Silently ignore ping failures

def keep_alive():
    server_thread = Thread(target=run)
    server_thread.daemon = True
    server_thread.start()

    ping_thread = Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()
