import sys, os
sys.path.append("/vagrant/Webapp")
os.chdir("/vagrant/Webapp/catalog")
from catalog import app as application
