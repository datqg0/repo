# src/linkedin_api.py
# Re-export from collectors.linkedin_api
try:
    from src.collectors.linkedin_api import fetch_linkedin_jobs, LinkedInCollector
except ImportError:
    from collectors.linkedin_api import fetch_linkedin_jobs, LinkedInCollector

__all__ = ["fetch_linkedin_jobs", "LinkedInCollector"]

if __name__ == "__main__":
    jobs = fetch_linkedin_jobs()
    print(f"Quét được {len(jobs)} bài.")
