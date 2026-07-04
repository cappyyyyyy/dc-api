import os
import glob
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================
# VERİ DOSYALARI
# ============================================
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def get_data_files():
    """Tüm accounts*.txt dosyalarını bulur"""
    pattern = os.path.join(DATA_DIR, 'accounts*.txt')
    files = glob.glob(pattern)
    
    # Eğer hiç dosya yoksa örnek dosya oluştur
    if not files:
        os.makedirs(DATA_DIR, exist_ok=True)
        for i in range(1, 21):
            file_path = os.path.join(DATA_DIR, f'accounts{i}.txt')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f'# accounts{i}.txt\n')
                f.write('android://token123@com.example.app/:user1:pass123\n')
                f.write('android://token456@com.test.app/:user2:pass456\n')
                f.write('alex:password123\n')
                f.write('test@example.com:testpass\n')
                f.write('192.168.1.1:admin:admin123\n')
                f.write('gmail:test@gmail.com:mypass\n')
        files = glob.glob(pattern)
    
    return sorted(files)

DATA_FILES = get_data_files()

# ============================================
# ARAMA FONKSİYONU
# ============================================
def search_in_files(query):
    """
    Tüm dosyalarda aranan kelimeyi içeren satırları döndürür
    """
    if not query or query.strip() == '':
        return []
    
    all_results = []
    query_lower = query.lower().strip()
    
    for file_path in DATA_FILES:
        if not os.path.exists(file_path):
            continue
        
        try:
            file_name = os.path.basename(file_path)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Boş satırları ve yorum satırlarını atla
                    if not line or line.startswith('#'):
                        continue
                    
                    # Aranan kelime satırda varsa ekle
                    if query_lower in line.lower():
                        all_results.append({
                            'line': line,
                            'file': file_name,
                            'line_number': line_num
                        })
        except Exception as e:
            print(f"❌ Dosya okuma hatası ({file_path}): {e}")
    
    return all_results

# ============================================
# REST API ENDPOINTLERİ
# ============================================

@app.route('/search', methods=['GET'])
def search():
    """
    Arama endpoint'i
    Kullanım: GET /search?q=aranacak_kelime
    """
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query parameter "q" is required',
            'results': []
        }), 400
    
    # Arama yap
    results = search_in_files(query)
    
    return jsonify({
        'success': True,
        'query': query,
        'total': len(results),
        'results': results,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/stats', methods=['GET'])
def stats():
    """
    İstatistik endpoint'i
    Kullanım: GET /stats
    """
    total_lines = 0
    total_files = len(DATA_FILES)
    files_info = {}
    
    for file_path in DATA_FILES:
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            lines = 0
            size_mb = os.path.getsize(file_path) / (1024*1024)
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            lines += 1
            except:
                pass
            
            files_info[file_name] = {
                'lines': lines,
                'size_mb': round(size_mb, 2)
            }
            total_lines += lines
    
    return jsonify({
        'success': True,
        'total_files': total_files,
        'total_lines': total_lines,
        'files': files_info,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/search/file/<filename>', methods=['GET'])
def search_file(filename):
    """
    Belirli bir dosyada arama yapar
    Kullanım: GET /search/file/accounts1.txt?q=kelime
    """
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query parameter "q" is required'
        }), 400
    
    # Dosyayı bul
    target_file = None
    for file_path in DATA_FILES:
        if filename in os.path.basename(file_path):
            target_file = file_path
            break
    
    if not target_file or not os.path.exists(target_file):
        return jsonify({
            'success': False,
            'error': f'File "{filename}" not found'
        }), 404
    
    # Dosyada ara
    results = []
    query_lower = query.lower().strip()
    
    try:
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if query_lower in line.lower():
                    results.append({
                        'line': line,
                        'file': os.path.basename(target_file),
                        'line_number': line_num
                    })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
    return jsonify({
        'success': True,
        'query': query,
        'file': filename,
        'total': len(results),
        'results': results,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/export', methods=['GET'])
def export():
    """
    Sonuçları TXT olarak dışa aktarır
    Kullanım: GET /export?q=kelime
    """
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query parameter "q" is required'
        }), 400
    
    results = search_in_files(query)
    
    output = []
    for r in results:
        output.append(r['line'])
    
    return '\n'.join(output), 200, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Disposition': f'attachment; filename=search_results_{query}.txt'
    }

@app.route('/files', methods=['GET'])
def files():
    """
    Tüm dosyaları listeler
    Kullanım: GET /files
    """
    files_list = []
    
    for file_path in DATA_FILES:
        if os.path.exists(file_path):
            files_list.append({
                'name': os.path.basename(file_path),
                'size_mb': round(os.path.getsize(file_path) / (1024*1024), 2)
            })
    
    return jsonify({
        'success': True,
        'total': len(files_list),
        'files': files_list
    })

@app.route('/', methods=['GET'])
def home():
    """Ana sayfa - API bilgileri"""
    return jsonify({
        'name': 'Account Search API',
        'version': '1.0',
        'description': 'Search across 20 account files',
        'endpoints': {
            'search': {
                'url': '/search?q=QUERY',
                'method': 'GET',
                'description': 'Search all files'
            },
            'search_file': {
                'url': '/search/file/FILENAME?q=QUERY',
                'method': 'GET',
                'description': 'Search specific file'
            },
            'stats': {
                'url': '/stats',
                'method': 'GET',
                'description': 'Get file statistics'
            },
            'files': {
                'url': '/files',
                'method': 'GET',
                'description': 'List all files'
            },
            'export': {
                'url': '/export?q=QUERY',
                'method': 'GET',
                'description': 'Export results as TXT'
            }
        },
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# HATA YÖNETİCİLERİ
# ============================================
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    # data klasörünü oluştur
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Eğer hiç dosya yoksa örnek dosyalar oluştur
    if not glob.glob(os.path.join(DATA_DIR, 'accounts*.txt')):
        print("📝 Örnek dosyalar oluşturuluyor...")
        for i in range(1, 21):
            file_path = os.path.join(DATA_DIR, f'accounts{i}.txt')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f'# accounts{i}.txt\n')
                f.write('android://token123@com.example.app/:user1:pass123\n')
                f.write('android://token456@com.test.app/:user2:pass456\n')
                f.write('alex:password123\n')
                f.write('test@example.com:testpass\n')
                f.write('192.168.1.1:admin:admin123\n')
                f.write('gmail:test@gmail.com:mypass\n')
        print("✅ Örnek dosyalar oluşturuldu!")
    
    print("=" * 60)
    print("🚀 ACCOUNT SEARCH REST API")
    print("=" * 60)
    print(f"📁 Veri klasörü: {DATA_DIR}")
    print(f"📄 Toplam dosya: {len(DATA_FILES)}")
    
    # Toplam satır sayısını göster
    total_lines = 0
    for file_path in DATA_FILES:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            total_lines += 1
            except:
                pass
    
    print(f"📊 Toplam satır: {total_lines}")
    print("=" * 60)
    print("📡 API ENDPOINTLERİ:")
    print("   GET /search?q=KELIME        - Tüm dosyalarda ara")
    print("   GET /search/file/DOSYA?q=K   - Belirli dosyada ara")
    print("   GET /stats                   - İstatistikler")
    print("   GET /files                   - Dosya listesi")
    print("   GET /export?q=KELIME        - Sonuçları dışa aktar")
    print("   GET /                        - API bilgisi")
    print("=" * 60)
    print("🌐 http://localhost:5000/search?q=alex")
    print("=" * 60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
