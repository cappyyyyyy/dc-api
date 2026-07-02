import os
import re
import json
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app)

# ============================================
# VERİ DOSYASI YOLU
# ============================================
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'accounts.txt')

# ============================================
# CACHE SİSTEMİ (Performans için)
# ============================================
class AccountCache:
    def __init__(self):
        self.lines = []
        self.last_modified = 0
        self.lock = threading.Lock()
    
    def load(self):
        """Dosyayı yükler ve cache'ler"""
        with self.lock:
            if not os.path.exists(DATA_FILE):
                return []
            
            # Dosya değişiklik kontrolü
            current_mtime = os.path.getmtime(DATA_FILE)
            if current_mtime == self.last_modified and self.lines:
                return self.lines
            
            try:
                with open(DATA_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            lines.append(line)
                
                self.lines = lines
                self.last_modified = current_mtime
                print(f"✅ Cache yenilendi: {len(lines)} satır yüklendi")
                return lines
                
            except Exception as e:
                print(f"❌ Dosya okuma hatası: {e}")
                return self.lines if self.lines else []
    
    def search(self, query):
        """Cache'de arama yapar"""
        lines = self.load()
        query_lower = query.lower()
        
        results = []
        for line in lines:
            if query_lower in line.lower():
                results.append(line)
        
        return results
    
    def get_stats(self):
        """İstatistikleri döndürür"""
        lines = self.load()
        return {
            'total': len(lines),
            'last_modified': datetime.fromtimestamp(self.last_modified).strftime('%Y-%m-%d %H:%M:%S') if self.last_modified else 'Never'
        }

# Global cache instance
cache = AccountCache()

# ============================================
# ACCOUNTS.TXT OKUMA (Backward compatibility)
# ============================================
def load_accounts():
    """Eski fonksiyon - cache kullanır"""
    return cache.load()

# ============================================
# EVRENSEL FORMAT DETECTION
# ============================================
def detect_format(line):
    """
    Her türlü formatı tespit eder:
    - URL:username:password
    - email:password
    - username:password
    - URL:email:password
    - Herhangi bir format
    """
    if not line or ':' not in line:
        return None
    
    parts = line.split(':')
    
    if len(parts) == 2:
        # username:password veya email:password
        return {
            'username': parts[0].strip(),
            'password': parts[1].strip(),
            'full': line
        }
    
    elif len(parts) >= 3:
        # URL:username:password veya URL:email:password
        # İlk kısım URL olabilir, kalanlar username ve password
        url = parts[0]
        
        # URL'yi kontrol et
        if '://' in url or '.' in url:
            # URL:username:password formatı
            username = ':'.join(parts[1:-1])  # Arasındaki her şey username
            password = parts[-1]
            return {
                'username': username.strip(),
                'password': password.strip(),
                'full': line
            }
        else:
            # Normal username:password formatı ama 3+ parça var (örn: user:pass:extra)
            username = ':'.join(parts[0:-1])
            password = parts[-1]
            return {
                'username': username.strip(),
                'password': password.strip(),
                'full': line
            }
    
    return None

# ============================================
# EVRENSEL SEARCH
# ============================================
def search_accounts(query):
    """Verilen query ile her satırda arama yapar"""
    query_lower = query.lower().strip()
    
    if not query_lower:
        return []
    
    # Cache'den ara
    matched_lines = cache.search(query_lower)
    
    # Detaylı sonuçlar oluştur
    results = []
    for line in matched_lines:
        detected = detect_format(line)
        if detected:
            results.append({
                'line': line,
                'username': detected.get('username', ''),
                'password': detected.get('password', ''),
                'matched': True
            })
        else:
            # Format tespit edilemezse bile satırı göster
            results.append({
                'line': line,
                'username': 'Unknown',
                'password': 'Unknown',
                'matched': True
            })
    
    return results

# ============================================
# ANA SAYFA - HTML TEMPLATE (Güncellendi)
# ============================================
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Universal Account API</title>
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
            max-width: 900px;
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
            background: linear-gradient(135deg, #f472b6, #60a5fa, #a78bfa);
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
            max-height: 500px;
            overflow-y: auto;
        }
        .results::-webkit-scrollbar {
            width: 8px;
        }
        .results::-webkit-scrollbar-track {
            background: #0d0d0d;
            border-radius: 4px;
        }
        .results::-webkit-scrollbar-thumb {
            background: #2a2a2a;
            border-radius: 4px;
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
        .result-item .line {
            color: #e4e4e7;
            font-size: 14px;
            font-family: monospace;
            word-break: break-all;
        }
        .result-item .username {
            color: #f472b6;
            font-weight: 600;
            font-size: 13px;
            margin-top: 4px;
        }
        .result-item .password {
            color: #fbbf24;
            font-size: 13px;
            font-family: monospace;
        }
        .result-item .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            margin-top: 6px;
            background: #a78bfa20;
            color: #a78bfa;
        }
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
        .api-info {
            margin-top: 15px;
            padding: 15px;
            background: #0d0d0d;
            border-radius: 10px;
            border: 1px solid #2a2a2a;
        }
        .api-info code {
            color: #a78bfa;
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
            <h1>🌐 Universal Account API</h1>
            <p class="subtitle">Search any format: URL:user:pass | email:pass | user:pass</p>
            <span class="status">🟢 Online - Universal Search</span>
            
            <form method="GET" action="/search" class="search-box">
                <input type="text" name="q" placeholder="Search any keyword in the database..." required>
                <button type="submit">🔍 Search</button>
            </form>
            
            <div class="api-info">
                <strong>📌 API Endpoints:</strong><br>
                <code>GET /search?q=keyword</code> - Search in all lines<br>
                <code>GET /accounts</code> - List all accounts (parsed)<br>
                <code>GET /accounts/raw</code> - List all raw lines<br>
                <code>POST /accounts/add</code> - Add single account<br>
                <code>POST /accounts/bulk</code> - Bulk add accounts
            </div>
            
            <div class="stats">
                <span>📊 Total Accounts: <strong id="totalCount">Loading...</strong></span>
                <span>📅 Updated: <strong id="updateTime">Loading...</strong></span>
            </div>
        </div>
        <div class="footer">
            <span>Powered by VoidOSINT Universal API</span>
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
# API: SEARCH (Evrensel)
# ============================================
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 1000, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    if not query:
        return jsonify({
            'error': 'Query parameter "q" is required',
            'results': []
        }), 400
    
    results = search_accounts(query)
    
    # Limit ve offset uygula
    total = len(results)
    results = results[offset:offset + limit]
    
    return jsonify({
        'query': query,
        'total': total,
        'limit': limit,
        'offset': offset,
        'results': results,
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# API: STATS (Güncellendi)
# ============================================
@app.route('/stats')
def stats():
    stats_data = cache.get_stats()
    return jsonify(stats_data)

# ============================================
# API: ACCOUNTS LIST (Tüm hesaplar - parse edilmiş)
# ============================================
@app.route('/accounts')
def accounts_list():
    """Tüm hesapları döndürür (parsed)"""
    lines = cache.load()
    results = []
    
    for line in lines:
        detected = detect_format(line)
        if detected:
            results.append({
                'line': line,
                'username': detected['username'],
                'password': detected['password']
            })
        else:
            results.append({
                'line': line,
                'username': 'Unknown',
                'password': 'Unknown'
            })
    
    return jsonify({
        'total': len(results),
        'accounts': results
    })

# ============================================
# API: ACCOUNTS RAW (Orijinal satırlar)
# ============================================
@app.route('/accounts/raw')
def accounts_raw():
    """Tüm satırları orijinal formatında döndürür"""
    lines = cache.load()
    return jsonify({
        'total': len(lines),
        'lines': lines
    })

# ============================================
# API: ACCOUNTS ADD (Yeni hesap ekleme)
# ============================================
@app.route('/accounts/add', methods=['POST'])
def add_account():
    """Yeni hesap ekler"""
    data = request.get_json()
    if not data or 'account' not in data:
        return jsonify({'error': 'Account data required'}), 400
    
    account = data['account'].strip()
    
    # Boş veya geçersiz kontrol
    if not account or ':' not in account:
        return jsonify({'error': 'Invalid account format'}), 400
    
    # Dosyaya ekle
    with open(DATA_FILE, 'a', encoding='utf-8') as f:
        f.write(account + '\n')
    
    # Cache'i yenile
    cache.load()
    
    return jsonify({
        'success': True,
        'message': 'Account added successfully',
        'account': account
    })

# ============================================
# API: ACCOUNTS BULK ADD (Toplu ekleme)
# ============================================
@app.route('/accounts/bulk', methods=['POST'])
def bulk_add():
    """Toplu hesap ekler"""
    data = request.get_json()
    if not data or 'accounts' not in data:
        return jsonify({'error': 'Accounts list required'}), 400
    
    accounts_list = data['accounts']
    if not isinstance(accounts_list, list):
        return jsonify({'error': 'Accounts must be a list'}), 400
    
    added = 0
    
    with open(DATA_FILE, 'a', encoding='utf-8') as f:
        for account in accounts_list:
            account = account.strip()
            if account and ':' in account:
                f.write(account + '\n')
                added += 1
    
    # Cache'i yenile
    cache.load()
    
    return jsonify({
        'success': True,
        'added': added,
        'total': len(accounts_list)
    })

# ============================================
# API: CACHE RELOAD
# ============================================
@app.route('/admin/reload', methods=['POST'])
def reload_cache():
    """Cache'i yeniden yükler"""
    cache.load()
    return jsonify({
        'success': True,
        'message': 'Cache reloaded successfully',
        'total': len(cache.lines)
    })

# ============================================
# API: SEARCH WITH REGEX (Gelişmiş)
# ============================================
@app.route('/search/regex', methods=['POST'])
def search_regex():
    """Regex ile arama yapar"""
    data = request.get_json()
    if not data or 'pattern' not in data:
        return jsonify({'error': 'Pattern required'}), 400
    
    pattern = data['pattern']
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return jsonify({'error': f'Invalid regex: {str(e)}'}), 400
    
    lines = cache.load()
    results = []
    
    for line in lines:
        if regex.search(line):
            results.append({
                'line': line,
                'matched': True
            })
    
    return jsonify({
        'pattern': pattern,
        'total': len(results),
        'results': results
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
            f.write('# Universal Accounts Database\n')
            f.write('# Support: URL:user:pass | email:pass | user:pass\n\n')
    
    # Cache'i ilk yükleme
    cache.load()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
