import json

with open("artifacts/network_trace.json", encoding="utf-8") as f:
    d = json.load(f)

events = d["events"]

print("Searching for origin of ad configurations, snapshot IDs, or targeting...")
for i, ev in enumerate(events[:758]):
    u = ev.get("url", "")
    if any(k in u.lower() for k in ["target", "snapshot", "wuolad", "ad-", "banner", "campaign"]):
        if not any(ign in u.lower() for ign in ["doubleclick", "google", "criteo", "clarity", "adnxs", "smartad", "amazon"]):
            print(f"[{i}] {ev.get('event_type')} {ev.get('method')} {u[:110]}")
            if ev.get("json_keys"):
                print(f"     json_keys: {ev.get('json_keys')}")

print("\nChecking GET /v2/documents/14080870 response in trace...")
for i, ev in enumerate(events):
    if "documents/14080870" in ev.get("url", "") and ev.get("event_type") == "response":
        print(f"Found document metadata response at [{i}]:")
        print("Keys:", ev.get("json_keys"))
        # Check if there are download or fileUrl fields
        keys = ev.get("json_keys", [])
        interesting = [k for k in keys if any(w in k.lower() for w in ["ad", "file", "url", "down", "token"])]
        print("Interesting fields:", interesting)
