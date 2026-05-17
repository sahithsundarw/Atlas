import requests

base = "http://localhost:8000"

r = requests.get(f"{base}/health")
assert r.json() == {"status": "ok"}
print("PASS health")

r = requests.post(f"{base}/query", json={"message": "Tell me about Paris", "thread_id": "smoke-1"})
d = r.json()
assert d.get("city", "").lower() == "paris", f"city wrong: {d}"
assert d.get("source") in ("vector", "web"), f"bad source: {d}"
assert d.get("city_summary"), "no summary"
assert len(d.get("weather_forecast", [])) > 0, "no forecast"
assert len(d.get("image_urls", [])) > 0, "no images"
print(f"PASS paris  source={d['source']}  sim={d.get('similarity_score',0):.2f}  days={len(d['weather_forecast'])}  imgs={len(d['image_urls'])}")

r = requests.post(f"{base}/query", json={"message": "Tell me about Reykjavik", "thread_id": "smoke-2"})
d = r.json()
assert d.get("city"), f"no city: {d}"
assert d.get("source") == "web", f"expected web source: {d}"
print(f"PASS reykjavik  source={d['source']}")

r = requests.post(f"{base}/query", json={"message": "What is 2+2?", "thread_id": "smoke-3"})
d = r.json()
assert d.get("city_summary"), f"no summary in guard response: {d}"
print(f"PASS guard  msg={d['city_summary'][:60]}")

r = requests.post(f"{base}/query", json={"message": "Tell me about Tokyo", "thread_id": "multi-1"})
r2 = requests.post(f"{base}/query", json={"message": "What is the nightlife like there?", "thread_id": "multi-1"})
d2 = r2.json()
assert d2.get("city", "").lower() == "tokyo", f"multi-turn city wrong: {d2}"
print(f"PASS multi-turn  city={d2['city']}")

r = requests.post(f"{base}/query", json={"message": "How is India in the summer?", "thread_id": "smoke-4"})
d = r.json()
assert d.get("source") == "seasonal", f"expected seasonal: {d}"
assert d.get("city_summary"), "no seasonal summary"
print(f"PASS seasonal  source={d['source']}")

print("\nALL SMOKE TESTS PASSED")
