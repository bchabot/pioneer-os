from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import subprocess
import shutil
import os
import json
import psutil
import sys
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Apply ProxyFix to trust X-Forwarded headers (Nginx)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

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

def is_installing(app_id):
    """Checks if a salt-call process is running for the given app_id."""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
            try:
                # Ignore zombie processes (finished but not reaped)
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    continue

                cmdline = proc.info['cmdline']
                if cmdline:
                    cmd_str = " ".join(cmdline)
                    if 'salt-call' in cmd_str and f"modules.{app_id}" in cmd_str:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception:
        pass
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
            "url": f"https://{hostname}.local/", 
            "login_info": "Default User: user / bitnami (Check logs if changed)"
        },
        {
            "id": "portainer", 
            "name": "Portainer", 
            "description": "Advanced App/Container Manager", 
            "port": 9443,
            "url": f"https://{hostname}.local:9443", 
            "login_info": "Create admin user on first login."
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
            installing = is_installing(app['id'])
            
            app['installed'] = is_installed
            app['running'] = is_running
            app['installing'] = installing
            
            # If installing, override installed/running to prevent confusion
            if installing:
                app['installed'] = False
                app['running'] = False
                
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

# --- DNS & DHCP Config Helpers ---
DHCP_CONF = '/etc/dnsmasq.d/pioneer-dhcp.conf'
DNS_CONF = '/etc/dnsmasq.d/pioneer-dns.conf'

def reload_dnsmasq():
    """Reloads dnsmasq configuration safely."""
    try:
        # Check config syntax first
        subprocess.check_call(['dnsmasq', '--test'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Try reload
        subprocess.check_call(['systemctl', 'reload', 'dnsmasq'])
    except subprocess.CalledProcessError as e:
        print(f"Failed to reload dnsmasq: {e}", file=sys.stderr)
        # Fallback to restart if reload fails or isn't supported (though reload is standard)
        try:
             subprocess.check_call(['systemctl', 'restart', 'dnsmasq'])
        except Exception as e2:
             print(f"Failed to restart dnsmasq: {e2}", file=sys.stderr)
             raise Exception("Failed to apply network changes (dnsmasq error)")

def ensure_config_dir():
    if not os.path.exists('/etc/dnsmasq.d'):
        os.makedirs('/etc/dnsmasq.d')

def read_dhcp_reservations():
    res = []
    if os.path.exists(DHCP_CONF):
        with open(DHCP_CONF, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('dhcp-host=') and not line.startswith('#'):
                    # dhcp-host=mac,ip,[hostname]
                    try:
                        parts = line.replace('dhcp-host=', '').split(',')
                        res.append({
                            'mac': parts[0],
                            'ip': parts[1] if len(parts) > 1 else '',
                            'hostname': parts[2] if len(parts) > 2 else ''
                        })
                    except:
                        continue
    return res

def save_dhcp_reservation(mac, ip, hostname=""):
    ensure_config_dir()
    mac = mac.strip()
    ip = ip.strip()
    hostname = hostname.strip()
    
    lines = []
    if os.path.exists(DHCP_CONF):
        with open(DHCP_CONF, 'r') as f:
            lines = f.readlines()
    
    # Format: dhcp-host=MAC,IP,HOSTNAME
    entry = f"dhcp-host={mac},{ip}"
    if hostname:
        entry += f",{hostname}"
    entry += "\n"

    found = False
    for i, line in enumerate(lines):
        if f"dhcp-host={mac}" in line:
            lines[i] = entry
            found = True
            break
    
    if not found:
        lines.append(entry)
        
    with open(DHCP_CONF, 'w') as f:
        f.writelines(lines)
    
    reload_dnsmasq()

def delete_dhcp_reservation(mac):
    if not os.path.exists(DHCP_CONF): return
    mac = mac.strip()
    
    with open(DHCP_CONF, 'r') as f:
        lines = f.readlines()
    
    with open(DHCP_CONF, 'w') as f:
        for line in lines:
            if f"dhcp-host={mac}" not in line:
                f.write(line)
    
    reload_dnsmasq()

def read_dns_records():
    recs = []
    if os.path.exists(DNS_CONF):
        with open(DNS_CONF, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('host-record=') and not line.startswith('#'):
                    try:
                        parts = line.replace('host-record=', '').split(',')
                        if len(parts) >= 2:
                            recs.append({'hostname': parts[0], 'ip': parts[1]})
                    except:
                        continue
    return recs

def save_dns_record(hostname, ip):
    ensure_config_dir()
    hostname = hostname.strip()
    ip = ip.strip()
    
    lines = []
    if os.path.exists(DNS_CONF):
        with open(DNS_CONF, 'r') as f:
            lines = f.readlines()
    
    entry = f"host-record={hostname},{ip}\n"
    
    # Check if hostname exists, update IP
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"host-record={hostname},"):
            lines[i] = entry
            found = True
            break
            
    if not found:
        lines.append(entry)
        
    with open(DNS_CONF, 'w') as f:
        f.writelines(lines)
    
    reload_dnsmasq()

def delete_dns_record(hostname):
    if not os.path.exists(DNS_CONF): return
    hostname = hostname.strip()
    
    with open(DNS_CONF, 'r') as f:
        lines = f.readlines()
    
    with open(DNS_CONF, 'w') as f:
        for line in lines:
            if not line.startswith(f"host-record={hostname},"):
                f.write(line)
    
    reload_dnsmasq()

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
                         hotspot=get_hotspot_status(),
                         apps=get_installed_apps())

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
    # Get detailed interface info
    interfaces = []
    try:
        # Try ip -j first (requires iproute2-json usually, but standard ip usually supports it now)
        # If not, we might need manual parsing. Let's try simple manual parsing of 'ip addr' if -j fails
        # or just basic parsing.
        # Check if json output is supported
        try:
            output = subprocess.check_output(['ip', '-j', 'addr'], stderr=subprocess.DEVNULL).decode()
            data = json.loads(output)
            for iface in data:
                if iface['ifname'] == 'lo': continue
                ipv4 = next((a['local'] for a in iface.get('addr_info', []) if a['family'] == 'inet'), 'No IP')
                interfaces.append({
                    'name': iface['ifname'],
                    'mac': iface.get('address', ''),
                    'ip': ipv4,
                    'state': iface['operstate']
                })
        except:
             # Fallback to simple shell
             output = subprocess.check_output(['ip', '-o', 'addr']).decode()
             for line in output.split('\n'):
                 if 'inet ' in line and ' lo ' not in line:
                     parts = line.split()
                     # 1: lo    inet 127.0.0.1/8 ...
                     interfaces.append({'name': parts[1], 'ip': parts[3].split('/')[0], 'state': 'up', 'mac': 'Unknown'})
    except:
        pass

    return render_template('network.html', 
                         interfaces=interfaces, 
                         hotspot_active=get_hotspot_status(),
                         leases=read_dhcp_leases(), 
                         dhcp_reservations=read_dhcp_reservations(),
                         dns_records=read_dns_records())

@app.route('/docs')
def docs():
    return render_template('docs.html')

# --- API Actions (Protected) ---

@app.route('/api/action', methods=['POST'])
@login_required
def action():
    cmd = request.json.get('command')
    target = request.json.get('target') # For app install/remove
    data = request.json.get('data') # For DHCP/Config
    
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
            
        elif cmd == 'update_hotspot':
            ssid = data.get('ssid')
            password = data.get('password')
            if len(password) < 8:
                raise Exception("Password must be at least 8 characters")
            
            ensure_hotspot_exists()
            subprocess.run(['nmcli', 'con', 'modify', 'PIONEER_SETUP', 'ssid', ssid, 'wifi-sec.psk', password], check=True)
            # Restart connection
            subprocess.run(['nmcli', 'con', 'down', 'PIONEER_SETUP'])
            subprocess.run(['nmcli', 'con', 'up', 'PIONEER_SETUP'])
            return jsonify({'status': 'success'})

        elif cmd == 'set_hostname':
            new_name = data.get('hostname')
            # Validate hostname (alphanumeric, hyphens)
            if not new_name.replace('-', '').isalnum():
                raise Exception("Invalid hostname format")
            
            subprocess.run(['hostnamectl', 'set-hostname', new_name], check=True)
            # Update /etc/hosts to prevent sudo warnings
            subprocess.run(['sed', '-i', f's/127.0.1.1.*/127.0.1.1\t{new_name}/', '/etc/hosts'])
            return jsonify({'status': 'success', 'message': 'Hostname changed. Reboot recommended.'})

        elif cmd == 'update_password':
            new_pass = data.get('password')
            if len(new_pass) < 5:
                 raise Exception("Password too short")
            
            config['admin_password'] = new_pass
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            return jsonify({'status': 'success'})

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
                res = subprocess.run(['/usr/bin/docker', 'compose', 'stop'], cwd='/opt/pioneer/wordpress', capture_output=True, text=True)
                if res.returncode != 0:
                    raise Exception(f"Docker stop failed: {res.stderr}")
                return jsonify({'status': 'stopped'})

        elif cmd == 'remove_app':
            if target == 'wordpress':
                # Stop container and remove dir
                res = subprocess.run(['/usr/bin/docker', 'compose', 'down'], cwd='/opt/pioneer/wordpress', capture_output=True, text=True)
                if res.returncode != 0:
                     # Log but continue cleanup
                     with open('/var/log/pioneer-dashboard.log', 'a') as f:
                        f.write(f"Docker down warning: {res.stderr}\n")
                
                shutil.rmtree('/opt/pioneer/wordpress', ignore_errors=True)
                return jsonify({'status': 'removed'})

        # --- DHCP & DNS Actions ---
        elif cmd == 'add_dhcp_reservation':
            save_dhcp_reservation(data['mac'], data['ip'], data.get('hostname', ''))
            return jsonify({'status': 'success'})

        elif cmd == 'del_dhcp_reservation':
            delete_dhcp_reservation(data['mac'])
            return jsonify({'status': 'success'})

        elif cmd == 'add_dns_record':
            save_dns_record(data['hostname'], data['ip'])
            return jsonify({'status': 'success'})

        elif cmd == 'del_dns_record':
            delete_dns_record(data['hostname'])
            return jsonify({'status': 'success'})

    except Exception as e:
        with open('/var/log/pioneer-dashboard.log', 'a') as f:
            f.write(f"Action failed: {str(e)}\n")
        print(f"Action failed: {e}", file=sys.stderr)
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'unknown_command'}), 400

if __name__ == '__main__':
    # Run on port 5000 (Nginx will proxy to this)
    app.run(host='0.0.0.0', port=5000)
