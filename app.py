import os
import re
import json
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================
# VERİ DOSYASI YOLU
# ============================================
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'accounts.txt')

# ============================================
# ACCOUNTS.TXT OKUMA FONKSİYONU
# ============================================
def load_accounts():
    """accounts.txt dosyasını okur ve liste olarak döndürür"""
    if not os.path.exists(DATA_FILE):
        return []
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    accounts = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            accounts.append(line)
    
    return accounts

# ============================================
# FORMAT DETECTION
# ============================================
def detect_format(line):
    """
    Formatları tespit eder:
    - roblox.com/login:username:password
    - roblox.com/Login:username:password
    - roblox.com/:username:password
    - roblox.com/promocodes:username:password
    """
    patterns = [
        r'roblox\.com/(?:login|Login|NewLogin|promocodes|ko/NewLogin)/?[:]?([^:]+):(.+)$',
        r'roblox\.com/[:]?([^:]+):(.+)$',
        r'roblox\.com/([^:]+):(.+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return {
                'username': match.group(1).strip(),
                'password': match.group(2).strip(),
                'full': line
            }
    
    # Alternatif: sadece username:password formatı
    if ':' in line and not 'roblox.com' in line:
        parts = line.split(':', 1)
        if len(parts) == 2:
            return {
                'username': parts[0].strip(),
                'password': parts[1].strip(),
                'full': line
            }
    
    return None

# ============================================
# SEARCH FONKSİYONU
# ============================================
def search_accounts(query):
    """Verilen query ile accounts.txt'de arama yapar"""
    accounts = load_accounts()
    results = []
    
    query_lower = query.lower().strip()
    
    for line in accounts:
        detected = detect_format(line)
        if not detected:
            continue
        
        # Arama yap
        if (query_lower in detected['username'].lower() or 
            query_lower in detected['password'].lower() or
            query_lower in line.lower()):
            results.append({
                'username': detected['username'],
                'password': detected['password'],
                'full': line,
                'matched_field': 'username' if query_lower in detected['username'].lower() else 'password'
            })
    
    return results

# ============================================
# ANA SAYFA - HTML TEMPLATE
# ============================================
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Roblox Account API</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: #0d0d0d;
            color: #e4e4e7;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            max-width: 800px;
            width: 100%;
            padding: 40px 20px;
        }
        .card {
            background: #1a1a1a;
            border-radius: 16px;
            padding: 40px;
            border: 1px solid #2a2a2a;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        h1 {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #a78bfa, #60a5fa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            color: #71717a;
            font-size: 14px;
            margin-bottom: 30px;
        }
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            background: #22c55e20;
            color: #22c55e;
            border: 1px solid #22c55e30;
            margin-bottom: 20px;
        }
        .search-box {
            display: flex;
            gap: 12px;
            margin-bottom: 30px;
        }
        .search-box input {
            flex: 1;
            padding: 12px 16px;
            border-radius: 10px;
            border: 1px solid #2a2a2a;
            background: #0d0d0d;
            color: #e4e4e7;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        .search-box input:focus {
            border-color: #a78bfa;
        }
        .search-box button {
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            background: linear-gradient(135deg, #a78bfa, #60a5fa);
            color: #fff;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .search-box button:hover {
            transform: scale(1.02);
            box-shadow: 0 4px 20px rgba(167, 139, 250, 0.3);
        }
        .results {
            margin-top: 20px;
        }
        .result-item {
            background: #0d0d0d;
            border: 1px solid #2a2a2a;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 10px;
            transition: border-color 0.3s;
        }
        .result-item:hover {
            border-color: #a78bfa40;
        }
        .result-item .username {
            color: #a78bfa;
            font-weight: 600;
            font-size: 16px;
        }
        .result-item .password {
            color: #fbbf24;
            font-size: 14px;
            font-family: monospace;
        }
        .result-item .full {
            color: #52525b;
            font-size: 12px;
            margin-top: 6px;
            word-break: break-all;
            font-family: monospace;
        }
        .result-item .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            margin-top: 6px;
        }
        .badge-username { background: #a78bfa20; color: #a78bfa; }
        .badge-password { background: #fbbf2420; color: #fbbf24; }
        .empty {
            color: #52525b;
            text-align: center;
            padding: 40px 0;
            font-size: 14px;
        }
        .stats {
            color: #52525b;
            font-size: 12px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #2a2a2a;
            display: flex;
            justify-content: space-between;
        }
        .footer {
            margin-top: 20px;
            text-align: center;
            color: #3a3a3a;
            font-size: 12px;
        }
        @media (max-width: 600px) {
            .card { padding: 20px; }
            .search-box { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🎮 Roblox Account API</h1>
            <p class="subtitle">Search for Roblox accounts in the database</p>
            <span class="status">🟢 Online</span>
            
            <form method="GET" action="/search" class="search-box">
                <input type="text" name="q" placeholder="Search by username or password..." required>
                <button type="submit">🔍 Search</button>
            </form>
            
            <div class="stats">
                <span>📊 Total Accounts: <strong id="totalCount">Loading...</strong></span>
                <span>📅 Updated: <strong id="updateTime">Loading...</strong></span>
            </div>
        </div>
        <div class="footer">
            <span>Powered by VoidOSINT API</span>
        </div>
    </div>
    
    <script>
        fetch('/stats')
            .then(res => res.json())
            .then(data => {
                document.getElementById('totalCount').textContent = data.total || 0;
                document.getElementById('updateTime').textContent = data.updated || 'Never';
            });
    </script>
</body>
</html>
    ''')

# ============================================
# API: SEARCH
# ============================================
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'error': 'Query parameter "q" is required',
            'results': []
        }), 400
    
    results = search_accounts(query)
    
    return jsonify({
        'query': query,
        'total': len(results),
        'results': results,
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# API: STATS
# ============================================
@app.route('/stats')
def stats():
    accounts = load_accounts()
    total = len(accounts)
    
    # Dosya değişiklik zamanı
    mtime = None
    if os.path.exists(DATA_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(DATA_FILE)).strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'total': total,
        'updated': mtime or 'Never'
    })

# ============================================
# API: ACCOUNTS LIST (Sadece username:password)
# ============================================
@app.route('/accounts')
def accounts_list():
    """Tüm hesapları döndürür (sadece username:password)"""
    accounts = load_accounts()
    results = []
    
    for line in accounts:
        detected = detect_format(line)
        if detected:
            results.append({
                'username': detected['username'],
                'password': detected['password']
            })
    
    return jsonify({
        'total': len(results),
        'accounts': results
    })

# ============================================
# API: ACCOUNTS RAW (Orijinal format)
# ============================================
@app.route('/accounts/raw')
def accounts_raw():
    """Tüm hesapları orijinal formatında döndürür"""
    accounts = load_accounts()
    return jsonify({
        'total': len(accounts),
        'accounts': accounts
    })

# ============================================
# API: ACCOUNTS ADD (Yeni hesap ekleme)
# ============================================
@app.route('/accounts/add', methods=['POST'])
def add_account():
    """Yeni hesap ekler (username:password veya full URL formatında)"""
    data = request.get_json()
    if not data or 'account' not in data:
        return jsonify({'error': 'Account data required'}), 400
    
    account = data['account'].strip()
    
    # Format kontrolü
    detected = detect_format(account)
    if not detected:
        return jsonify({'error': 'Invalid account format'}), 400
    
    # Dosyaya ekle
    with open(DATA_FILE, 'a', encoding='utf-8') as f:
        f.write(account + '\n')
    
    return jsonify({
        'success': True,
        'message': 'Account added successfully',
        'account': detected
    })

# ============================================
# API: ACCOUNTS BULK ADD (Toplu ekleme)
# ============================================
@app.route('/accounts/bulk', methods=['POST'])
def bulk_add():
    """Toplu hesap ekler - her satırda bir hesap"""
    data = request.get_json()
    if not data or 'accounts' not in data:
        return jsonify({'error': 'Accounts list required'}), 400
    
    accounts_list = data['accounts']
    if not isinstance(accounts_list, list):
        return jsonify({'error': 'Accounts must be a list'}), 400
    
    added = 0
    failed = []
    
    with open(DATA_FILE, 'a', encoding='utf-8') as f:
        for account in accounts_list:
            account = account.strip()
            if account and detect_format(account):
                f.write(account + '\n')
                added += 1
            else:
                failed.append(account)
    
    return jsonify({
        'success': True,
        'added': added,
        'failed': failed,
        'total': len(accounts_list)
    })

# ============================================
# ERROR HANDLERS
# ============================================
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    # data klasörünü oluştur
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    
    # accounts.txt yoksa oluştur
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            f.write('# Roblox Accounts Database\n')
            f.write('# Format: https://www.roblox.com/login:username:password\n\n')
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
