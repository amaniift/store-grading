import urllib.request, json
r = urllib.request.urlopen('http://localhost:5000/api/filters')
d = json.loads(r.read())
print(f"Depts: {len(d['depts'])}, Classes: {len(d['classes'])}, Countries: {len(d['countries'])}, Stores: {len(d['stores'])}")
print("Sample Depts:", [x['DEPT'] for x in d['depts'][:5]])
print("Sample Countries:", [x['AREA_NAME'] for x in d['countries'][:5]])
