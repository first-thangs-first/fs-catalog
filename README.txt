Place your catalog project in this directory.

# Setup
Used additional google oauth library

sudo pip install --upgrade google-auth google-auth-oauthlib google-auth-httplib2
sudo pip install --upgrade google-api-python-client

- google.oauth2
Run the following command under catalog directory in terminal
```
python models.py
python fill_tables.py
python views.py
```

View from browser at localhost:8080

# Apache Setup

```
root@vagrant:/vagrant/Webapp# sudo su postgres
postgres@vagrant:/vagrant/Webapp$ createdb catalog
postgres@vagrant:/vagrant/Webapp$ psql -s catalog
catalog=# create user catalog password catalog;
catalog=# GRANT ALL PRIVILEGES ON DATABASE catalog TO catalog
```
