import json
import time
import os
import uuid
from pathlib import Path
from nexttoken import NextToken

client = NextToken()
MODEL_ID = "gemini-3-flash-preview"

def _load_prompt(name: str) -> str:
    path = Path(__file__).parent / "prompts" / name
    return path.read_text(encoding="utf-8")

def run_trust_agent_streaming(message: str, history: list = None, max_iterations: int = 5):
    """
    Agentic Middleware Loop for Civic AI Trust.
    Processes unstructured civic reports and returns structured trust events.
    """
    system_prompt = _load_prompt("system.md")
    messages = [{"role": "system", "content": system_prompt}] + (history or [])
    messages.append({"role": "user", "content": f"Analyze this civic data report and provide a structured trust assessment: {message}"})

    yield {"type": "status", "content": "Analyzing civic data report...", "progress": 20}
    
    # Simple agent loop for data validation (can be expanded with tools)
    for iteration in range(max_iterations):
        yield {"type": "thinking", "content": f"Validating data integrity and calculating reliability scores (Iteration {iteration+1})..."}
        
        # Call LLM to perform trust-aware logic
        # Using json_mode if needed, but for agentic loop we use structured instruction
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        try:
            # Validate output is correct JSON matching our "Middleware" contract
            data = json.loads(content)
            
            # Simulated reliability check (in a real app, this might involve a tool call to a DB)
            reliability = data.get("reliability_score", 0.0)
            yield {"type": "status", "content": f"Reliability Score: {int(reliability * 100)}%", "progress": 80}
            
            # Return final assessment
            yield {"type": "message_complete", "content": content}
            yield {"type": "done"}
            return
            
        except json.JSONDecodeError:
            yield {"type": "error", "content": "Middleware failed to produce structured output. Retrying..."}
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": "Please format your last response as valid JSON."})

    yield {"type": "error", "content": "Agent reached maximum iterations without valid JSON."}
    yield {"type": "done"}
