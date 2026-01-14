from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import subprocess
import shutil
import os
import json
import psutil
import sys

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
    try:
        # Check if PIONEER_SETUP is active
        out_name = subprocess.check_output(['nmcli', '-t', '-f', 'NAME,ACTIVE', 'connection', 'show']).decode()
        if "PIONEER_SETUP:yes" in out_name:
            return True
        return False
    except Exception as e:
        print(f"Error checking hotspot: {e}", file=sys.stderr)
        return False

def ensure_hotspot_exists():
    """Creates the hotspot connection if it doesn't exist."""
    try:
        # Check if connection exists (active or not)
        out = subprocess.check_output(['nmcli', '-t', '-f', 'NAME', 'connection', 'show']).decode()
        if "PIONEER_SETUP" not in out:
            print("Creating Hotspot PIONEER_SETUP...", file=sys.stderr)
            # Try to find a wireless interface
            iface = "wlan0" # Default fallback
            try:
                 # Find first wireless device
                devs = subprocess.check_output(['nmcli', '-t', '-f', 'DEVICE,TYPE', 'device']).decode().split('\n')
                for line in devs:
                    if ':wifi' in line:
                        iface = line.split(':')[0]
                        break
            except:
                pass
            
            subprocess.check_call([
                'nmcli', 'con', 'add', 'type', 'wifi', 'ifname', iface, 'con-name', 'PIONEER_SETUP',
                'autoconnect', 'yes', 'ssid', 'PIONEER_SETUP'
            ])
            subprocess.check_call([
                'nmcli', 'con', 'modify', 'PIONEER_SETUP', '802-11-wireless.mode', 'ap',
                '802-11-wireless.band', 'bg', 'ipv4.method', 'shared'
            ])
            subprocess.check_call([
                'nmcli', 'con', 'modify', 'PIONEER_SETUP', 'wifi-sec.key-mgmt', 'wpa-psk',
                'wifi-sec.psk', 'pioneer123'
            ])
            return True
    except Exception as e:
        print(f"Failed to create hotspot: {e}", file=sys.stderr)
        return False

def get_installed_apps():
    # Assuming standard ports. In production, read from docker compose labels.
    hostname = os.uname()[1]
    apps = [
        {
            "id": "wordpress", 
            "name": "WordPress", 
            "description": "Blog and Website Builder", 
            "port": 8080,
            "url": f"http://{hostname}.local:8080", 
            "login_info": "Default User: user / bitnami (Check logs if changed)"
        },
        # {"id": "filebrowser", "name": "File Browser", "description": "Web-based File Manager", "port": 8081}
    ]
    try:
        # Check running containers
        docker_ps = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}']).decode()
        for app in apps:
            # Check if container is running OR if data directory exists (installed but stopped)
            is_running = app['id'] in docker_ps
            is_installed = os.path.exists(f"/opt/pioneer/{app['id']}")
            app['installed'] = is_installed
            app['running'] = is_running
    except Exception as e:
        print(f"Error checking apps: {e}", file=sys.stderr)
        pass
    return apps

def read_dhcp_leases():
    leases = []
    lease_file = '/var/lib/misc/dnsmasq.leases'
    if os.path.exists(lease_file):
        with open(lease_file, 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 4:
                    leases.append({
                        'mac': parts[1],
                        'ip': parts[2],
                        'hostname': parts[3]
                    })
    return leases

def read_static_hosts():
    hosts = []
    host_file = '/etc/dnsmasq.d/pioneer-hosts.conf'
    if os.path.exists(host_file):
        with open(host_file, 'r') as f:
            for line in f:
                if line.startswith('dhcp-host='):
                    # Format: dhcp-host=mac,ip,hostname
                    parts = line.strip().replace('dhcp-host=', '').split(',')
                    if len(parts) >= 2:
                         hosts.append({
                             'mac': parts[0],
                             'ip': parts[1] if len(parts) > 1 else '',
                             'hostname': parts[2] if len(parts) > 2 else ''
                         })
    return hosts

def save_static_host(mac, ip, hostname):
    host_file = '/etc/dnsmasq.d/pioneer-hosts.conf'
    # Read existing
    lines = []
    if os.path.exists(host_file):
        with open(host_file, 'r') as f:
            lines = f.readlines()
    
    # Check if MAC exists and update, else append
    new_line = f"dhcp-host={mac},{ip},{hostname}\n"
    found = False
    for i, line in enumerate(lines):
        if f"dhcp-host={mac}" in line:
            lines[i] = new_line
            found = True
            break
    
    if not found:
        lines.append(new_line)
        
    with open(host_file, 'w') as f:
        f.writelines(lines)
    
    # Restart dnsmasq (or reload)
    subprocess.call(['systemctl', 'restart', 'dnsmasq'])

# --- Routes ---

@app.route('/')
def index():
    try:
        disk_total, disk_used, disk_free = shutil.disk_usage("/")
        disk_percent = (disk_used / disk_total) * 100
    except:
        disk_percent = 0
    
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
    try:
        ip_info = subprocess.check_output(['hostname', '-I']).decode().strip()
    except:
        ip_info = "Unknown"
    return render_template('network.html', ip=ip_info, hotspot_active=get_hotspot_status())

@app.route('/dhcp')
@login_required
def dhcp():
    return render_template('dhcp.html', leases=read_dhcp_leases(), static_hosts=read_static_hosts())

@app.route('/docs')
def docs():
    return render_template('docs.html')

# --- API Actions (Protected) ---

@app.route('/api/action', methods=['POST'])
@login_required
def action():
    cmd = request.json.get('command')
    target = request.json.get('target') # For app install/remove
    data = request.json.get('data') # For DHCP
    
    try:
        if cmd == 'reboot':
            subprocess.Popen(['shutdown', '-r', 'now'])
            return jsonify({'status': 'rebooting'})
        
        elif cmd == 'shutdown':
            subprocess.Popen(['shutdown', '-h', 'now'])
            return jsonify({'status': 'shutting_down'})
        
        elif cmd == 'toggle_hotspot':
            ensure_hotspot_exists()
            is_on = get_hotspot_status()
            action = 'down' if is_on else 'up'
            subprocess.run(['nmcli', 'connection', action, 'PIONEER_SETUP'], check=True)
            return jsonify({'status': 'success', 'new_state': not is_on})

        elif cmd == 'install_app':
            if target == 'wordpress':
                # Run Salt State in background
                subprocess.Popen(['salt-call', '--local', 'state.apply', 'modules.wordpress'])
                return jsonify({'status': 'installing'})
        
        elif cmd == 'start_app':
             if target == 'wordpress':
                # Use up -d to ensure it starts even if not created or just stopped
                res = subprocess.run(['/usr/bin/docker', 'compose', 'up', '-d'], cwd='/opt/pioneer/wordpress', capture_output=True, text=True)
                if res.returncode != 0:
                    raise Exception(f"Docker failed: {res.stderr}")
                return jsonify({'status': 'started'})

        elif cmd == 'stop_app':
             if target == 'wordpress':
                subprocess.run(['docker', 'compose', 'stop'], cwd='/opt/pioneer/wordpress', check=False)
                return jsonify({'status': 'stopped'})

        elif cmd == 'remove_app':
            if target == 'wordpress':
                # Stop container and remove dir (Simple removal)
                # In real prod, we might want to backup data first
                subprocess.run(['docker', 'compose', 'down'], cwd='/opt/pioneer/wordpress', check=False)
                shutil.rmtree('/opt/pioneer/wordpress', ignore_errors=True)
                return jsonify({'status': 'removed'})

        elif cmd == 'add_static_lease':
            save_static_host(data['mac'], data['ip'], data['hostname'])
            return jsonify({'status': 'success'})

    except Exception as e:
        with open('/var/log/pioneer-dashboard.log', 'a') as f:
            f.write(f"Action failed: {str(e)}\n")
        print(f"Action failed: {e}", file=sys.stderr)
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'unknown_command'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
