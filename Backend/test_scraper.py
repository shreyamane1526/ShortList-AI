from app import create_app
from scraper import scrape_once

app = create_app()
with app.app_context():
    count = scrape_once(app)
    print(f"Scraped {count} jobs")