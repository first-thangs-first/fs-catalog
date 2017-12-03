from models import Base, User, Category, CatalogItem
from flask import (Flask, jsonify, request, url_for, abort, g,
    render_template, redirect, flash)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine, desc

from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

engine = create_engine('sqlite:///catalog.db')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
app = Flask(__name__)

# helpers to be moved to separate class
def get_category_by_name(category_name):
    for c in session.query(Category).all():
        if c.name.lower() == category_name.lower():
            return c
    return None

# routes
@app.route('/')
def index():
    categories = session.query(Category).all()
    latest_items = session.query(CatalogItem).order_by(desc(CatalogItem.id))[0:10]
    logged_in = True
    return render_template('catalogs.html', items=latest_items, categories=categories, logged_in=logged_in)

@app.route('/catalog/category/<category_id>/items')
def list_category(category_id):
    categories = session.query(Category).all()
    items = session.query(CatalogItem).filter_by(category_id=category_id).all()
    category = session.query(Category).filter_by(id=category_id).one()
    return render_template('items.html', categories=categories, items=items, category=category)

@app.route('/catalog/category/<category_id>/item/<item_id>')
def show_item(category_id, item_id):
    catalog_item = session.query(CatalogItem).filter_by(category_id=category_id, id=item_id).one()
    return render_template('detailed-item.html', item=catalog_item)

@app.route('/catalog/item/add', methods=["GET", "POST"])
def add_item():
    categories = session.query(Category).all()
    if request.method == "POST":
        if request.form['name'] and request.form['description']:    
            item = CatalogItem(name=request.form['name'])
            item.description = request.form['description']
            item.category_id = get_category_by_name(request.form['category']).id
            session.add(item)
            session.commit()
            return redirect(url_for('show_item', category_id=item.category_id, item_id=item.id))
        else:
            flash("Can not have empty name or description")
            return render_template("add.html",
                                   name=request.form['name'],
                                   description=request.form['description'],
                                   prev_selected_category=request.form['category'],
                                   categories=categories)
    return render_template('add.html', categories=categories)

@app.route('/catalog/item/<item_id>/edit', methods=["GET","POST"])
def edit_item(item_id):
    item = session.query(CatalogItem).filter_by(id=item_id).one()
    if request.method == 'POST':
        if (not request.form['name']) or (not request.form['description']):
           flash('Can not have empty name or description')
           return redirect(url_for('edit_item',item_id=item_id))
        category = get_category_by_name(request.form['category'])
        item.name = request.form['name']
        item.description = request.form['description']
        item.category_id = category.id
        session.add(item)
        session.commit()
        return redirect(url_for('show_item', category_id=category.id, item_id=item_id))
    categories = session.query(Category).all()
    return render_template('edit.html',item=item, categories=categories)

@app.route('/catalog/item/<item_id>/delete',methods=["GET","POST"])
def delete_item(item_id):
    item = session.query(CatalogItem).filter_by(id=item_id).one()
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        return redirect(url_for('list_category', category_id=item.category_id))
    return render_template('delete.html', item=item)

@app.route('/api/v1.0/catalogs')
def api_list_catalogs():
    return 'listing all items for catalogs api'

if __name__ == '__main__':
    app.debug = True
    app.secret_key = 'super_secret_key'
    #app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    app.run(host='0.0.0.0', port=8000)