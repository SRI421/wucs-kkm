import os, sys

# edit your path below
sys.path.append("/home/wucskkm.helioho.st/httpdocs/");

sys.path.insert(0, os.path.dirname(__file__))
from main import app as application

# set this to something harder to guess
application.secret_key = 'secret'