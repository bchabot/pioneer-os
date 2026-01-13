from flask import Flask, render_template, jsonify, request
import subprocess
import shutil
import os

app = Flask(__name__)

def check_internet():
    try:
        # Ping Google's DNS to check connectivity
        subprocess.check_call(['ping', '-c', '1', '8.8.8.8'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def get_service_status(service_name):
    try:
        output = subprocess.check_output(['systemctl', 'is-active', service_name]).decode().strip()
        return output == 'active'
    except:
        return False

@app.route('/')
def index():
    # Get initial status
    disk_total, disk_used, disk_free = shutil.disk_usage("/")
    disk_percent = (disk_used / disk_total) * 100
    
    return render_template('index.html', 
                         disk_percent=int(disk_percent),
                         hostname=os.uname()[1])

@app.route('/api/status')
def status():
    # Dynamic status updates
    return jsonify({
        'internet': check_internet(),
        'hotspot': False, # Placeholder: Implement actual NMCLI check
        'cockpit': get_service_status('cockpit.socket')
    })

@app.route('/api/action', methods=['POST'])
def action():
    cmd = request.json.get('command')
    
    if cmd == 'reboot':
        subprocess.Popen(['shutdown', '-r', 'now'])
        return jsonify({'status': 'rebooting'})
    
    elif cmd == 'shutdown':
        subprocess.Popen(['shutdown', '-h', 'now'])
        return jsonify({'status': 'shutting_down'})
        
    return jsonify({'status': 'unknown_command'}), 400

if __name__ == '__main__':
    # Run on port 80 for easy access (requires root)
    app.run(host='0.0.0.0', port=80)
