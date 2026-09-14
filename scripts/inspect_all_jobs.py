import pathlib
import json

for p in pathlib.Path('data').glob('*/job.json'):
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
        meta = d.get('result_metadata') or {}
        print(f"{d.get('job_id')}: pages={meta.get('pages')} size={meta.get('size_formatted')} type={meta.get('detected_type')} url={d.get('url')}")
    except Exception as e:
        print(p, e)
