import urllib.request
import json
import pathlib

token = pathlib.Path('data/browser_profile/session_token.txt').read_text().strip()

docs = [
    (11877090, "FC-Teoria-y-Practica-PARTE-2"),
    (14082935, "pilas-pdf-14082935"),
    (12780665, "fc-tema-2-completo"),
    (11740526, "apuntes-b-igor-video-youtube"),
    (14080870, "preguntas-examen-ssoo-i")
]

for doc_id, slug in docs:
    req = urllib.request.Request(
        f'https://api.wuolah.com/v2/documents/{doc_id}',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read())
        print(f"Doc {doc_id} ({slug}):")
        print(f"   REAL numPages: {d.get('numPages')}")
        print(f"   REAL size: {d.get('size')} bytes ({d.get('size', 0)/1024/1024:.2f} MB)")
        print(f"   uploadId: {d.get('uploadId')}")
        print(f"   fileUrl: {d.get('fileUrl')}")
