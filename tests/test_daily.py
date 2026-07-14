import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parsers.daily import parse_daily_email

sample_path = os.path.join(os.path.dirname(__file__), "email_samples", "aegis_daily_sample.txt")
with open(sample_path, "r", encoding="utf-8") as f:
    sample = f.read()

report = parse_daily_email(sample)
assert report.projects_count == 47, f"projects_count={report.projects_count}"
assert report.open_tasks == 969, f"open_tasks={report.open_tasks}"
assert report.soak_rounds == 1380, f"soak_rounds={report.soak_rounds}"
assert len(report.competition_leaderboard) >= 3, "leaderboard empty"
assert report.competition_leaderboard[0]["model"] == "qwen2.5-coder:0.5b"
print("test_daily PASS")
