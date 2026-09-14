import json

with open("artifacts/network_trace.json", encoding="utf-8") as f:
    d = json.load(f)

events = d["events"]

print("=== FORENSIC ANALYSIS OF POST /v2/download ===")
for i in [758, 763, 764, 783, 787, 788]:
    if i < len(events):
        ev = events[i]
        print(f"\n--- EVENT [{i}] {ev.get('event_type')} {ev.get('method')} {ev.get('url')} ---")
        print("Timestamp:", ev.get("timestamp"))
        print("Resource Type:", ev.get("resource_type"))
        print("Status:", ev.get("status"))
        print("Content-Type:", ev.get("content_type"))
        print("Content-Disposition:", ev.get("content_disposition"))
        print("Redirect Chain:", ev.get("redirect_chain"))
        print("Post Data Keys / Body Info:", ev.get("post_data_keys"))
        print("Post Data Raw:", ev.get("post_data_preview"))
        print("Request Headers (non-sensitive):", ev.get("request_headers"))
        print("Response Headers:", ev.get("response_headers"))
        print("JSON Keys:", ev.get("json_keys"))
        print("JSON Data preview (safe):", ev.get("json_data"))
