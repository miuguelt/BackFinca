"""
Safe migration helper: make `fields.food_type_id` NOT NULL by:
1. Creating a placeholder FoodTypes record (name='Sin especificar') if needed.
2. Updating all `fields` rows with NULL `food_type_id` to point to the placeholder.
3. Attempting to alter the column to NOT NULL (only for MySQL automated).

This script is idempotent and will not drop data. It prints instructions for dialects
that require manual intervention (SQLite).

Usage:
    python scripts/migrate_fields_food_type_not_null.py

Prerequisites: ensure you have a backup. This script connects using the app configuration.
"""
from __future__ import annotations
from sqlalchemy import text

try:
    from app import create_app, db
    from app.models.foodTypes import FoodTypes
    from app.models.fields import Fields
except Exception:
    print("Failed to import application context. Run from repository root and ensure dependencies are installed.")
    raise


def main():
    app = create_app()
    with app.app_context():
        engine = db.engine
        dialect = engine.dialect.name
        print(f"Connected to database using dialect: {dialect}")

        # Step 1: ensure placeholder FoodType exists
        placeholder = FoodTypes.query.filter_by(food_type='Sin especificar').first()
        if not placeholder:
            print("Creating placeholder FoodTypes record 'Sin especificar'")
            placeholder = FoodTypes(food_type='Sin especificar', handlings='Placeholder for migration')
            db.session.add(placeholder)
            db.session.commit()
        else:
            print(f"Found placeholder FoodTypes id={placeholder.id}")

        # Step 2: update fields with NULL food_type_id
        null_fields = Fields.query.filter(Fields.food_type_id == None).all()
        count = len(null_fields)
        if count == 0:
            print("No fields with NULL food_type_id found. Data migration step skipped.")
        else:
            print(f"Found {count} fields with NULL food_type_id. Updating to placeholder id={placeholder.id}...")
            for f in null_fields:
                f.food_type_id = placeholder.id
                db.session.add(f)
            db.session.commit()
            print("Update complete.")

        # Step 3: attempt to alter column to NOT NULL where supported
        if dialect in ('mysql', 'mariadb'):
            print("Attempting to ALTER TABLE to set food_type_id NOT NULL (MySQL/MariaDB)...")
            try:
                engine.execute(text('ALTER TABLE fields MODIFY COLUMN food_type_id INT NOT NULL'))
                print("ALTER TABLE executed successfully.")
            except Exception as ex:
                print("ALTER TABLE failed:", ex)
                print("Please run the equivalent ALTER statement manually on your database or use Alembic migration.")
        elif dialect == 'postgresql':
            print("Attempting to ALTER TABLE to set food_type_id NOT NULL (Postgres)...")
            try:
                engine.execute(text('ALTER TABLE fields ALTER COLUMN food_type_id SET NOT NULL'))
                print("ALTER TABLE executed successfully.")
            except Exception as ex:
                print("ALTER TABLE failed:", ex)
                print("Please run the equivalent ALTER statement manually on your database or use Alembic migration.")
        else:
            print("Automatic ALTER TABLE not implemented for this dialect. For SQLite, manual table rebuild is required.")
            print("Recommended steps:")
            print("  1) Ensure all rows have a non-null food_type_id (script already updated them).")
            print("  2) Create a new table with desired schema and copy data, or use Alembic autogenerate on a MySQL/Postgres DB.")


if __name__ == '__main__':
    main()
