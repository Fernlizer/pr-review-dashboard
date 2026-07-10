import urllib.request
import json

endpoints = ['/api/stats', '/api/prs', '/api/prs/136', '/api/scheduler/status', '/api/settings/auto-comment']

for ep in endpoints:
    print(f'\n=== {ep} ===')
    try:
        req = urllib.request.Request(f'http://localhost:9100{ep}')
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode()
            print(f'Status: {resp.status}')
            try:
                data = json.loads(body)
                print(json.dumps(data, indent=2, default=str)[:2000])
            except:
                print(body[:2000])
    except Exception as e:
        print(f'Error: {e}')
