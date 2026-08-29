"""Check B09 + B05 advanced traces: LLM raw output OK? frames canonical?"""
import json

B = "/root/.hermes/micro1-hackathon/creative-court/traces"

for bid in ("B09", "B05"):
    p = f"{B}/eval_adv_{bid}.jsonl"
    print(f"=== {bid} ===")
    for line in open(p, encoding="utf-8"):
        e = json.loads(line)
        if e["type"] == "retry":
            print(" RETRY:", e.get("retry_of"), "|", (e.get("feedback") or "")[:100])
        if e["type"] == "tool_response" and e.get("tool") == "llm":
            print(" llm raw head:", e["tool_response"][:120].replace("\n", " "))
        if e["type"] == "agent_step" and e.get("action", "").startswith("produced"):
            name = e["action"].split(": ", 1)[-1]
            print(" dir:", e["action"][:80])
