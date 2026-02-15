"""
Export Database to CSV Files
Extracts all data from SQLite database and saves as CSV files
These CSV files can be pushed to GitHub for data portability
"""

import sqlite3
import csv
import os
from datetime import datetime


def export_database_to_csv(db_path='wucskkm.db', output_dir='data'):
    """
    Export all tables from SQLite database to CSV files.
    
    Args:
        db_path: Path to the SQLite database
        output_dir: Directory to store CSV files
    """
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"✓ Created directory: {output_dir}/")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    print(f"\n{'='*60}")
    print(f"Exporting Database to CSV Files")
    print(f"{'='*60}\n")
    print(f"📁 Database: {db_path}")
    print(f"📂 Output: {output_dir}/")
    print()
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    if not tables:
        print("❌ No tables found in database")
        conn.close()
        return
    
    print(f"Found {len(tables)} tables to export:\n")
    
    exported_count = 0
    total_rows = 0
    
    for table_name in tables:
        try:
            # Get all data from table
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            if len(rows) == 0:
                print(f"⊘ {table_name:25s} - EMPTY (skipped)")
                continue
            
            # Get column names
            column_names = [description[0] for description in cursor.description]
            
            # Write to CSV
            csv_filename = os.path.join(output_dir, f"{table_name}.csv")
            
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(column_names)
                
                # Write data rows
                for row in rows:
                    # Convert Row object to list, handling BLOB data
                    row_data = []
                    for i, value in enumerate(row):
                        if isinstance(value, bytes):
                            # For BLOB data, store as base64 or indicate it's binary
                            import base64
                            row_data.append(f"BLOB:{base64.b64encode(value).decode('utf-8')}")
                        else:
                            row_data.append(value)
                    writer.writerow(row_data)
            
            print(f"✓ {table_name:25s} - {len(rows):5d} rows exported")
            exported_count += 1
            total_rows += len(rows)
            
        except Exception as e:
            print(f"❌ {table_name:25s} - Error: {e}")
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✅ Export Complete!")
    print(f"{'='*60}")
    print(f"📊 Tables exported: {exported_count}/{len(tables)}")
    print(f"📊 Total rows: {total_rows}")
    print(f"📁 Location: {os.path.abspath(output_dir)}/")
    print()
    
    # Create a README in the data directory
    readme_path = os.path.join(output_dir, 'README.md')
    with open(readme_path, 'w') as f:
        f.write(f"""# Database Data Export

**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Files in this directory

These CSV files contain the database data that will be imported when `init_db.py` runs.

### Tables Exported:

""")
        for table in tables:
            csv_file = f"{table}.csv"
            if os.path.exists(os.path.join(output_dir, csv_file)):
                f.write(f"- `{csv_file}` - {table} table data\n")

        f.write(f"""
## How to use

1. **Push to GitHub:** These CSV files can be safely committed to Git
2. **Deploy anywhere:** Clone your repo on any server
3. **Auto-import:** Run `python main.py` - database will be created and data imported automatically

## Updating data

To update the CSV files after making changes to the database:

```bash
python export_data.py
```

This will overwrite the CSV files with current database data.

## Note

- BLOB data (images) is stored as base64-encoded strings with `BLOB:` prefix
- Empty tables are not exported
- All data is UTF-8 encoded
""")

    print(f"✓ Created README.md in {output_dir}/")
    print()


def create_gitignore_for_data(output_dir='data'):
    """Create a .gitignore file to ensure CSV files are tracked"""
    gitignore_path = os.path.join(output_dir, '.gitkeep')
    with open(gitignore_path, 'w') as f:
        f.write("# This file ensures the data directory is tracked in Git\n")
    print(f"✓ Created .gitkeep in {output_dir}/")


if __name__ == '__main__':
    """
    Run this script to export your current database to CSV files
    """
    print("\n" + "="*60)
    print("DATABASE TO CSV EXPORTER")
    print("="*60 + "\n")

    DB_FILE = 'wucskkm.db'
    DATA_DIR = 'data'

    # Check if database exists
    if not os.path.exists(DB_FILE):
        print(f"❌ Database file '{DB_FILE}' not found!")
        print(f"ℹ️  Make sure you're running this from the directory containing {DB_FILE}")
        exit(1)

    # Ask for confirmation
    print(f"This will export all data from '{DB_FILE}' to CSV files in '{DATA_DIR}/'")
    response = input("\nContinue? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        export_database_to_csv(DB_FILE, DATA_DIR)
        create_gitignore_for_data(DATA_DIR)

        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("="*60)
        print(f"1. Review CSV files in '{DATA_DIR}/' directory")
        print(f"2. Add to Git: git add {DATA_DIR}/")
        print(f"3. Commit: git commit -m 'Add database CSV exports'")
        print(f"4. Push: git push origin main")
        print(f"5. On deployment, init_db.py will import this data automatically!")
        print("="*60 + "\n")
    else:
        print("\n❌ Export cancelled.")