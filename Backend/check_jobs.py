from app import create_app

app = create_app()
with app.app_context():
    from models import Job
    print(f"Jobs count: {Job.query.count()}")
    jobs = Job.query.all()
    for job in jobs:
        print(f"Job: {job.title}, region_id: {job.region_id}")