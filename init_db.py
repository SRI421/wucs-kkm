"""
Database Initialization Script for WUCSKKM Farmers Application
Creates SQLite database with all required tables and imports data from CSV files
"""

import sqlite3
import os
import csv
import base64


def init_database(db_path='wucskkm.db'):
    """
    Initialize the SQLite database with all required tables.
    
    Args:
        db_path: Path to the database file
    """
    print(f"Initializing database at: {db_path}")
    
    # Connect to database (creates file if doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # =====================================================
        # TABLE 1: farmers_news
        # =====================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                headline TEXT,
                text1 TEXT,
                text2 TEXT,
                text3 TEXT
            )
        """)
        print("✓ Created table: farmers_news")
        
        # =====================================================
        # TABLE 2: farmers_years
        # =====================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers_years (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                years TEXT NOT NULL UNIQUE
            )
        """)
        print("✓ Created table: farmers_years")
        
        # =====================================================
        # TABLE 3: farmers_year_data
        # =====================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers_year_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                y TEXT NOT NULL,
                batha REAL,
                kabbu REAL,
                tota REAL,
                mtax REAL,
                UNIQUE(y)
            )
        """)
        print("✓ Created table: farmers_year_data")
        
        # =====================================================
        # TABLE 4: farmers_data
        # =====================================================
        cursor.execute("""
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
                name TEXT,
                share TEXT,
                year TEXT,
                first INTEGER DEFAULT 0,
                paid REAL DEFAULT 0,
                bal REAL DEFAULT 0,
                t2 REAL,
                old REAL DEFAULT 0,
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
        """)
        print("✓ Created table: farmers_data")

        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_farmers_data_pass_year 
            ON farmers_data(pass, year)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_farmers_data_year_first 
            ON farmers_data(year, first)
        """)

        # =====================================================
        # TABLE 5: farmers_document
        # =====================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers_document (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data BLOB,
                link TEXT,
                title TEXT,
                filename TEXT
            )
        """)
        print("✓ Created table: farmers_document")

        # =====================================================
        # TABLE 6: farmers_board
        # =====================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers_board (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data BLOB,
                content TEXT
            )
        """)
        print("✓ Created table: farmers_board")

        # =====================================================
        # TABLE 7: farmers_crops
        # =====================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers_crops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data BLOB,
                content TEXT
            )
        """)
        print("✓ Created table: farmers_crops")

        # =====================================================
        # TABLE 8: farmers_gallery
        # =====================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers_gallery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data BLOB,
                content TEXT
            )
        """)
        print("✓ Created table: farmers_gallery")

        # =====================================================
        # TABLE 9: farmers_society
        # =====================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers_society (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data BLOB
            )
        """)
        print("✓ Created table: farmers_society")

        # =====================================================
        # TABLE 10: farmers_map_data
        # =====================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers_map_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mapid TEXT,
                name TEXT,
                pass INTEGER,
                sno TEXT,
                area REAL
            )
        """)
        print("✓ Created table: farmers_map_data")

        # Create index for map data
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_farmers_map_data_pass 
            ON farmers_map_data(pass)
        """)

        # Commit table creation
        conn.commit()
        print("\n✅ All tables created successfully!")

        # =====================================================
        # IMPORT DATA FROM CSV FILES
        # =====================================================
        import_data_from_csv(conn, cursor)

        # Display summary
        cursor.execute("""
            SELECT COUNT(*) as table_count 
            FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        table_count = cursor.fetchone()[0]

        print(f"\n{'='*60}")
        print(f"✅ Database initialized successfully!")
        print(f"{'='*60}")
        print(f"📁 Database location: {os.path.abspath(db_path)}")
        print(f"📊 Total tables: {table_count}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def import_data_from_csv(conn, cursor, data_dir='data'):
    """
    Import data from CSV files into database tables.

    Args:
        conn: Database connection
        cursor: Database cursor
        data_dir: Directory containing CSV files
    """

    if not os.path.exists(data_dir):
        print(f"\nℹ️  No '{data_dir}/' directory found - skipping data import")
        print(f"ℹ️  Database created with empty tables")

        # Insert default news entry only if no data directory
        cursor.execute("""
            INSERT INTO farmers_news (id, headline, text1, text2, text3) 
            SELECT 1, 'Welcome to WUCSKKM', 
                   'Latest updates and news will appear here.',
                   'Stay tuned for more information.',
                   'Thank you for visiting.'
            WHERE NOT EXISTS (SELECT 1 FROM farmers_news WHERE id = 1)
        """)
        conn.commit()
        return

    print(f"\n{'='*60}")
    print(f"Importing Data from CSV Files")
    print(f"{'='*60}\n")

    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]

    if not csv_files:
        print(f"⚠️  No CSV files found in '{data_dir}/' - database will be empty")
        return

    imported_count = 0
    total_rows = 0

    for csv_file in sorted(csv_files):
        table_name = csv_file[:-4]  # Remove .csv extension
        csv_path = os.path.join(data_dir, csv_file)

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                headers = next(csv_reader)  # Get column names
                rows = list(csv_reader)

                if len(rows) == 0:
                    print(f"⊘ {table_name:25s} - Empty CSV (skipped)")
                    continue

                # Prepare INSERT statement
                placeholders = ','.join(['?' for _ in headers])
                columns = ','.join(headers)
                insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

                # Process and insert rows
                processed_rows = []
                for row in rows:
                    processed_row = []
                    for value in row:
                        # Handle BLOB data
                        if isinstance(value, str) and value.startswith('BLOB:'):
                            # Decode base64 BLOB data
                            blob_data = base64.b64decode(value[5:])  # Remove 'BLOB:' prefix
                            processed_row.append(blob_data)
                        elif value == '':
                            # Handle empty strings as NULL for numeric fields
                            processed_row.append(None)
                        else:
                            processed_row.append(value)
                    processed_rows.append(tuple(processed_row))

                # Insert data
                cursor.executemany(insert_sql, processed_rows)
                conn.commit()

                print(f"✓ {table_name:25s} - {len(rows):5d} rows imported")
                imported_count += 1
                total_rows += len(rows)

        except Exception as e:
            print(f"❌ {table_name:25s} - Error: {e}")
            conn.rollback()

    if imported_count > 0:
        print(f"\n{'='*60}")
        print(f"✅ Data Import Complete!")
        print(f"{'='*60}")
        print(f"📊 Files imported: {imported_count}/{len(csv_files)}")
        print(f"📊 Total rows: {total_rows}")
        print(f"{'='*60}\n")


def check_database_integrity(db_path='wucskkm.db'):
    """
    Check if database exists and has all required tables.

    Returns:
        bool: True if database is properly initialized, False otherwise
    """
    if not os.path.exists(db_path):
        return False

    required_tables = [
        'farmers_news',
        'farmers_years',
        'farmers_year_data',
        'farmers_data',
        'farmers_document',
        'farmers_board',
        'farmers_crops',
        'farmers_gallery',
        'farmers_society',
        'farmers_map_data'
    ]

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        missing_tables = set(required_tables) - set(existing_tables)

        if missing_tables:
            print(f"⚠️  Missing tables: {', '.join(missing_tables)}")
            return False

        return True

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False


if __name__ == '__main__':
    """
    Run this script directly to initialize the database
    """
    print("=" * 60)
    print("WUCSKKM Database Initialization")
    print("=" * 60)
    print()

    DB_FILE = 'wucskkm.db'

    # Check if database already exists
    if os.path.exists(DB_FILE):
        print(f"⚠️  Database file '{DB_FILE}' already exists!")
        response = input("Do you want to recreate it? (yes/no): ").strip().lower()

        if response in ['yes', 'y']:
            print(f"🗑️  Removing existing database...")
            os.remove(DB_FILE)
            init_database(DB_FILE)
        else:
            print("ℹ️  Keeping existing database. Checking integrity...")
            if check_database_integrity(DB_FILE):
                print("✅ Database is properly initialized!")
            else:
                print("❌ Database is missing some tables. Please recreate it.")
    else:
        # Create new database
        init_database(DB_FILE)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)