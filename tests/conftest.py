import sqlite3

import pytest

import main


def seed_test_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE farmers_news (
            id INTEGER PRIMARY KEY,
            headline TEXT,
            text1 TEXT,
            text2 TEXT,
            text3 TEXT
        );

        CREATE TABLE farmers_years (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            years TEXT
        );

        CREATE TABLE farmers_year_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            y TEXT,
            batha REAL,
            kabbu REAL,
            tota REAL,
            mtax REAL
        );

        CREATE TABLE farmers_data (
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
            share TEXT,
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
        );
        """
    )
    conn.execute(
        "INSERT INTO farmers_news (id, headline, text1, text2, text3) VALUES (1, 'News', 'Crops', 'Board', 'Manage News')"
    )

    years = ["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"]
    for year in years:
        conn.execute("INSERT INTO farmers_years (years) VALUES (?)", (year,))
        conn.execute(
            "INSERT INTO farmers_year_data (y, batha, kabbu, tota, mtax) VALUES (?, 1, 1, 1, 1)",
            (year,)
        )

    for index, year in enumerate(years, start=1):
        conn.execute(
            """
            INSERT INTO farmers_data
                (pass, sno, area, batha, kabu, thota, name, first, share, paid, year,
                 crop1, area1, crop2, area2, total, balance, count)
            VALUES
                (?, 'S1', 1, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, 0, 0, 1)
            """,
            (
                index,
                10.0 if year == "2020-2021" else 1.0,
                0.0,
                0.0,
                f"Farmer {index}",
                "0" if year == "2024-2025" else "10",
                index * 100,
                year,
                "other",
                0.0,
                "",
                0.0,
            )
        )

    conn.execute(
        """
        INSERT INTO farmers_data
            (pass, sno, area, batha, kabu, thota, name, first, share, paid, year,
             crop1, area1, crop2, area2, total, balance, count)
        VALUES
            (99, 'S2', 1, 0, 2.20, 0.10, 'Latest Farmer', 1, '25', 250, '2024-2025',
             'beans', 0.20, 'rice', 5.00, 0, 0, 1)
        """
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "wucskkm-test.db"
    seed_test_db(db_path)
    monkeypatch.setattr(main, "DB_PATH", str(db_path))
    main.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    return main.app


@pytest.fixture()
def client(app):
    return app.test_client()
