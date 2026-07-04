import os
import re
import json
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
import base64
import urllib.parse

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
# EVRENSEL FORMAT PARSER - TÜM FORMATLAR
# ============================================
def parse_android_format(line):
    """
    android:// formatını parse eder
    android://TOKEN@PACKAGE/:USERNAME:PASSWORD
    """
    if not line.startswith('android://'):
        return None
    
    try:
        # android:// kısmını kaldır
        content = line[10:]  # 'android://' uzunluğu = 10
        
        # @ işareti ile token ve gerisini ayır
        if '@' not in content:
            return None
        
        token_part, rest = content.split('@', 1)
        
        # /: ile package ve gerisini ayır
        if '/:' not in rest:
            return None
        
        package, credentials = rest.split('/:', 1)
        
        # : ile username ve password'u ayır
        if ':' not in credentials:
            return None
        
        # Birden fazla : varsa, ilk : username, son : password
        parts = credentials.split(':')
        if len(parts) >= 2:
            username = ':'.join(parts[:-1])  # İlk kısımlar username
            password = parts[-1]  # Son kısım password
        else:
            username = parts[0]
            password = ''
        
        # Token'ı decode etmeyi dene (base64)
        decoded_token = None
        try:
            decoded_token = base64.b64decode(token_part).decode('utf-8', errors='ignore')
        except:
            decoded_token = token_part
        
        return {
            'format': 'android',
            'token': token_part,
            'token_decoded': decoded_token,
            'package': package,
            'username': username.strip(),
            'password': password.strip(),
            'full': line
        }
    except Exception as e:
        return None

def parse_standard_format(line):
    """
    Standart formatları parse eder:
    - email:password
    - username:password
    - url:username:password
    - url:email:password
    """
    if not line or ':' not in line:
        return None
    
    parts = line.split(':')
    
    # URL içeriyor mu kontrol et
    has_url = any('.' in part and ('://' in part or '/' in part) for part in parts)
    
    if has_url:
        # URL:USER:PASS formatı
        if len(parts) >= 3:
            url = parts[0]
            username = ':'.join(parts[1:-1])
            password = parts[-1]
            return {
                'format': 'url',
                'url': url,
                'username': username.strip(),
                'password': password.strip(),
                'full': line
            }
    else:
        # USER:PASS formatı
        if len(parts) == 2:
            return {
                'format': 'standard',
                'username': parts[0].strip(),
                'password': parts[1].strip(),
                'full': line
            }
        elif len(parts) > 2:
            # Çoklu : varsa, ilk kısım username, son kısım password
            username = ':'.join(parts[:-1])
            password = parts[-1]
            return {
                'format': 'standard',
                'username': username.strip(),
                'password': password.strip(),
                'full': line
            }
    
    return None

def parse_json_format(line):
    """JSON formatını parse eder"""
    try:
        data = json.loads(line)
        if isinstance(data, dict):
            # Yaygın alan adlarını kontrol et
            username = data.get('username') or data.get('user') or data.get('email') or data.get('login') or ''
            password = data.get('password') or data.get('pass') or data.get('pwd') or ''
            return {
                'format': 'json',
                'username': str(username),
                'password': str(password),
                'full': line,
                'data': data
            }
    except:
        pass
    return None

def parse_cookie_format(line):
    """Cookie formatını parse eder"""
    if '=' in line and (';' in line or 'cookie' in line.lower()):
        try:
            # Basit cookie parse
            cookies = {}
            for item in line.split(';'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies[key.strip()] = value.strip()
            
            if cookies:
                return {
                    'format': 'cookie',
                    'cookies': cookies,
                    'full': line
                }
        except:
            pass
    return None

def parse_any_format(line):
    """
    Her türlü formatı tespit edip parse eder
    """
    if not line or line.startswith('#'):
        return None
    
    # Android format
    result = parse_android_format(line)
    if result:
        return result
    
    # JSON format
    result = parse_json_format(line)
    if result:
        return result
    
    # Cookie format
    result = parse_cookie_format(line)
    if result:
        return result
    
    # Standart format
    result = parse_standard_format(line)
    if result:
        return result
    
    # Hiçbir formata uymuyorsa ham olarak döndür
    return {
        'format': 'unknown',
        'full': line,
        'username': 'Unknown',
        'password': 'Unknown'
    }

# ============================================
# DOSYA OKUMA - SATIR SATIR (RAM DOSTU)
# ============================================
def search_in_all_files(query, files_to_search=None):
    """
    Tüm dosyalarda arar ve SONUÇ LİMİTİ OLMADAN tüm eşleşmeleri döndürür
    """
    if files_to_search is None:
        files_to_search = DATA_FILES
    
    all_results = []
    query_lower = query.lower()
    
    for file_path in files_to_search:
        if not os.path.exists(file_path):
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Arama yap
                    if query_lower in line.lower():
                        parsed = parse_any_format(line)
                        parsed['file'] = os.path.basename(file_path)
                        all_results.append(parsed)
        except Exception as e:
            print(f"❌ Dosya okuma hatası ({file_path}): {e}")
    
    return all_results

def count_lines_in_file(file_path):
    """Bir dosyadaki toplam satır sayısını sayar"""
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
    <title>Multi-Account API - Universal Parser</title>
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
            max-width: 1200px;
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
        .format-filter {
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .format-filter button {
            padding: 6px 14px;
            border-radius: 20px;
            border: 1px solid #2a2a2a;
            background: transparent;
            color: #71717a;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .format-filter button:hover {
            border-color: #a78bfa;
            color: #e4e4e7;
        }
        .format-filter button.active {
            background: #a78bfa20;
            border-color: #a78bfa;
            color: #a78bfa;
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
        .result-item .line {
            color: #e4e4e7;
            font-size: 13px;
            font-family: monospace;
            word-break: break-all;
        }
        .result-item .info {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            margin-top: 8px;
            font-size: 12px;
        }
        .result-item .info .label {
            color: #52525b;
        }
        .result-item .info .value {
            color: #e4e4e7;
        }
        .result-item .file-name {
            color: #60a5fa;
        }
        .result-item .format-badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .format-badge.android { background: #f472b620; color: #f472b6; }
        .format-badge.standard { background: #60a5fa20; color: #60a5fa; }
        .format-badge.url { background: #34d39920; color: #34d399; }
        .format-badge.json { background: #fbbf2420; color: #fbbf24; }
        .format-badge.cookie { background: #a78bfa20; color: #a78bfa; }
        .format-badge.unknown { background: #52525b20; color: #71717a; }
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
        .result-count {
            color: #71717a;
            margin-bottom: 16px;
            font-size: 14px;
        }
        @media (max-width: 600px) {
            .card { padding: 20px; }
            .search-box { flex-direction: column; }
            .stats .file-stats { grid-template-columns: 1fr; }
            .result-item .info { flex-direction: column; gap: 4px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>📚 Universal Account Parser</h1>
            <p class="subtitle">Search across 20 files - All formats supported</p>
            <span class="status">🟢 Online - Unlimited Results</span>
            
            <form method="GET" action="/search" class="search-box" id="searchForm">
                <input type="text" name="q" placeholder="Search any keyword..." required>
                <button type="submit">🔍 Search</button>
            </form>
            
            <div id="resultsContainer">
                <div class="empty">Enter a search term to find accounts</div>
            </div>
            
            <div class="stats">
                <div class="total">
                    <span>📊 Total Accounts: <strong id="totalCount">Loading...</strong></span>
                    <span>📁 Files: <strong id="fileCount">Loading...</strong></span>
                </div>
                <div class="file-stats" id="fileStats">Loading...</div>
            </div>
        </div>
        <div class="footer">
            <span>Powered by Universal Account Parser v3.0 - All Formats Supported</span>
        </div>
    </div>
    
    <script>
        // Load stats
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
        
        // Handle search form submission
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const query = this.querySelector('input[name="q"]').value;
            if (!query) return;
            
            fetch(`/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    displayResults(data);
                })
                .catch(err => {
                    document.getElementById('resultsContainer').innerHTML = 
                        `<div class="empty">❌ Error: ${err.message}</div>`;
                });
        });
        
        function displayResults(data) {
            const container = document.getElementById('resultsContainer');
            
            if (!data.results || data.results.length === 0) {
                container.innerHTML = `<div class="empty">🔍 No results found for "${data.query}"</div>`;
                return;
            }
            
            let html = `
                <div class="result-count">
                    📊 Found <strong>${data.total}</strong> results for "${data.query}"
                </div>
            `;
            
            data.results.forEach((item, index) => {
                const formatClass = item.format || 'unknown';
                let details = '';
                
                if (item.format === 'android') {
                    details = `
                        <div class="info">
                            <span><span class="label">Package:</span> <span class="value">${item.package || 'N/A'}</span></span>
                            <span><span class="label">User:</span> <span class="value">${item.username || 'N/A'}</span></span>
                            <span><span class="label">Pass:</span> <span class="value">${item.password || 'N/A'}</span></span>
                            <span><span class="label">File:</span> <span class="file-name">${item.file}</span></span>
                        </div>
                    `;
                } else if (item.format === 'json') {
                    details = `
                        <div class="info">
                            <span><span class="label">User:</span> <span class="value">${item.username || 'N/A'}</span></span>
                            <span><span class="label">Pass:</span> <span class="value">${item.password || 'N/A'}</span></span>
                            <span><span class="label">File:</span> <span class="file-name">${item.file}</span></span>
                        </div>
                    `;
                } else if (item.format === 'cookie') {
                    const cookieCount = item.cookies ? Object.keys(item.cookies).length : 0;
                    details = `
                        <div class="info">
                            <span><span class="label">Cookies:</span> <span class="value">${cookieCount} cookies</span></span>
                            <span><span class="label">File:</span> <span class="file-name">${item.file}</span></span>
                        </div>
                    `;
                } else {
                    details = `
                        <div class="info">
                            <span><span class="label">User:</span> <span class="value">${item.username || 'N/A'}</span></span>
                            <span><span class="label">Pass:</span> <span class="value">${item.password || 'N/A'}</span></span>
                            <span><span class="label">File:</span> <span class="file-name">${item.file}</span></span>
                        </div>
                    `;
                }
                
                html += `
                    <div class="result-item">
                        <div class="line">${escapeHtml(item.full || item.line || 'N/A')}</div>
                        <div style="margin-top:6px;">
                            <span class="format-badge ${formatClass}">${formatClass}</span>
                        </div>
                        ${details}
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
    ''')

# ============================================
# API: SEARCH - SINIRSIZ SONUÇ
# ============================================
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    format_filter = request.args.get('format', '')  # android, standard, url, json, cookie
    file_filter = request.args.get('file', '')
    
    if not query:
        return jsonify({
            'error': 'Query parameter "q" is required',
            'results': []
        }), 400
    
    # Dosya filtresi uygula
    files_to_search = DATA_FILES
    if file_filter:
        files_to_search = [f for f in DATA_FILES if file_filter in os.path.basename(f)]
    
    # Tüm sonuçları bul (limit yok)
    all_results = search_in_all_files(query, files_to_search)
    
    # Format filtresi uygula
    if format_filter:
        all_results = [r for r in all_results if r.get('format') == format_filter]
    
    return jsonify({
        'query': query,
        'total': len(all_results),
        'format_filter': format_filter,
        'file_filter': file_filter,
        'results': all_results,
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# API: STATS
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
# API: FILES LIST
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
    """Belirli bir dosyada arama yapar - sinirsiz sonuç"""
    query = request.args.get('q', '').strip()
    
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
    
    # Dosyada ara (limit yok)
    results = []
    query_lower = query.lower()
    
    try:
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if query_lower in line.lower():
                    parsed = parse_any_format(line)
                    parsed['file'] = os.path.basename(target_file)
                    results.append(parsed)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({
        'query': query,
        'file': filename,
        'total': len(results),
        'results': results
    })

# ============================================
# API: EXPORT RESULTS
# ============================================
@app.route('/export')
def export_results():
    """Sonuçları JSON veya TXT olarak dışa aktarır"""
    query = request.args.get('q', '').strip()
    format_type = request.args.get('format', 'json')  # json veya txt
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    results = search_in_all_files(query)
    
    if format_type == 'txt':
        # TXT formatında dışa aktar
        output = []
        for r in results:
            output.append(r.get('full', ''))
        return '\n'.join(output), 200, {'Content-Type': 'text/plain'}
    else:
        # JSON formatında dışa aktar
        return jsonify({
            'query': query,
            'total': len(results),
            'results': results,
            'exported_at': datetime.now().isoformat()
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
                f.write('# All formats supported: android://, email:pass, user:pass, url:user:pass, JSON, Cookies\n\n')
                f.write('example:password\n')
    
    print("🚀 Universal Account Parser Başlatılıyor...")
    print(f"📁 Veri klasörü: {DATA_DIR}")
    print(f"📄 Toplam dosya: {len(DATA_FILES)}")
    print("📋 Desteklenen Formatlar:")
    print("   ✅ android://TOKEN@PACKAGE/:USER:PASS")
    print("   ✅ email:password")
    print("   ✅ username:password")
    print("   ✅ url:username:password")
    print("   ✅ JSON format")
    print("   ✅ Cookie format")
    print("   ✅ Tüm diğer formatlar (ham olarak)")
    print("🔍 SONUÇ LİMİTİ YOK - Tüm eşleşmeler döndürülür")
    
    # İstatistikleri göster
    stats, total = get_file_stats()
    print(f"📊 Toplam satır: {total}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
