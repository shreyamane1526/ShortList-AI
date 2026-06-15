from app import create_app

app = create_app()
with app.app_context():
    from models import Region
    print(f"Regions count: {Region.query.count()}")
    regions = Region.query.all()
    for region in regions:
        print(f"Region: {region.name}, id: {region.id}, code: {region.code}")