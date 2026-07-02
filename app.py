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
# VERİ DOSYALARI YOLU - 20 DOSYA
# ============================================
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def get_data_files():
    """accounts1.txt'den accounts20.txt'ye kadar tüm dosyaları döndürür"""
    files = []
    for i in range(1, 21):  # 1'den 20'ye kadar
        file_path = os.path.join(DATA_DIR, f'accounts{i}.txt')
        files.append(file_path)
    return files

DATA_FILES = get_data_files()

# ============================================
# CACHE SİSTEMİ (Çoklu Dosya için)
# ============================================
class MultiAccountCache:
    def __init__(self):
        self.files_data = {}  # {file_path: [lines]}
        self.last_modified = {}  # {file_path: mtime}
        self.lock = threading.Lock()
        self.total_lines = 0
        self.file_stats = {}  # Her dosya için istatistik
    
    def load_all(self):
        """Tüm dosyaları yükler"""
        with self.lock:
            total = 0
            self.file_stats = {}
            
            for file_path in DATA_FILES:
                if not os.path.exists(file_path):
                    continue
                
                current_mtime = os.path.getmtime(file_path)
                if current_mtime == self.last_modified.get(file_path, 0) and file_path in self.files_data:
                    total += len(self.files_data[file_path])
                    self.file_stats[os.path.basename(file_path)] = {
                        'lines': len(self.files_data[file_path]),
                        'size_mb': os.path.getsize(file_path) / (1024*1024),
                        'last_modified': datetime.fromtimestamp(current_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = []
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                lines.append(line)
                        
                        self.files_data[file_path] = lines
                        self.last_modified[file_path] = current_mtime
                        total += len(lines)
                        
                        self.file_stats[os.path.basename(file_path)] = {
                            'lines': len(lines),
                            'size_mb': os.path.getsize(file_path) / (1024*1024),
                            'last_modified': datetime.fromtimestamp(current_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        }
                        print(f"✅ Yüklendi: {os.path.basename(file_path)} - {len(lines)} satır")
                except Exception as e:
                    print(f"❌ Dosya okuma hatası ({file_path}): {e}")
            
            self.total_lines = total
            print(f"📊 Toplam yüklenen satır: {self.total_lines}")
            return self.files_data
    
    def search(self, query):
        """Tüm dosyalarda arama yapar"""
        self.load_all()
        query_lower = query.lower()
        results = []
        
        for file_path, lines in self.files_data.items():
            for line in lines:
                if query_lower in line.lower():
                    results.append({
                        'line': line,
                        'file': os.path.basename(file_path)
                    })
        
        return results
    
    def get_stats(self):
        """İstatistikleri döndürür"""
        self.load_all()
        return {
            'total': self.total_lines,
            'total_files': len([f for f in self.files_data if self.files_data[f]]),
            'files': self.file_stats,
            'timestamp': datetime.now().isoformat()
        }

# Global cache instance
cache = MultiAccountCache()

# ============================================
# EVRENSEL FORMAT DETECTION
# ============================================
def detect_format(line):
    """Her türlü formatı tespit eder"""
    if not line or ':' not in line:
        return None
    
    parts = line.split(':')
    
    if len(parts) == 2:
        return {
            'username': parts[0].strip(),
            'password': parts[1].strip(),
            'full': line
        }
    elif len(parts) >= 3:
        url = parts[0]
        if '://' in url or '.' in url:
            username = ':'.join(parts[1:-1])
            password = parts[-1]
            return {
                'username': username.strip(),
                'password': password.strip(),
                'full': line
            }
        else:
            username = ':'.join(parts[0:-1])
            password = parts[-1]
            return {
                'username': username.strip(),
                'password': password.strip(),
                'full': line
            }
    
    return None

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
    <title>Multi-Account API</title>
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
        .result-item .file-name {
            color: #60a5fa;
            font-size: 12px;
            margin-top: 4px;
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
        }
        .stats .total {
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
        }
        .stats .file-stats {
            margin-top: 10px;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 8px;
            font-size: 11px;
        }
        .stats .file-stats .file-item {
            background: #0d0d0d;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid #2a2a2a;
        }
        .stats .file-stats .file-item .name {
            color: #60a5fa;
        }
        .stats .file-stats .file-item .info {
            color: #71717a;
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
            .stats .file-stats { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>📚 Multi-Account API</h1>
            <p class="subtitle">Search across 20 different account files</p>
            <span class="status">🟢 Online - 20 Files</span>
            
            <form method="GET" action="/search" class="search-box">
                <input type="text" name="q" placeholder="Search any keyword in all files..." required>
                <button type="submit">🔍 Search</button>
            </form>
            
            <div class="stats">
                <div class="total">
                    <span>📊 Total Accounts: <strong id="totalCount">Loading...</strong></span>
                    <span>📁 Files: <strong id="fileCount">Loading...</strong></span>
                </div>
                <div class="file-stats" id="fileStats">Loading...</div>
            </div>
        </div>
        <div class="footer">
            <span>Powered by Multi-Account API v2.0 (20 Files)</span>
        </div>
    </div>
    
    <script>
        fetch('/stats')
            .then(res => res.json())
            .then(data => {
                document.getElementById('totalCount').textContent = data.total || 0;
                const fileCount = Object.keys(data.files || {}).length;
                document.getElementById('fileCount').textContent = fileCount;
                
                let fileStatsHtml = '';
                for (const [name, info] of Object.entries(data.files || {})) {
                    fileStatsHtml += `
                        <div class="file-item">
                            <div class="name">📄 ${name}</div>
                            <div class="info">${info.lines} lines | ${info.size_mb.toFixed(2)} MB</div>
                        </div>
                    `;
                }
                document.getElementById('fileStats').innerHTML = fileStatsHtml || 'No files loaded';
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
    limit = request.args.get('limit', 1000, type=int)
    offset = request.args.get('offset', 0, type=int)
    file_filter = request.args.get('file', '')  # Belirli bir dosyada ara
    
    if not query:
        return jsonify({
            'error': 'Query parameter "q" is required',
            'results': []
        }), 400
    
    # Tüm dosyalarda ara
    results = cache.search(query)
    
    # Dosya filtresi uygula
    if file_filter:
        results = [r for r in results if file_filter in r['file']]
    
    # Detaylı sonuçlar oluştur
    detailed_results = []
    for result in results:
        detected = detect_format(result['line'])
        if detected:
            detailed_results.append({
                'line': result['line'],
                'file': result['file'],
                'username': detected['username'],
                'password': detected['password']
            })
        else:
            detailed_results.append({
                'line': result['line'],
                'file': result['file'],
                'username': 'Unknown',
                'password': 'Unknown'
            })
    
    # Limit ve offset uygula
    total = len(detailed_results)
    detailed_results = detailed_results[offset:offset + limit]
    
    return jsonify({
        'query': query,
        'total': total,
        'limit': limit,
        'offset': offset,
        'file_filter': file_filter,
        'results': detailed_results,
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# API: STATS
# ============================================
@app.route('/stats')
def stats():
    stats_data = cache.get_stats()
    return jsonify(stats_data)

# ============================================
# API: FILES LIST
# ============================================
@app.route('/files')
def files_list():
    """Tüm dosyaları ve içeriklerini listeler"""
    cache.load_all()
    result = {}
    
    for file_path, lines in cache.files_data.items():
        result[os.path.basename(file_path)] = {
            'total': len(lines),
            'size_mb': os.path.getsize(file_path) / (1024*1024) if os.path.exists(file_path) else 0,
            'preview': lines[:5] if lines else []
        }
    
    return jsonify({
        'total_files': len(result),
        'files': result
    })

# ============================================
# API: RELOAD ALL
# ============================================
@app.route('/admin/reload', methods=['POST'])
def reload_all():
    """Tüm cache'i yeniden yükler"""
    cache.load_all()
    stats = cache.get_stats()
    return jsonify({
        'success': True,
        'message': 'All caches reloaded',
        'total': cache.total_lines,
        'files_loaded': len(stats['files'])
    })

# ============================================
# API: SEARCH BY FILE
# ============================================
@app.route('/search/file/<filename>')
def search_by_file(filename, query):
    """Belirli bir dosyada arama yapar"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    cache.load_all()
    query_lower = query.lower()
    results = []
    
    for file_path, lines in cache.files_data.items():
        if filename in os.path.basename(file_path):
            for line in lines:
                if query_lower in line.lower():
                    detected = detect_format(line)
                    results.append({
                        'line': line,
                        'file': os.path.basename(file_path),
                        'username': detected['username'] if detected else 'Unknown',
                        'password': detected['password'] if detected else 'Unknown'
                    })
    
    return jsonify({
        'query': query,
        'file': filename,
        'total': len(results),
        'results': results
    })

# ============================================
# API: SEARCH WITH REGEX
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
    
    cache.load_all()
    results = []
    
    for file_path, lines in cache.files_data.items():
        for line in lines:
            if regex.search(line):
                results.append({
                    'line': line,
                    'file': os.path.basename(file_path)
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
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Eksik dosyaları oluştur
    for i in range(1, 21):
        file_path = os.path.join(DATA_DIR, f'accounts{i}.txt')
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f'# accounts{i}.txt\n')
                f.write('# Format: URL:user:pass | email:pass | user:pass\n\n')
                f.write('example:password\n')
    
    # Cache'i ilk yükleme
    cache.load_all()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
