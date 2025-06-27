from main import db, Product, app

with app.app_context():
    if Product.query.count() == 0:
        products = [
            Product(name="T-Shirt", description="100% cotton", price=19.99),
            Product(name="Mug", description="Ceramic, 350ml", price=9.99),
            Product(name="Notebook", description="A5 size, 200 pages", price=5.49),
        ]
        db.session.bulk_save_objects(products)
        db.session.commit()
        print("Database seeded.")
    else:
        print("Database already contains products. Skipping seeding.")
