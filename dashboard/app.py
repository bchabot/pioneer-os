from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import subprocess
import shutil
import os
import json
import psutil

app = Flask(__name__)

# Load Config
CONFIG_FILE = 'config.json'
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"admin_password": "pioneer_admin", "secret_key": "default_secret"}

config = load_config()
app.secret_key = config['secret_key']

# Login Manager Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# --- Helpers ---
def check_internet():
    try:
        subprocess.check_call(['ping', '-c', '1', '8.8.8.8'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_hotspot_status():
    # Check if a connection with type 'wifi' and mode 'ap' is active
    try:
        # Simplistic check: look for an active connection named 'PIONEER_SETUP' or similar
        # A better way is to parse nmcli -t -f NAME,TYPE,ACTIVE connection show
        out = subprocess.check_output(['nmcli', '-t', '-f', 'TYPE,ACTIVE,MODE', 'connection', 'show', '--active']).decode()
        # Look for wifi:yes:ap (This depends on exact nmcli output fields, keep it simple for now)
        # We'll just check if the known hotspot name is active
        out_name = subprocess.check_output(['nmcli', '-t', '-f', 'NAME,ACTIVE', 'connection', 'show']).decode()
        if "PIONEER_SETUP:yes" in out_name:
            return True
        return False
    except:
        return False

def get_installed_apps():
    apps = [
        {"id": "wordpress", "name": "WordPress", "description": "Blog and Website Builder", "port": 8080},
        {"id": "filebrowser", "name": "File Browser", "description": "Web-based File Manager", "port": 8081}
    ]
    # Check if they are running (simple docker check)
    try:
        docker_ps = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}']).decode()
        for app in apps:
            app['installed'] = app['id'] in docker_ps # Very rough check
            # Better check: Does the state file exist? Or check specific container name
    except:
        pass
    return apps

# --- Routes ---

@app.route('/')
def index():
    disk_total, disk_used, disk_free = shutil.disk_usage("/")
    disk_percent = (disk_used / disk_total) * 100
    
    return render_template('index.html', 
                         disk_percent=int(disk_percent),
                         hostname=os.uname()[1],
                         internet=check_internet(),
                         hotspot=get_hotspot_status())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == config['admin_password']:
            login_user(User(1))
            return redirect(url_for('index'))
        else:
            flash('Invalid password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/apps')
@login_required
def apps():
    return render_template('apps.html', apps=get_installed_apps())

@app.route('/network')
@login_required
def network():
    # Get IP info
    try:
        ip_info = subprocess.check_output(['hostname', '-I']).decode().strip()
    except:
        ip_info = "Unknown"
    return render_template('network.html', ip=ip_info, hotspot_active=get_hotspot_status())

@app.route('/docs')
def docs():
    return render_template('docs.html')

# --- API Actions (Protected) ---

@app.route('/api/action', methods=['POST'])
@login_required
def action():
    cmd = request.json.get('command')
    target = request.json.get('target') # For app install/remove
    
    if cmd == 'reboot':
        subprocess.Popen(['shutdown', '-r', 'now'])
        return jsonify({'status': 'rebooting'})
    
    elif cmd == 'shutdown':
        subprocess.Popen(['shutdown', '-h', 'now'])
        return jsonify({'status': 'shutting_down'})
    
    elif cmd == 'toggle_hotspot':
        # Toggle logic
        is_on = get_hotspot_status()
        action = 'down' if is_on else 'up'
        # Assume hotspot connection name is PIONEER_SETUP
        try:
            subprocess.run(['nmcli', 'connection', action, 'PIONEER_SETUP'], check=True)
            return jsonify({'status': 'success', 'new_state': not is_on})
        except:
            return jsonify({'status': 'error'}), 500

    elif cmd == 'install_app':
        # Run Salt State
        # Warning: This blocks. In a real app, use a background task (Celery/Redis or simple Thread)
        # For MVP, we will block or spawn a detatched process
        if target == 'wordpress':
            # subprocess.Popen(['salt-call', '--local', 'state.apply', 'modules.wordpress'])
            pass
        return jsonify({'status': 'installing'})

    return jsonify({'status': 'unknown_command'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)