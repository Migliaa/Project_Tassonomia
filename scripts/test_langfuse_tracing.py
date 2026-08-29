"""Single minimal LLM call to verify the Langfuse tracing wiring, without
burning meaningful API quota (one request, tiny prompt, no retries loop)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tau2-bench" / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "tau2-bench" / ".env")

import time

import litellm

litellm.success_callback = ["langfuse_otel"]
litellm.failure_callback = ["langfuse_otel"]

response = litellm.completion(
    model="gemini/gemini-3.5-flash-lite",
    messages=[{"role": "user", "content": "Reply with just: ok"}],
    temperature=0.0,
    metadata={"session_id": "s2_tracing_smoke_test_2", "tags": ["tau2", "s2-verify"]},
)
print("Response:", response.choices[0].message.content)

print("Waiting for the OpenTelemetry batch exporter to flush...")
time.sleep(10)
print("Sent one completion call tagged trace_id=s2_tracing_smoke_test to Langfuse.")
