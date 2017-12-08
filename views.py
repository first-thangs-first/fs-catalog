from models import Base, User, Category, CatalogItem
from flask import (Flask, jsonify, request, url_for, abort, g,
    render_template, redirect, flash)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine, desc

from flask_httpauth import HTTPBasicAuth
import flask, os
## google oauth
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

import httplib2, requests


engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
auth = HTTPBasicAuth()
app = Flask(__name__)

CLIENT_SECRETS_FILE = 'client_secrets.json'
GOOGLE_SCOPES = ['profile', 'email', 'openid']
# TODO helpers to be moved to separate class
def get_category_by_name(category_name):
    for c in session.query(Category).all():
        if c.name.lower() == category_name.lower():
            return c
    return None

def revoke_google_access():
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
                           params={'token': credentials.token},
                           headers={'content-type': 'application/x-www-form-urlencoded'})
    status_code = getattr(revoke, 'status_code')
    return status_code

def get_user():
    user = None
    if 'auth' in flask.session:
        token = flask.session['auth']
        user_id = User.verify_auth_token(token)
        if user_id == 'Signature Expired':
            print 'signature expired, deleting auth and credentials from session'
            del flask.session['auth']
            del flask.session['credentials']
            return None
        if user_id:
            user = session.query(User).filter_by(id=user_id).first()
            return user
    else:
        print 'auth not in session', flask.session
        return user

@auth.verify_password
def verify_password(token, x):
    if 'auth' in flask.session:
        user_id = User.verify_auth_token(token)
        if user_id:
            return True
    return False

# this route is for testing purpose only
@app.route('/token')
def get_token():
    if 'auth' in flask.session:
        return flask.session['auth']
    else:
        return "Sign in first to receive token"
    
# routes
@app.route('/')
def index():
    categories = session.query(Category).all()
    latest_items = session.query(CatalogItem).order_by(desc(CatalogItem.id))[0:10]
    user = get_user()
    return render_template('catalogs.html',
                           items=latest_items,
                           categories=categories,
                           user=user)

@app.route('/login')
def login():
    if 'credentials' in flask.session:
        return 'already logged in'

    # use the clien_secret.json file to identify the application
    # set the scope needed for our app
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, GOOGLE_SCOPES)
    
    # indicate the api server will redirect the user after the user completes authorization
    flow.redirect_uri = url_for('gconnect', _external=True)
    authorization_url, state = flow.authorization_url(
        # Enable offline access so that our app can refresh an access token without
        # re-prompting the user for permission. Recommended by google
        access_type = 'offline',
        # Enable incremental authorization. Recommended
        include_granted_scopes='true')
    # store the state for verification of response
    flask.session['state'] = state
    return redirect(authorization_url)

@app.route('/logout')
def logout():
    if 'credentials' not in flask.session:
        return redirect(url_for('index'))
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])
    revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
                           params={'token': credentials.token},
                           headers={'content-type': 'application/x-www-form-urlencoded'})
    status_code = getattr(revoke, 'status_code')
    if status_code == 200:
        del flask.session['credentials']
        del flask.session['auth']
        return redirect(url_for('index'))
    else:
        return 'error occurred revoking third party authorization'

@app.route('/gconnect')
def gconnect():
    print 'inside gconnect'
    state = flask.session['state']
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=GOOGLE_SCOPES, state=state)
    flow.redirect_uri = flask.url_for('gconnect', _external=True)

    # Use the authentication server's response to fetch the OAuth 2 tokens
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session
    credentials = flow.credentials
    flask.session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes}

    #Get user info, safe first time user to database
    h = httplib2.Http()
    userinfo_url =  "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.token, 'alt':'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    name = data['name']
    email = data['email']
    picture = data['picture']
    user = session.query(User).filter_by(email=email).first()
    if not user:
        user = User(name=name, email=email, picture=picture)
        session.add(user)
        session.commit()
    token = user.generate_auth_token()
    flask.session['auth'] = token

    return flask.redirect(url_for('index'))

@app.route('/catalog/category/<category_id>/items')
def list_category(category_id):
    categories = session.query(Category).all()
    items = session.query(CatalogItem).filter_by(category_id=category_id).all()
    category = session.query(Category).filter_by(id=category_id).one_or_none()
    user = get_user()
    return render_template('items.html', categories=categories, items=items, category=category, user=user)

@app.route('/catalog/category/<category_id>/item/<item_id>')
def show_item(category_id, item_id):
    catalog_item = session.query(CatalogItem).filter_by(category_id=category_id, id=item_id).one_or_none()
    user = get_user()
    return render_template('detailed-item.html', item=catalog_item, user=user)

@app.route('/catalog/item/add', methods=["GET", "POST"])
def add_item():
    user = get_user()
    if not user:
        return redirect(url_for('unauthorized'))
    categories = session.query(Category).all()
    if request.method == "POST":
        if request.form['name'] and request.form['description']:    
            item = CatalogItem(name=request.form['name'])
            item.description = request.form['description']
            item.category_id = get_category_by_name(request.form['category']).id
            item.user_id = user.id
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
    return render_template('add.html', categories=categories, user=user)


@app.route('/unauthorized')
def unauthorized():
    user = get_user()
    if user == 'Signature Expired':
        user = None
    return render_template('unauthorized.html', user=user)

@app.route('/catalog/item/<item_id>/edit', methods=["GET","POST"])
def edit_item(item_id):
    user = get_user()
    if not user:
        print 'user error', user
        return redirect(url_for('unauthorized'))
    item = session.query(CatalogItem).filter_by(id=item_id).one_or_none()
    if item.user_id is not user.id:
        print 'user id not same as created id'
        return redirect(url_for('unauthorized'))
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
    return render_template('edit.html',item=item, categories=categories, user=user)


@app.route('/catalog/item/<item_id>/delete',methods=["GET","POST"])
def delete_item(item_id):
    user = get_user()
    if not user:
        return redirect(url_for('unauthorized'))
    item = session.query(CatalogItem).filter_by(id=item_id).one_or_none()
    if item.user_id is not user.id:
        return redirect(url_for('unauthorized'))
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        return redirect(url_for('list_category', category_id=item.category_id))
    return render_template('delete.html', item=item, user=user)

@app.route('/api/v1.0/catalogs/json')
@auth.login_required
def api_list_catalogs():
    result = {}
    for category in session.query(Category).all():
        result[category.name] = []
        items = session.query(CatalogItem).filter_by(category_id=category.id)
        for item in items:
            result[category.name].append(item.serialize)
    json_result = jsonify(catalogs=result)
    return json_result

# api to search for arbitary category
@app.route('/api/v1.0/catalogs/<category_name>/json')
@auth.login_required
def api_list_category(category_name):
    result = {}
    category = session.query(Category).filter_by(name=category_name.capitalize()).one_or_none()
    if category:
        items = session.query(CatalogItem).filter_by(category_id=category.id)
        result[category.name] = []
        for i in items:
            result[category.name].append(i.serialize)
    json_result = jsonify(result)
    return json_result

# api to search for arbitary item
@app.route('/api/v1.0/catalogs/item/<item_id>/json')
@auth.login_required
def api_list_item(item_id):
    item = session.query(CatalogItem).filter_by(id=item_id).one_or_none()
    json_result = jsonify(item.serialize)
    return json_result

if __name__ == '__main__':
    app.debug = True
    app.secret_key = 'super_secret_key'
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    #app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    app.run(host='0.0.0.0', port=5000)