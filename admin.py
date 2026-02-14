"""
Flask-Admin Configuration for WUCSKKM Farmers Database
Provides admin interface at /admin route using flask-admin
"""

from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask import session, redirect, url_for, flash
from sqlalchemy import Column, Integer, Float, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import os

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), 'wucskkm.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()


# Define Models
class FarmersNews(Base):
    __tablename__ = 'farmers_news'
    id = Column(Integer, primary_key=True)
    headline = Column(Text)
    text1 = Column(Text)
    text2 = Column(Text)
    text3 = Column(Text)

    def __repr__(self):
        return f'<News {self.id}: {self.headline}>'


class FarmersDocument(Base):
    __tablename__ = 'farmers_document'
    id = Column(Integer, primary_key=True)
    data = Column(Text)
    link = Column(Text)
    title = Column(Text)
    filename = Column(Text)

    def __repr__(self):
        return f'<Document {self.id}: {self.title}>'


class FarmersBoard(Base):
    __tablename__ = 'farmers_board'
    id = Column(Integer, primary_key=True)
    data = Column(Text)
    content = Column(Text)

    def __repr__(self):
        return f'<Board {self.id}: {self.content}>'


class FarmersCrops(Base):
    __tablename__ = 'farmers_crops'
    id = Column(Integer, primary_key=True)
    data = Column(Text)
    content = Column(Text)

    def __repr__(self):
        return f'<Crop {self.id}: {self.content}>'


class FarmersGallery(Base):
    __tablename__ = 'farmers_gallery'
    id = Column(Integer, primary_key=True)
    data = Column(Text)
    content = Column(Text)

    def __repr__(self):
        return f'<Gallery {self.id}: {self.content}>'


class FarmersSociety(Base):
    __tablename__ = 'farmers_society'
    id = Column(Integer, primary_key=True)
    data = Column(Text)

    def __repr__(self):
        return f'<Society {self.id}>'


class FarmersMapData(Base):
    __tablename__ = 'farmers_map_data'
    id = Column(Integer, primary_key=True)
    mapid = Column(Integer)
    name = Column(Text)
    pass_ = Column('pass', Integer)
    sno = Column(Text)
    area = Column(Float)

    def __repr__(self):
        return f'<MapData {self.id}: {self.name}>'


class FarmersYears(Base):
    __tablename__ = 'farmers_years'
    id = Column(Integer, primary_key=True)
    years = Column(Text)

    def __repr__(self):
        return f'<Year {self.years}>'


class FarmersYearData(Base):
    __tablename__ = 'farmers_year_data'
    id = Column(Integer, primary_key=True)
    y = Column(Text)
    batha = Column(Float)
    kabbu = Column(Float)
    tota = Column(Float)
    mtax = Column(Float)

    def __repr__(self):
        return f'<YearData {self.y}>'


class FarmersData(Base):
    __tablename__ = 'farmers_data'
    id = Column(Integer, primary_key=True)
    pass_ = Column('pass', Integer)
    sno = Column(Text)
    area = Column(Float)
    batha = Column(Float)
    bkara = Column(Float)
    kabu = Column(Float)
    kkara = Column(Float)
    thota = Column(Float)
    tkara = Column(Float)
    wtax = Column(Float)
    mtax = Column(Float)
    t1 = Column(Float)
    bal = Column(Float)
    t2 = Column(Float)
    name = Column(Text)
    first = Column(Integer)
    share = Column(Integer)
    paid = Column(Float)
    year = Column(Text)
    old = Column(Float)
    rt = Column(Float)
    total = Column(Float)
    balance = Column(Float)
    count = Column(Integer)
    village = Column(Text)
    crop1 = Column(Text)
    area1 = Column(Float)
    kara1 = Column(Float)
    crop2 = Column(Text)
    area2 = Column(Float)
    kara2 = Column(Float)
    pp = Column(Text)
    phone = Column(Text)

    def __repr__(self):
        return f'<FarmerData {self.id}: {self.name} (Pass: {self.pass_})>'


# Custom ModelView with Authentication
class SecureModelView(ModelView):
    """Base ModelView that requires login"""

    def is_accessible(self):
        return session.get('logged_in', False)

    def inaccessible_callback(self, name, **kwargs):
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('home'))

    # Pagination
    page_size = 50
    can_set_page_size = True

    # Export
    can_export = True
    export_types = ['csv', 'xlsx']

    # Display
    column_display_pk = True


# News Admin
class NewsAdmin(SecureModelView):
    column_list = ['id', 'headline', 'text1']
    column_searchable_list = ['headline', 'text1']
    column_filters = ['id', 'headline']
    column_editable_list = ['headline']

    form_columns = ['headline', 'text1', 'text2', 'text3']

    column_labels = {
        'headline': 'Headline',
        'text1': 'Text Section 1',
        'text2': 'Text Section 2',
        'text3': 'Text Section 3'
    }


# Document Admin
class DocumentAdmin(SecureModelView):
    column_list = ['id', 'title', 'filename', 'link']
    column_searchable_list = ['title', 'filename']
    column_filters = ['id', 'title', 'filename']
    column_editable_list = ['title']

    # Don't show data field
    column_exclude_list = ['data']
    form_excluded_columns = ['data']

    column_labels = {
        'title': 'Document Title',
        'filename': 'File Name',
        'link': 'File Path'
    }


# Board Admin
class BoardAdmin(SecureModelView):
    column_list = ['id', 'content']
    column_searchable_list = ['content']
    column_filters = ['id', 'content']

    column_exclude_list = ['data']
    form_excluded_columns = ['data']


# Crops Admin
class CropsAdmin(SecureModelView):
    column_list = ['id', 'content']
    column_searchable_list = ['content']
    column_filters = ['id', 'content']

    column_exclude_list = ['data']
    form_excluded_columns = ['data']


# Gallery Admin
class GalleryAdmin(SecureModelView):
    column_list = ['id', 'content']
    column_searchable_list = ['content']
    column_filters = ['id', 'content']

    column_exclude_list = ['data']
    form_excluded_columns = ['data']


# Society Admin
class SocietyAdmin(SecureModelView):
    column_list = ['id']
    column_filters = ['id']

    column_exclude_list = ['data']
    form_excluded_columns = ['data']


# Map Data Admin
class MapDataAdmin(SecureModelView):
    column_list = ['id', 'mapid', 'pass_', 'name', 'sno', 'area']
    column_searchable_list = ['name', 'sno']
    column_filters = ['mapid', 'pass_', 'name']
    column_editable_list = ['name', 'area']
    column_sortable_list = ['id', 'mapid', 'pass_', 'name', 'area']

    column_labels = {
        'mapid': 'Map ID',
        'pass_': 'Pass Number',
        'name': 'Village/Name',
        'sno': 'Survey Number',
        'area': 'Area (acres)'
    }


# Years Admin
class YearsAdmin(SecureModelView):
    column_list = ['id', 'years']
    column_searchable_list = ['years']
    column_filters = ['id', 'years']
    column_sortable_list = ['id', 'years']

    column_labels = {
        'years': 'Year Period'
    }


# Year Data Admin
class YearDataAdmin(SecureModelView):
    column_list = ['id', 'y', 'batha', 'kabbu', 'tota', 'mtax']
    column_searchable_list = ['y']
    column_filters = ['y']
    column_editable_list = ['batha', 'kabbu', 'tota', 'mtax']
    column_sortable_list = ['id', 'y', 'batha', 'kabbu', 'tota', 'mtax']

    column_labels = {
        'y': 'Year',
        'batha': 'Batha Price',
        'kabbu': 'Kabbu Price',
        'tota': 'Tota Price',
        'mtax': 'M-Tax'
    }


# Farmers Data Admin
class FarmersDataAdmin(SecureModelView):
    # Show most important columns
    column_list = [
        'id', 'pass_', 'name', 'year', 'village',
        'area', 'total', 'paid', 'balance', 'first'
    ]

    column_searchable_list = ['name', 'year', 'village', 'sno']
    column_filters = ['pass_', 'year', 'name', 'first', 'village']
    column_editable_list = ['name', 'paid', 'balance']
    column_sortable_list = [
        'id', 'pass_', 'name', 'year', 'village',
        'area', 'total', 'paid', 'balance', 'first'
    ]

    # Details view shows all columns
    column_details_list = [
        'id', 'pass_', 'name', 'year', 'first', 'share',
        'sno', 'area', 'village',
        'batha', 'bkara', 'kabu', 'kkara', 'thota', 'tkara',
        'wtax', 'mtax', 't1', 'bal', 't2',
        'crop1', 'area1', 'kara1', 'crop2', 'area2', 'kara2',
        'rt', 'old', 'total', 'paid', 'balance', 'count',
        'pp', 'phone'
    ]

    column_labels = {
        'pass_': 'Pass Number',
        'name': 'Farmer Name',
        'year': 'Year',
        'first': 'Primary Record',
        'share': 'Share',
        'sno': 'Survey Number',
        'area': 'Total Area',
        'village': 'Village',
        'batha': 'Batha Area',
        'bkara': 'Batha Kara',
        'kabu': 'Kabu Area',
        'kkara': 'Kabu Kara',
        'thota': 'Thota Area',
        'tkara': 'Thota Kara',
        'wtax': 'Water Tax',
        'mtax': 'Maintenance Tax',
        't1': 'Total Tax 1',
        'bal': 'Balance',
        't2': 'Total Tax 2',
        'crop1': 'Crop 1',
        'area1': 'Crop 1 Area',
        'kara1': 'Crop 1 Kara',
        'crop2': 'Crop 2',
        'area2': 'Crop 2 Area',
        'kara2': 'Crop 2 Kara',
        'rt': 'Running Total',
        'old': 'Old Balance',
        'total': 'Total Amount',
        'paid': 'Amount Paid',
        'balance': 'Outstanding Balance',
        'count': 'Record Count',
        'pp': 'PP',
        'phone': 'Phone Number'
    }

    # Format currency columns
    column_formatters = {
        'total': lambda v, c, m, p: f"₹{m.total:.2f}" if m.total else "₹0.00",
        'paid': lambda v, c, m, p: f"₹{m.paid:.2f}" if m.paid else "₹0.00",
        'balance': lambda v, c, m, p: f"₹{m.balance:.2f}" if m.balance else "₹0.00",
    }


# Simple Custom Admin Index
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return session.get('logged_in', False)

    def inaccessible_callback(self, name, **kwargs):
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('home'))


def init_admin(app):
    """Initialize Flask-Admin with the Flask app"""

    # Create tables if they don't exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create tables: {e}")

    # Create admin - uses default index view
    admin = Admin(
        app,
        name='WUCSKKM Admin',
        index_view=MyAdminIndexView()
    )

    # Add model views
    admin.add_view(NewsAdmin(FarmersNews, db_session, name='News'))
    admin.add_view(DocumentAdmin(FarmersDocument, db_session, name='Documents'))
    admin.add_view(BoardAdmin(FarmersBoard, db_session, name='Notice Board'))
    admin.add_view(CropsAdmin(FarmersCrops, db_session, name='Crops'))
    admin.add_view(GalleryAdmin(FarmersGallery, db_session, name='Gallery'))
    admin.add_view(SocietyAdmin(FarmersSociety, db_session, name='Society Info'))
    admin.add_view(MapDataAdmin(FarmersMapData, db_session, name='Map Data'))
    admin.add_view(YearsAdmin(FarmersYears, db_session, name='Years'))
    admin.add_view(YearDataAdmin(FarmersYearData, db_session, name='Year Pricing'))
    admin.add_view(FarmersDataAdmin(FarmersData, db_session, name='Farmers Data'))

    # Setup teardown
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    return admin