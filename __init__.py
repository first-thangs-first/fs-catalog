import os
from views import app

app.debug = True
app.secret_key = 'super_secret_key'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'