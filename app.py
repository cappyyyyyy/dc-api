import os
import re
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime

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
# DOSYA OKUMA - SADECE SATIR OKUMA
# ============================================
def search_in_files(query):
    """
    Tüm dosyalarda aranan kelimeyi içeren satırları döndürür
    """
    all_results = []
    query_lower = query.lower()
    
    for file_path in DATA_FILES:
        if not os.path.exists(file_path):
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Aranan kelime satırda varsa ekle
                    if query_lower in line.lower():
                        all_results.append({
                            'line': line,
                            'file': os.path.basename(file_path)
                        })
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
# ANA SAYFA
# ============================================
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Account Search - 20 Files</title>
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
            max-width: 1000px;
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
            white-space: pre-wrap;
        }
        .result-item .file-name {
            color: #60a5fa;
            font-size: 12px;
            margin-top: 8px;
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
        .result-count {
            color: #71717a;
            margin-bottom: 16px;
            font-size: 14px;
        }
        .loading {
            color: #71717a;
            text-align: center;
            padding: 20px;
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
            <h1>🔍 Account Search</h1>
            <p class="subtitle">Search across 20 files - Returns matching lines</p>
            <span class="status">🟢 Online - 20 Files</span>
            
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search any keyword..." onkeypress="if(event.key==='Enter') search()">
                <button onclick="search()">🔍 Search</button>
            </div>
            
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
            <span>Account Search v1.0 - Simple Line Matching</span>
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
        
        function search() {
            const query = document.getElementById('searchInput').value.trim();
            if (!query) {
                document.getElementById('resultsContainer').innerHTML = 
                    `<div class="empty">Please enter a search term</div>`;
                return;
            }
            
            document.getElementById('resultsContainer').innerHTML = 
                `<div class="loading">🔍 Searching for "${query}"...</div>`;
            
            fetch(`/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('resultsContainer').innerHTML = 
                            `<div class="empty">❌ ${data.error}</div>`;
                        return;
                    }
                    
                    displayResults(data);
                })
                .catch(err => {
                    document.getElementById('resultsContainer').innerHTML = 
                        `<div class="empty">❌ Error: ${err.message}</div>`;
                });
        }
        
        function displayResults(data) {
            const container = document.getElementById('resultsContainer');
            
            if (!data.results || data.results.length === 0) {
                container.innerHTML = `<div class="empty">🔍 No results found for "${data.query}"</div>`;
                return;
            }
            
            let html = `
                <div class="result-count">
                    📊 Found <strong>${data.total}</strong> matching lines for "<strong>${data.query}</strong>"
                </div>
            `;
            
            data.results.forEach((item) => {
                html += `
                    <div class="result-item">
                        <div class="line">${escapeHtml(item.line)}</div>
                        <div class="file-name">📄 ${item.file}</div>
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
# API: SEARCH - SADECE SATIR OKUMA
# ============================================
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'error': 'Query parameter "q" is required',
            'results': []
        }), 400
    
    # Tüm dosyalarda ara
    results = search_in_files(query)
    
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
    """Tüm dosyaları listeler"""
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
    results = []
    query_lower = query.lower()
    
    try:
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if query_lower in line.lower():
                    results.append({
                        'line': line,
                        'file': os.path.basename(target_file)
                    })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({
        'query': query,
        'file': filename,
        'total': len(results),
        'results': results
    })

# ============================================
# API: EXPORT
# ============================================
@app.route('/export')
def export_results():
    """Sonuçları TXT olarak dışa aktarır"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    results = search_in_files(query)
    
    # TXT formatında dışa aktar
    output = []
    for r in results:
        output.append(r['line'])
    
    return '\n'.join(output), 200, {
        'Content-Type': 'text/plain',
        'Content-Disposition': f'attachment; filename=search_results_{query}.txt'
    }

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
                f.write('# Format: android://TOKEN@PACKAGE/:USER:PASS\n')
                f.write('# Or any other format\n\n')
                f.write('example:password\n')
    
    print("🚀 Account Search API Başlatılıyor...")
    print(f"📁 Veri klasörü: {DATA_DIR}")
    print(f"📄 Toplam dosya: {len(DATA_FILES)}")
    print("🔍 Arama: Satır satır okuma, eşleşen satırları döndürür")
    
    # İstatistikleri göster
    stats, total = get_file_stats()
    print(f"📊 Toplam satır: {total}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
