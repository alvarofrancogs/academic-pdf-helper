import json

with open("artifacts/network_trace.json", encoding="utf-8") as f:
    d = json.load(f)

events = d["events"]
print(f"Total events: {len(events)}")
print(f"Downloads list in trace root: {d.get('downloads')}")

print("\n--- ALL api.wuolah.com EVENTS ---")
for i, ev in enumerate(events):
    u = ev.get("url", "")
    if "api.wuolah.com" in u:
        etype = ev.get("event_type")
        method = ev.get("method")
        status = ev.get("status")
        keys = ev.get("json_keys")
        ctype = ev.get("content_type")
        size = ev.get("size_bytes")
        print(f"[{i}] {etype} | {method} {u} | status={status} | ctype={ctype} | size={size} | json_keys={keys}")
        if keys:
            print(f"     json_keys: {keys}")
        if ev.get("post_data_keys"):
            print(f"     post_data_keys: {ev.get('post_data_keys')}")
        if ev.get("request_headers"):
            print(f"     req_headers: {list(ev['request_headers'].keys())}")
        if ev.get("response_headers"):
            print(f"     resp_headers: {list(ev['response_headers'].keys())}")

print("\n--- ALL DOWNLOAD EVENTS ---")
for i, ev in enumerate(events):
    if ev.get("event_type") == "download":
        print(f"[{i}] DOWNLOAD EVENT:")
        print(json.dumps(ev, indent=2, ensure_ascii=False))

print("\n--- ANY PDF OR BINARY EVENTS ---")
for i, ev in enumerate(events):
    if ev.get("is_pdf") or ev.get("is_binary"):
        print(f"[{i}] {ev.get('method')} {ev.get('url')} | pdf={ev.get('is_pdf')} | binary={ev.get('is_binary')} | size={ev.get('size_bytes')}")
