# src/fb_cdp_listener.py
# Re-export from collectors.fb_cdp_listener
try:
    from src.collectors.fb_cdp_listener import fetch_facebook_group_jobs, FacebookCDPCollector, extract_posts_from_json
except ImportError:
    from collectors.fb_cdp_listener import fetch_facebook_group_jobs, FacebookCDPCollector, extract_posts_from_json

__all__ = ["fetch_facebook_group_jobs", "FacebookCDPCollector", "extract_posts_from_json"]

if __name__ == "__main__":
    jobs = fetch_facebook_group_jobs()
    print(f"Thu được {len(jobs)} bài.")
