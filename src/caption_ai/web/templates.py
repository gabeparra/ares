"""HTML templates for the web UI."""


def get_default_html() -> str:
    """Return default HTML if file doesn't exist."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Glup - Advanced Meeting Intelligence</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: #0a0a0a;
            color: #e0e0e0;
            overflow-x: hidden;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            border-bottom: 2px solid #ff0000;
            padding: 20px 0;
            margin-bottom: 30px;
        }
        h1 {
            color: #ff0000;
            text-shadow: 0 0 10px #ff0000;
            font-size: 2.5em;
            letter-spacing: 3px;
        }
        .subtitle {
            color: #888;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        @media (max-width: 968px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        .panel {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 0 20px rgba(255, 0, 0, 0.1);
        }
        .panel h2 {
            color: #ff4444;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        .segments {
            max-height: 500px;
            overflow-y: auto;
        }
        .segment {
            background: #252525;
            padding: 12px;
            margin-bottom: 10px;
            border-left: 3px solid #ff0000;
            border-radius: 4px;
        }
        .segment-time {
            color: #888;
            font-size: 0.85em;
            margin-bottom: 5px;
        }
        .segment-speaker {
            color: #ff6666;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .segment-text {
            color: #e0e0e0;
            line-height: 1.6;
        }
        .summary {
            background: #252525;
            padding: 15px;
            border-left: 3px solid #00ff00;
            border-radius: 4px;
            line-height: 1.8;
            color: #e0e0e0;
        }
        .status {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #1a1a1a;
            border: 1px solid #333;
            padding: 10px 15px;
            border-radius: 5px;
            font-size: 0.9em;
        }
        .status.connected {
            border-color: #00ff00;
            color: #00ff00;
        }
        .status.disconnected {
            border-color: #ff0000;
            color: #ff0000;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        .status.connected .status-indicator {
            background: #00ff00;
        }
        .status.disconnected .status-indicator {
            background: #ff0000;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #1a1a1a;
        }
        ::-webkit-scrollbar-thumb {
            background: #ff0000;
            border-radius: 4px;
        }
        .empty-state {
            text-align: center;
            color: #666;
            padding: 40px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="status disconnected" id="status">
        <span class="status-indicator"></span>
        <span id="status-text">Disconnected</span>
    </div>
    <div class="container">
        <header>
            <h1>GLUP</h1>
            <div class="subtitle">Advanced Meeting Intelligence | Neural Processing Active</div>
        </header>
        <div class="main-content">
            <div class="panel">
                <h2>Conversation Segments</h2>
                <div class="segments" id="segments">
                    <div class="empty-state">Awaiting conversation data...</div>
                </div>
            </div>
            <div class="panel">
                <h2>Glup Analysis</h2>
                <div id="summary">
                    <div class="empty-state">No analysis available yet...</div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        const segmentsDiv = document.getElementById('segments');
        const summaryDiv = document.getElementById('summary');
        const statusDiv = document.getElementById('status');
        const statusText = document.getElementById('status-text');
        
        function updateStatus(connected) {
            if (connected) {
                statusDiv.className = 'status connected';
                statusText.textContent = 'Connected';
            } else {
                statusDiv.className = 'status disconnected';
                statusText.textContent = 'Disconnected';
            }
        }
        
        function addSegment(segment) {
            if (segmentsDiv.querySelector('.empty-state')) {
                segmentsDiv.innerHTML = '';
            }
            const div = document.createElement('div');
            div.className = 'segment';
            const date = new Date(segment.timestamp);
            div.innerHTML = `
                <div class="segment-time">${date.toLocaleTimeString()}</div>
                <div class="segment-speaker">${segment.speaker || 'Speaker'}</div>
                <div class="segment-text">${segment.text}</div>
            `;
            segmentsDiv.insertBefore(div, segmentsDiv.firstChild);
            segmentsDiv.scrollTop = 0;
        }
        
        function updateSummary(summary) {
            summaryDiv.innerHTML = `<div class="summary">${summary.replace(/\\n/g, '<br>')}</div>`;
        }
        
        ws.onopen = () => {
            updateStatus(true);
            ws.send(JSON.stringify({type: 'init'}));
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'segment') {
                addSegment(data.segment);
            } else if (data.type === 'summary') {
                updateSummary(data.summary);
            } else if (data.type === 'init') {
                if (data.segments) {
                    data.segments.forEach(s => addSegment(s));
                }
                if (data.summary) {
                    updateSummary(data.summary);
                }
            }
        };
        
        ws.onclose = () => {
            updateStatus(false);
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        };
        
        ws.onerror = () => {
            updateStatus(false);
        };
    </script>
</body>
</html>"""

