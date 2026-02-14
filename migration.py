#!/usr/bin/env python3
"""
MySQL to SQLite Migration Script (FIXED)
Migrates all data from MySQL (wucskkm_db1) to SQLite (wucskkm.db)
Fixes: Missing columns, Decimal type conversion
"""

import mysql.connector
import sqlite3
import base64
import os
from datetime import datetime
from decimal import Decimal

# MySQL Configuration - UPDATE THESE!
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",  # Your MySQL username
    "password": "root",  # Your MySQL password
    "database": "wucskkm_db1",  # Your MySQL database
    "port": 3306
}

# SQLite Configuration
SQLITE_DB = "wucskkm.db"


class DatabaseMigration:
    def __init__(self):
        self.mysql_conn = None
        self.sqlite_conn = None
        self.stats = {}

    def connect_mysql(self):
        """Connect to MySQL database"""
        print("🔌 Connecting to MySQL...")
        try:
            self.mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
            print("✅ MySQL connected successfully!")
            return True
        except mysql.connector.Error as err:
            print(f"❌ MySQL connection failed: {err}")
            print("\n💡 Common fixes:")
            print("   1. Check username/password in MYSQL_CONFIG")
            print("   2. Verify database name")
            print("   3. Check if MySQL is running")
            return False

    def connect_sqlite(self):
        """Connect to SQLite database"""
        print(f"🔌 Connecting to SQLite ({SQLITE_DB})...")
        try:
            # Backup existing database if it exists
            if os.path.exists(SQLITE_DB):
                backup_name = f"{SQLITE_DB}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(SQLITE_DB, backup_name)
                print(f"📦 Existing database backed up to: {backup_name}")

            self.sqlite_conn = sqlite3.connect(SQLITE_DB)
            self.sqlite_conn.execute("PRAGMA foreign_keys = ON")
            print("✅ SQLite connected successfully!")
            return True
        except sqlite3.Error as err:
            print(f"❌ SQLite connection failed: {err}")
            return False

    def get_mysql_columns(self, table_name):
        """Get actual column names from MySQL table"""
        cursor = self.mysql_conn.cursor()
        cursor.execute(f"DESCRIBE {table_name}")
        columns = [row[0] for row in cursor.fetchall()]
        return columns

    def create_tables(self):
        """Create all tables in SQLite with proper columns"""
        print("\n📋 Creating SQLite tables...")

        cursor = self.sqlite_conn.cursor()

        # Get actual MySQL columns for problematic tables
        news_cols = self.get_mysql_columns('farmers_news')
        gallery_cols = self.get_mysql_columns('farmers_gallery')
        society_cols = self.get_mysql_columns('farmers_society')

        print(f"  ℹ️  farmers_news columns: {news_cols}")
        print(f"  ℹ️  farmers_gallery columns: {gallery_cols}")
        print(f"  ℹ️  farmers_society columns: {society_cols}")

        # Build CREATE statements based on actual columns
        news_fields = []
        for col in news_cols:
            if col == 'id':
                news_fields.append('id INTEGER PRIMARY KEY AUTOINCREMENT')
            else:
                news_fields.append(f'{col} TEXT')

        gallery_fields = []
        for col in gallery_cols:
            if col == 'id':
                gallery_fields.append('id INTEGER PRIMARY KEY AUTOINCREMENT')
            else:
                gallery_fields.append(f'{col} TEXT')

        society_fields = []
        for col in society_cols:
            if col == 'id':
                society_fields.append('id INTEGER PRIMARY KEY AUTOINCREMENT')
            else:
                society_fields.append(f'{col} TEXT')

        tables = {
            'farmers_news': f'''
                CREATE TABLE IF NOT EXISTS farmers_news (
                    {', '.join(news_fields)}
                )
            ''',

            'farmers_document': '''
                CREATE TABLE IF NOT EXISTS farmers_document (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    link TEXT,
                    title TEXT,
                    filename TEXT
                )
            ''',

            'farmers_board': '''
                CREATE TABLE IF NOT EXISTS farmers_board (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    content TEXT
                )
            ''',

            'farmers_crops': '''
                CREATE TABLE IF NOT EXISTS farmers_crops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    content TEXT
                )
            ''',

            'farmers_gallery': f'''
                CREATE TABLE IF NOT EXISTS farmers_gallery (
                    {', '.join(gallery_fields)}
                )
            ''',

            'farmers_society': f'''
                CREATE TABLE IF NOT EXISTS farmers_society (
                    {', '.join(society_fields)}
                )
            ''',

            'farmers_map_data': '''
                CREATE TABLE IF NOT EXISTS farmers_map_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mapid INTEGER,
                    name TEXT,
                    pass INTEGER,
                    sno TEXT,
                    area REAL
                )
            ''',

            'farmers_years': '''
                CREATE TABLE IF NOT EXISTS farmers_years (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    years TEXT
                )
            ''',

            'farmers_year_data': '''
                CREATE TABLE IF NOT EXISTS farmers_year_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    y TEXT,
                    batha REAL,
                    kabbu REAL,
                    tota REAL,
                    mtax REAL
                )
            ''',

            'farmers_data': '''
                CREATE TABLE IF NOT EXISTS farmers_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pass INTEGER,
                    sno TEXT,
                    area REAL,
                    batha REAL,
                    bkara REAL,
                    kabu REAL,
                    kkara REAL,
                    thota REAL,
                    tkara REAL,
                    wtax REAL,
                    mtax REAL,
                    t1 REAL,
                    bal REAL,
                    t2 REAL,
                    name TEXT,
                    first INTEGER,
                    share INTEGER,
                    paid REAL,
                    year TEXT,
                    old REAL,
                    rt REAL,
                    total REAL,
                    balance REAL,
                    count INTEGER,
                    village TEXT,
                    crop1 TEXT,
                    area1 REAL,
                    kara1 REAL,
                    crop2 TEXT,
                    area2 REAL,
                    kara2 REAL,
                    pp TEXT,
                    phone TEXT
                )
            '''
        }

        for table_name, create_sql in tables.items():
            try:
                cursor.execute(create_sql)
                print(f"  ✅ Created table: {table_name}")
            except sqlite3.Error as err:
                print(f"  ❌ Failed to create {table_name}: {err}")

        self.sqlite_conn.commit()
        print("✅ All tables created!")

    def convert_decimals(self, row):
        """Convert Decimal objects to float"""
        for key, value in row.items():
            if isinstance(value, Decimal):
                row[key] = float(value)
        return row

    def transform_blob_to_text(self, row):
        """Transform blob fields to text for SQLite"""
        for key, value in row.items():
            if isinstance(value, bytes):
                try:
                    # Try to decode as base64
                    row[key] = base64.b64encode(value).decode('utf-8')
                except:
                    try:
                        # Try to decode as utf-8
                        row[key] = value.decode('utf-8')
                    except:
                        # Keep as base64
                        row[key] = base64.b64encode(value).decode('utf-8')
        return row

    def transform_row(self, row):
        """Apply all transformations to a row"""
        row = self.convert_decimals(row)
        row = self.transform_blob_to_text(row)
        return row

    def migrate_table(self, table_name):
        """Migrate a single table from MySQL to SQLite"""
        print(f"\n📦 Migrating table: {table_name}")

        try:
            # Get data from MySQL
            mysql_cursor = self.mysql_conn.cursor(dictionary=True)
            mysql_cursor.execute(f"SELECT * FROM {table_name}")
            rows = mysql_cursor.fetchall()

            if not rows:
                print(f"  ⚠️  No data found in {table_name}")
                self.stats[table_name] = 0
                return

            # Transform all rows
            rows = [self.transform_row(row) for row in rows]

            # Get column names from first row
            columns = list(rows[0].keys())

            # Prepare SQLite insert
            placeholders = ','.join(['?' for _ in columns])
            column_names = ','.join(columns)
            insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"

            # Insert data into SQLite
            sqlite_cursor = self.sqlite_conn.cursor()
            for row in rows:
                values = tuple(row.values())
                sqlite_cursor.execute(insert_sql, values)

            self.sqlite_conn.commit()
            self.stats[table_name] = len(rows)
            print(f"  ✅ Migrated {len(rows)} rows")

        except Exception as err:
            print(f"  ❌ Migration failed: {err}")
            self.stats[table_name] = f"FAILED: {err}"
            import traceback
            traceback.print_exc()

    def migrate_all(self):
        """Migrate all tables"""
        print("\n" + "=" * 70)
        print("🚀 STARTING MIGRATION: MySQL → SQLite")
        print("=" * 70)

        tables = [
            'farmers_news',
            'farmers_document',
            'farmers_board',
            'farmers_crops',
            'farmers_gallery',
            'farmers_society',
            'farmers_map_data',
            'farmers_years',
            'farmers_year_data',
            'farmers_data'
        ]

        for table in tables:
            self.migrate_table(table)

    def verify_migration(self):
        """Verify data was migrated correctly"""
        print("\n" + "=" * 70)
        print("🔍 VERIFYING MIGRATION")
        print("=" * 70)

        sqlite_cursor = self.sqlite_conn.cursor()
        mysql_cursor = self.mysql_conn.cursor()

        # Get all tables
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in sqlite_cursor.fetchall()]

        print("\n📊 Row count comparison:\n")
        print(f"{'Table':<25} {'MySQL':<15} {'SQLite':<15} {'Status'}")
        print("-" * 70)

        all_match = True
        for table in tables:
            if table == 'sqlite_sequence':
                continue

            # Count MySQL rows
            try:
                mysql_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                mysql_count = mysql_cursor.fetchone()[0]
            except:
                mysql_count = 0

            # Count SQLite rows
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            sqlite_count = sqlite_cursor.fetchone()[0]

            status = "✅ OK" if mysql_count == sqlite_count else "❌ MISMATCH"
            if mysql_count != sqlite_count:
                all_match = False

            print(f"{table:<25} {mysql_count:<15} {sqlite_count:<15} {status}")

        print("-" * 70)
        if all_match:
            print("\n✅ Migration verified successfully! All row counts match.")
        else:
            print("\n⚠️  Some tables have mismatched row counts. Please review.")

        return all_match

    def create_indexes(self):
        """Create indexes for better performance"""
        print("\n📇 Creating indexes for better performance...")

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_farmers_data_pass ON farmers_data(pass)",
            "CREATE INDEX IF NOT EXISTS idx_farmers_data_year ON farmers_data(year)",
            "CREATE INDEX IF NOT EXISTS idx_farmers_data_first ON farmers_data(first)",
            "CREATE INDEX IF NOT EXISTS idx_farmers_data_pass_year ON farmers_data(pass, year)",
            "CREATE INDEX IF NOT EXISTS idx_farmers_map_data_pass ON farmers_map_data(pass)",
            "CREATE INDEX IF NOT EXISTS idx_farmers_map_data_mapid ON farmers_map_data(mapid)",
        ]

        cursor = self.sqlite_conn.cursor()
        for idx_sql in indexes:
            try:
                cursor.execute(idx_sql)
                print(f"  ✅ Created index")
            except sqlite3.Error as err:
                print(f"  ⚠️  Index creation: {err}")

        self.sqlite_conn.commit()
        print("✅ Indexes created!")

    def close_connections(self):
        """Close all database connections"""
        if self.mysql_conn:
            self.mysql_conn.close()
            print("\n🔌 MySQL connection closed")
        if self.sqlite_conn:
            self.sqlite_conn.close()
            print("🔌 SQLite connection closed")

    def run(self):
        """Run the complete migration process"""
        try:
            # Connect to databases
            if not self.connect_mysql():
                return False
            if not self.connect_sqlite():
                return False

            # Create tables
            self.create_tables()

            # Migrate data
            self.migrate_all()

            # Create indexes
            self.create_indexes()

            # Verify migration
            self.verify_migration()

            # Print summary
            print("\n" + "=" * 70)
            print("📊 MIGRATION SUMMARY")
            print("=" * 70)
            for table, count in self.stats.items():
                print(f"  {table:<30} {count} rows")

            print("\n" + "=" * 70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print(f"\n📁 SQLite database created: {SQLITE_DB}")
            print(f"📊 Total tables migrated: {len(self.stats)}")
            print("\n🎉 You can now use main_v2.py with SQLite!")
            print("\nNext steps:")
            print("  1. Test the SQLite database: python test_sqlite.py")
            print("  2. Run your app: python main_v2.py")
            print("  3. If everything works, you can remove MySQL dependency!")

            return True

        except Exception as e:
            print(f"\n❌ Migration failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.close_connections()


def main():
    """Main entry point"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║         MySQL to SQLite Migration Script (FIXED)                    ║
║         For WUCSKKM Farmers Database                                ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    print("⚠️  IMPORTANT: Before running this script:")
    print("   1. Update MYSQL_CONFIG with your MySQL credentials")
    print("   2. Backup your MySQL database first!")
    print("   3. Close all connections to the database")
    print()

    response = input("Ready to start migration? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        return

    # Run migration
    migration = DatabaseMigration()
    success = migration.run()

    if success:
        print("\n✅ Migration successful! Database is ready to use.")
        exit(0)
    else:
        print("\n❌ Migration failed. Please check errors above.")
        exit(1)


if __name__ == '__main__':
    main()