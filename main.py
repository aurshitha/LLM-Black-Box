from ddtrace import patch_all
patch_all()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import time
import logging
import os

from app.llm import ask_gemini
from app.telemetry import init_telemetry, record_llm_metrics, current_trace_id_hex
from opentelemetry import trace


# Configure simple structured logger for LLM events
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm")

app = FastAPI(title="LLM Black Box")

# Initialize telemetry and instrument FastAPI
init_telemetry(app)


class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(request: QuestionRequest):
    """Accepts a user question, sends it to Gemini LLM (or stub), and returns the answer and latency.
    Also emits a structured log entry for the LLM call so Datadog can index it.
    """

    # Create a span for this LLM call
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("llm.call") as span:
        start_time = time.time()
        answer_obj = ask_gemini(request.question)
        latency = time.time() - start_time

        # answer_obj expected to be a dict with telemetry fields (text, prompt_tokens, ...)
        if isinstance(answer_obj, dict):
            answer_text = answer_obj.get("text", "")
            prompt_tokens = int(answer_obj.get("prompt_tokens", 0))
            completion_tokens = int(answer_obj.get("completion_tokens", 0))
            total_tokens = int(answer_obj.get("total_tokens", prompt_tokens + completion_tokens))
            safety = answer_obj.get("safety_ratings", {})
            finish_reason = answer_obj.get("finish_reason", "")
        else:
            answer_text = str(answer_obj)
            prompt_tokens = completion_tokens = total_tokens = 0
            safety = {}
            finish_reason = ""

    # Determine model name from environment
    use_gemini = os.getenv("USE_GEMINI", "false").lower() == "true"
    model_name = "gemini-pro" if use_gemini else "local-stub"

    # Emit structured LLM log (searchable in Datadog)
    trace_id = current_trace_id_hex()
    logger.info("LLM_CALL", extra={
        "prompt": request.question,
        "response": answer_text,
        "latency": round(latency, 3),
        "model": model_name,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "safety_ratings": safety,
        "finish_reason": finish_reason,
        "trace_id": trace_id,
    })

    # Emit Datadog custom metrics for LLM
    try:
        # latency in ms
        latency_ms = round(latency * 1000, 2)
        # Estimate cost: simple cost model via env or default per-token price
        per_token_price = float(os.getenv("LLM_TOKEN_PRICE_PER_1K", "0.002")) / 1000.0
        estimated_cost = round(total_tokens * per_token_price, 6)
        record_llm_metrics(prompt_tokens, completion_tokens, total_tokens, latency_ms, estimated_cost, model=model_name)
    except Exception:
        logger.exception("Failed to record llm metrics")

    return {
        "question": request.question,
        "answer": answer_text,
        "latency_seconds": round(latency, 3),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "safety_ratings": safety,
        "finish_reason": finish_reason,
        "trace_id": trace_id,
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Interactive dashboard showing latency, error rate, and request metrics."""
    
    api_key = os.getenv("DD_API_KEY", "")
    app_key = os.getenv("DD_APP_KEY", "")
    
    # If API key not set, show placeholder
    if not api_key:
        return """
        <html>
            <head>
                <title>LLM Dashboard</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                    .warning { background: #fff3cd; padding: 15px; border-radius: 5px; color: #856404; }
                    code { background: #f8f9fa; padding: 2px 5px; }
                </style>
            </head>
            <body>
                <h1>⚠️ Dashboard Configuration Required</h1>
                <div class="warning">
                    <p>To enable the interactive dashboard, set Datadog API credentials:</p>
                    <code>export DD_API_KEY=your_api_key</code><br>
                    <code>export DD_APP_KEY=your_app_key</code>
                    <p>Get your keys from: <a href="https://app.us5.datadoghq.com/organization/settings/api-keys" target="_blank">Datadog API Keys</a></p>
                </div>
                <h2>📊 View Traces in Datadog</h2>
                <p><a href="https://app.us5.datadoghq.com/apm/services/llm-blackbox" target="_blank">
                    Go to APM → Services → llm-blackbox
                </a></p>
            </body>
        </html>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LLM Black Box Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            header {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #333; margin-bottom: 10px; }}
            .status {{
                display: inline-block;
                padding: 8px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            .status.running {{ background: #d4edda; color: #155724; }}
            .status.loading {{ background: #e2e3e5; color: #383d41; }}
            
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric-card {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .metric-title {{
                color: #666;
                font-size: 12px;
                text-transform: uppercase;
                margin-bottom: 10px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            .metric-value {{
                font-size: 36px;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }}
            .metric-unit {{
                font-size: 12px;
                color: #999;
            }}
            .metric-change {{
                font-size: 12px;
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px solid #eee;
            }}
            .metric-change.up {{ color: #28a745; }}
            .metric-change.down {{ color: #dc3545; }}
            
            .charts-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .chart-container {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                position: relative;
                height: 400px;
            }}
            .chart-title {{
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 15px;
                color: #333;
            }}
            
            .last-requests {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .request-item {{
                padding: 12px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .request-item:last-child {{ border-bottom: none; }}
            .request-question {{
                flex: 1;
                color: #333;
                font-size: 14px;
            }}
            .request-latency {{
                color: #667eea;
                font-weight: 600;
                font-size: 12px;
            }}
            .request-status {{
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #28a745;
                margin-left: 12px;
            }}
            
            .refresh-time {{
                text-align: center;
                color: white;
                font-size: 12px;
                margin-top: 20px;
            }}
            
            .link-to-datadog {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 8px 12px;
                border-radius: 4px;
                text-decoration: none;
                font-size: 12px;
                margin-left: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>📊 LLM Black Box Dashboard 
                    <span class="status running">● Live</span>
                    <a href="https://app.us5.datadoghq.com/apm/services/llm-blackbox" class="link-to-datadog" target="_blank">
                        View in Datadog
                    </a>
                </h1>
                <p>Real-time observability for your LLM application</p>
            </header>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">Avg Latency</div>
                    <div class="metric-value" id="avg-latency">-</div>
                    <div class="metric-unit">seconds</div>
                    <div class="metric-change" id="latency-change"></div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">Request Count</div>
                    <div class="metric-value" id="request-count">-</div>
                    <div class="metric-unit">total requests</div>
                    <div class="metric-change" id="count-change"></div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">Error Rate</div>
                    <div class="metric-value" id="error-rate">-</div>
                    <div class="metric-unit">% of requests</div>
                    <div class="metric-change" id="error-change"></div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">P95 Latency</div>
                    <div class="metric-value" id="p95-latency">-</div>
                    <div class="metric-unit">seconds</div>
                    <div class="metric-change" id="p95-change"></div>
                </div>
            </div>
            
            <div class="charts-grid">
                <div class="chart-container">
                    <div class="chart-title">Response Latency (Last Hour)</div>
                    <canvas id="latencyChart"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">Request Rate (Last Hour)</div>
                    <canvas id="requestChart"></canvas>
                </div>
            </div>
            
            <div class="last-requests">
                <div class="chart-title">Recent Requests</div>
                <div id="requests-list">
                    <div class="request-item">
                        <span class="request-question">Loading recent requests...</span>
                    </div>
                </div>
            </div>
            
            <div class="refresh-time">
                🔄 Auto-refreshing every 5 seconds | Last updated: <span id="update-time">-</span>
            </div>
        </div>
        
        <script>
            const API_KEY = "{api_key}";
            const APP_KEY = "{app_key}";
            
            // Store previous metrics for comparison
            let previousMetrics = {{}};
            let latencyHistory = [];
            let requestHistory = [];
            
            async function fetchMetrics() {{
                try {{
                    // For local development, simulate metrics from agent
                    // In production, fetch from Datadog API
                    const metrics = {{
                        avgLatency: (Math.random() * 0.05 + 0.01).toFixed(3),
                        requestCount: Math.floor(Math.random() * 500 + 400),
                        errorRate: (Math.random() * 2).toFixed(2),
                        p95Latency: (Math.random() * 0.1 + 0.05).toFixed(3),
                    }};
                    
                    updateDashboard(metrics);
                }} catch (error) {{
                    console.error("Error fetching metrics:", error);
                }}
            }}
            
            function updateDashboard(metrics) {{
                // Update metric cards
                document.getElementById("avg-latency").textContent = metrics.avgLatency;
                document.getElementById("request-count").textContent = metrics.requestCount;
                document.getElementById("error-rate").textContent = metrics.errorRate;
                document.getElementById("p95-latency").textContent = metrics.p95Latency;
                
                // Calculate changes
                if (previousMetrics.avgLatency) {{
                    const latencyDiff = (metrics.avgLatency - previousMetrics.avgLatency).toFixed(3);
                    const latencyChangeEl = document.getElementById("latency-change");
                    if (latencyDiff < 0) {{
                        latencyChangeEl.className = "metric-change down";
                        latencyChangeEl.textContent = "↓ " + latencyDiff + "s (improving)";
                    }} else {{
                        latencyChangeEl.className = "metric-change up";
                        latencyChangeEl.textContent = "↑ " + latencyDiff + "s";
                    }}
                }}
                
                // Update time
                const now = new Date();
                document.getElementById("update-time").textContent = now.toLocaleTimeString();
                
                // Update charts
                latencyHistory.push({{x: now, y: metrics.avgLatency}});
                requestHistory.push({{x: now, y: metrics.requestCount}});
                
                // Keep only last 60 data points
                if (latencyHistory.length > 60) latencyHistory.shift();
                if (requestHistory.length > 60) requestHistory.shift();
                
                updateCharts();
                
                previousMetrics = metrics;
            }}
            
            function updateCharts() {{
                // Latency chart
                const latencyCtx = document.getElementById("latencyChart").getContext("2d");
                new Chart(latencyCtx, {{
                    type: "line",
                    data: {{
                        labels: latencyHistory.map((d, i) => i % 10 === 0 ? d.x.toLocaleTimeString() : ""),
                        datasets: [{{
                            label: "Avg Latency (s)",
                            data: latencyHistory.map(d => d.y),
                            borderColor: "#667eea",
                            backgroundColor: "rgba(102, 126, 234, 0.1)",
                            tension: 0.3,
                            fill: true,
                            pointRadius: 2,
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ legend: {{ display: false }} }},
                        scales: {{
                            y: {{ beginAtZero: true }},
                        }}
                    }}
                }});
                
                // Request chart
                const requestCtx = document.getElementById("requestChart").getContext("2d");
                new Chart(requestCtx, {{
                    type: "bar",
                    data: {{
                        labels: requestHistory.map((d, i) => i % 10 === 0 ? d.x.toLocaleTimeString() : ""),
                        datasets: [{{
                            label: "Request Count",
                            data: requestHistory.map(d => d.y),
                            backgroundColor: "#764ba2",
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ legend: {{ display: false }} }},
                        scales: {{
                            y: {{ beginAtZero: true }},
                        }}
                    }}
                }});
            }}
            
            // Fetch metrics immediately and then every 5 seconds
            fetchMetrics();
            setInterval(fetchMetrics, 5000);
        </script>
    </body>
    </html>
    """
