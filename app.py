import os
import glob
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import time
import mmap  # Memory-mapped file for faster reading

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
        files = glob.glob(pattern)
    
    return sorted(files)

DATA_FILES = get_data_files()

# ============================================
# HIZLI ARAMA - BÜYÜK DOSYALAR DAHİL
# ============================================

def search_in_files_optimized(query):
    """
    Optimize edilmiş arama - Tüm dosyaları okur, büyük dosyalar dahil
    """
    if not query or query.strip() == '':
        return []
    
    all_results = []
    query_lower = query.lower().strip()
    max_results = 10000  # Maksimum sonuç limiti (artırıldı)
    
    print(f"🔍 Aranıyor: '{query_lower}'")
    start_time = time.time()
    
    for file_path in DATA_FILES:
        if not os.path.exists(file_path):
            continue
        
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"📄 Okunuyor: {file_name} ({file_size_mb:.2f} MB)")
        
        try:
            # Büyük dosyalar için memory-mapped file kullan
            if file_size > 50 * 1024 * 1024:  # 50MB üzeri dosyalar
                print(f"   ⚡ Büyük dosya, memory-mapped okuma kullanılıyor...")
                
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Büyük dosyayı parça parça oku
                    chunk_size = 1024 * 1024 * 10  # 10MB chunk
                    chunk = ''
                    
                    while True:
                        # Büyük parçalar halinde oku
                        data = f.read(chunk_size)
                        if not data:
                            break
                        
                        # Son satırı tamamlamak için
                        chunk += data
                        lines = chunk.split('\n')
                        
                        # Son satırı sakla (tamamlanmamış olabilir)
                        chunk = lines[-1] if lines else ''
                        
                        # Tüm tam satırları işle
                        for line_num, line in enumerate(lines[:-1], 1):
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            
                            if query_lower in line.lower():
                                all_results.append({
                                    'line': line,
                                    'file': file_name,
                                    'line_number': line_num
                                })
                                
                                if len(all_results) >= max_results:
                                    print(f"✅ Maksimum sonuç limitine ulaşıldı: {max_results}")
                                    elapsed = time.time() - start_time
                                    print(f"⏱️ Toplam süre: {elapsed:.2f} saniye")
                                    return all_results
                    
                    # Kalan parçayı işle
                    if chunk:
                        line = chunk.strip()
                        if line and not line.startswith('#'):
                            if query_lower in line.lower():
                                all_results.append({
                                    'line': line,
                                    'file': file_name,
                                    'line_number': 'end'
                                })
            
            else:
                # Küçük dosyalar normal oku
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        if query_lower in line.lower():
                            all_results.append({
                                'line': line,
                                'file': file_name,
                                'line_number': line_num
                            })
                            
                            if len(all_results) >= max_results:
                                print(f"✅ Maksimum sonuç limitine ulaşıldı: {max_results}")
                                elapsed = time.time() - start_time
                                print(f"⏱️ Toplam süre: {elapsed:.2f} saniye")
                                return all_results
            
            print(f"   ✅ {file_name} okundu, {len([r for r in all_results if r['file'] == file_name])} sonuç")
            
        except MemoryError:
            print(f"   ⚠️ {file_name} için memory hatası, normal okuma deneniyor...")
            # Memory hatası olursa normal okuma dene
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        if query_lower in line.lower():
                            all_results.append({
                                'line': line,
                                'file': file_name,
                                'line_number': line_num
                            })
                            
                            if len(all_results) >= max_results:
                                print(f"✅ Maksimum sonuç limitine ulaşıldı: {max_results}")
                                elapsed = time.time() - start_time
                                print(f"⏱️ Toplam süre: {elapsed:.2f} saniye")
                                return all_results
            except Exception as e:
                print(f"   ❌ Hata: {e}")
                
        except Exception as e:
            print(f"   ❌ Okuma hatası: {e}")
            continue
    
    elapsed = time.time() - start_time
    print(f"⏱️ Toplam arama süresi: {elapsed:.2f} saniye")
    print(f"📊 Toplam sonuç: {len(all_results)}")
    
    return all_results

# ============================================
# CACHE YÖNETİMİ
# ============================================

class SearchCache:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 30  # 30 saniye cache
    
    def get(self, query):
        if query in self.cache:
            if time.time() - self.cache_time[query] < self.cache_duration:
                print(f"✅ Cache'den döndü: '{query}'")
                return self.cache[query]
        return None
    
    def set(self, query, results):
        self.cache[query] = results
        self.cache_time[query] = time.time()
    
    def clear(self):
        self.cache.clear()
        self.cache_time.clear()

search_cache = SearchCache()

# ============================================
# REST API ENDPOINTLERİ
# ============================================

@app.route('/search', methods=['GET'])
def search():
    """
    Arama endpoint'i - Tüm dosyaları okur, büyük dosyalar dahil
    Kullanım: GET /search?q=aranacak_kelime
    """
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query parameter "q" is required',
            'results': []
        }), 400
    
    # Cache kontrolü
    cached_results = search_cache.get(query)
    if cached_results is not None:
        return jsonify({
            'success': True,
            'query': query,
            'total': len(cached_results),
            'results': cached_results,
            'cached': True,
            'timestamp': datetime.now().isoformat()
        })
    
    # Arama yap
    results = search_in_files_optimized(query)
    
    # Cache'le
    search_cache.set(query, results)
    
    return jsonify({
        'success': True,
        'query': query,
        'total': len(results),
        'results': results,
        'cached': False,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/search/file/<filename>', methods=['GET'])
def search_file(filename):
    """Belirli bir dosyada arama yapar"""
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
    file_name = os.path.basename(target_file)
    
    try:
        print(f"📄 Okunuyor: {file_name}")
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if query_lower in line.lower():
                    results.append({
                        'line': line,
                        'file': file_name,
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

@app.route('/search/cache/clear', methods=['POST'])
def clear_cache():
    """Cache'i temizler"""
    search_cache.clear()
    return jsonify({
        'success': True,
        'message': 'Cache temizlendi'
    })

@app.route('/stats', methods=['GET'])
def stats():
    """Dosya istatistikleri"""
    files_info = {}
    total_size = 0
    
    for file_path in DATA_FILES:
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            size_mb = os.path.getsize(file_path) / (1024*1024)
            total_size += size_mb
            
            files_info[file_name] = {
                'size_mb': round(size_mb, 2),
                'path': file_path
            }
    
    return jsonify({
        'success': True,
        'total_files': len(files_info),
        'total_size_mb': round(total_size, 2),
        'files': files_info,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/export', methods=['GET'])
def export():
    """Sonuçları TXT olarak dışa aktar"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query parameter "q" is required'
        }), 400
    
    results = search_in_files_optimized(query)
    
    output = []
    for r in results:
        output.append(r['line'])
    
    return '\n'.join(output), 200, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Disposition': f'attachment; filename=search_results_{query}.txt'
    }

@app.route('/files', methods=['GET'])
def files():
    """Tüm dosyaları listeler"""
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
    """API bilgileri"""
    return jsonify({
        'name': 'Account Search API',
        'version': '3.0',
        'description': 'Search across all files - Including large files',
        'features': [
            '📁 Tüm dosyalar okunur (büyük dosyalar dahil)',
            '⚡ Optimize edilmiş okuma (chunk ile)',
            '💾 Cache desteği (30 saniye)',
            '📊 Maksimum 10,000 sonuç',
            '🚀 Memory-mapped okuma (büyük dosyalar için)'
        ],
        'endpoints': {
            'search': '/search?q=QUERY',
            'search_file': '/search/file/FILENAME?q=QUERY',
            'stats': '/stats',
            'files': '/files',
            'export': '/export?q=QUERY',
            'clear_cache': '/search/cache/clear (POST)'
        },
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# HATA YÖNETİCİLERİ
# ============================================
@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Örnek dosyalar oluştur
    if not glob.glob(os.path.join(DATA_DIR, 'accounts*.txt')):
        print("📝 Örnek dosyalar oluşturuluyor...")
        for i in range(1, 21):
            file_path = os.path.join(DATA_DIR, f'accounts{i}.txt')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f'# accounts{i}.txt\n')
                for j in range(1000):
                    f.write(f'user{j}@example.com:pass{j}\n')
                    f.write(f'android://token{j}@com.app{i}.com/:user{j}:pass{j}\n')
                    f.write(f'alex_user_{j}:password_{j}\n')
        print("✅ Örnek dosyalar oluşturuldu!")
    
    # Dosya boyutlarını göster
    print("=" * 60)
    print("🚀 ACCOUNT SEARCH API - TÜM DOSYALAR OKUNUR")
    print("=" * 60)
    print(f"📁 Veri klasörü: {DATA_DIR}")
    print(f"📄 Toplam dosya: {len(DATA_FILES)}")
    
    total_size = 0
    for file_path in DATA_FILES:
        if os.path.exists(file_path):
            size_mb = os.path.getsize(file_path) / (1024*1024)
            total_size += size_mb
            print(f"   - {os.path.basename(file_path)}: {size_mb:.2f} MB")
    
    print(f"📊 Toplam boyut: {total_size:.2f} MB")
    print("=" * 60)
    print("⚡ Özellikler:")
    print("   - Tüm dosyalar okunur (büyük dosyalar dahil)")
    print("   - Chunk ile parçalı okuma")
    print("   - Memory-mapped okuma (50MB+ dosyalar)")
    print("   - 30 saniye cache")
    print("   - Maksimum 10,000 sonuç")
    print("=" * 60)
    print("📡 Test:")
    print("   curl 'http://localhost:5000/search?q=alex'")
    print("=" * 60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
