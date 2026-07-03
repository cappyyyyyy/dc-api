import os
import re
import json
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
import threading

app = Flask(__name__)
CORS(app)

# ============================================
# VERİ DOSYALARI YOLU - 20 DOSYA
# ============================================
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def get_data_files():
    """accounts1.txt'den accounts20.txt'ye kadar tüm dosyaları döndürür"""
    files = []
    for i in range(1, 21):
        file_path = os.path.join(DATA_DIR, f'accounts{i}.txt')
        files.append(file_path)
    return files

DATA_FILES = get_data_files()

# ============================================
# DOSYA OKUMA - SATIR SATIR (RAM DOSTU)
# ============================================
def search_in_file(file_path, query, limit=1000):
    """
    Bir dosyada arama yapar - satır satır okur, RAM'e yüklemez
    """
    results = []
    query_lower = query.lower()
    
    if not os.path.exists(file_path):
        return results
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if query_lower in line.lower():
                    results.append(line)
                    if len(results) >= limit:
                        break
    except Exception as e:
        print(f"❌ Dosya okuma hatası ({file_path}): {e}")
    
    return results

def count_lines_in_file(file_path):
    """Bir dosyadaki toplam satır sayısını hızlıca sayar"""
    if not os.path.exists(file_path):
        return 0
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            count = 0
            for line in f:
                if line.strip() and not line.startswith('#'):
                    count += 1
        return count
    except:
        return 0

def get_file_stats():
    """Tüm dosyaların istatistiklerini döndürür"""
    stats = {}
    total_lines = 0
    
    for file_path in DATA_FILES:
        if os.path.exists(file_path):
            lines = count_lines_in_file(file_path)
            size_mb = os.path.getsize(file_path) / (1024*1024)
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
            
            stats[os.path.basename(file_path)] = {
                'lines': lines,
                'size_mb': round(size_mb, 2),
                'last_modified': mtime
            }
            total_lines += lines
    
    return stats, total_lines

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
                            <div class="info">${info.lines} lines | ${info.size_mb} MB</div>
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
# API: SEARCH - OPTİMİZE EDİLMİŞ
# ============================================
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 100, type=int)  # Maksimum sonuç limiti
    offset = request.args.get('offset', 0, type=int)
    file_filter = request.args.get('file', '')
    
    if not query:
        return jsonify({
            'error': 'Query parameter "q" is required',
            'results': []
        }), 400
    
    # Maksimum limit 5000
    if limit > 5000:
        limit = 5000
    
    all_results = []
    files_to_search = DATA_FILES
    
    # Dosya filtresi uygula
    if file_filter:
        files_to_search = [f for f in DATA_FILES if file_filter in os.path.basename(f)]
    
    # Her dosyada ara (satır satır)
    for file_path in files_to_search:
        if not os.path.exists(file_path):
            continue
        
        found_lines = search_in_file(file_path, query, limit=limit)
        file_name = os.path.basename(file_path)
        
        for line in found_lines:
            detected = detect_format(line)
            if detected:
                all_results.append({
                    'line': line,
                    'file': file_name,
                    'username': detected['username'],
                    'password': detected['password']
                })
            else:
                all_results.append({
                    'line': line,
                    'file': file_name,
                    'username': 'Unknown',
                    'password': 'Unknown'
                })
        
        # Toplam limit aşıldıysa dur
        if len(all_results) >= limit:
            break
    
    # Offset uygula
    total = len(all_results)
    paginated_results = all_results[offset:offset + limit]
    
    return jsonify({
        'query': query,
        'total': total,
        'limit': limit,
        'offset': offset,
        'file_filter': file_filter,
        'results': paginated_results,
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# API: STATS - OPTİMİZE EDİLMİŞ
# ============================================
@app.route('/stats')
def stats():
    stats_data, total_lines = get_file_stats()
    return jsonify({
        'total': total_lines,
        'total_files': len(stats_data),
        'files': stats_data,
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# API: FILES LIST - OPTİMİZE EDİLMİŞ
# ============================================
@app.route('/files')
def files_list():
    """Tüm dosyaları ve içeriklerini listeler"""
    result = {}
    
    for file_path in DATA_FILES:
        if os.path.exists(file_path):
            lines = count_lines_in_file(file_path)
            result[os.path.basename(file_path)] = {
                'total': lines,
                'size_mb': round(os.path.getsize(file_path) / (1024*1024), 2)
            }
    
    return jsonify({
        'total_files': len(result),
        'files': result
    })

# ============================================
# API: SEARCH BY FILE
# ============================================
@app.route('/search/file/<filename>')
def search_by_file(filename):
    """Belirli bir dosyada arama yapar"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 1000, type=int)
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    # Dosyayı bul
    target_file = None
    for file_path in DATA_FILES:
        if filename in os.path.basename(file_path):
            target_file = file_path
            break
    
    if not target_file or not os.path.exists(target_file):
        return jsonify({'error': f'File {filename} not found'}), 404
    
    # Dosyada ara
    found_lines = search_in_file(target_file, query, limit=limit)
    results = []
    
    for line in found_lines:
        detected = detect_format(line)
        results.append({
            'line': line,
            'file': os.path.basename(target_file),
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
    limit = data.get('limit', 1000)
    
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return jsonify({'error': f'Invalid regex: {str(e)}'}), 400
    
    results = []
    
    for file_path in DATA_FILES:
        if not os.path.exists(file_path):
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if regex.search(line):
                        results.append({
                            'line': line,
                            'file': os.path.basename(file_path)
                        })
                        if len(results) >= limit:
                            break
        except Exception as e:
            print(f"❌ Regex arama hatası ({file_path}): {e}")
        
        if len(results) >= limit:
            break
    
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
    
    print("🚀 API Başlatılıyor...")
    print(f"📁 Veri klasörü: {DATA_DIR}")
    print(f"📄 Toplam dosya: {len(DATA_FILES)}")
    
    # İstatistikleri göster
    stats, total = get_file_stats()
    print(f"📊 Toplam satır: {total}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
