import os
import sys

activate_this = '/usr/share/flask_rdm_web_service_ec/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

sys.stdout = sys.stderr

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))

sys.path.append('/usr/share/flask_rdm_web_service_ec/')

from run import app as application