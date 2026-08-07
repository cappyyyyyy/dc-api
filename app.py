import os
import glob
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import time

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
                f.write('URL: https://example.com/login\n')
                f.write('Username: testuser@email.com\n')
                f.write('Password: testpass123\n')
                f.write('Application: Google_[Chrome]_Default\n')
                f.write('===============\n')
        files = glob.glob(pattern)
    
    return sorted(files)

DATA_FILES = get_data_files()

# ============================================
# EVRENSEL PARSER - TÜM FORMATLAR
# ============================================
def parse_stealer_log(line):
    """Stealer log formatını parse eder"""
    if not line or 'URL:' not in line:
        return None
    
    try:
        data = {}
        
        # URL
        url_match = re.search(r'URL:\s*(.+?)(?:\s+Username:|$)', line, re.IGNORECASE)
        if url_match:
            data['url'] = url_match.group(1).strip()
        
        # Username
        user_match = re.search(r'Username:\s*(.+?)(?:\s+Password:|$)', line, re.IGNORECASE)
        if user_match:
            data['username'] = user_match.group(1).strip()
        
        # Password
        pass_match = re.search(r'Password:\s*(.+?)(?:\s+Application:|$)', line, re.IGNORECASE)
        if pass_match:
            data['password'] = pass_match.group(1).strip()
        
        # Application
        app_match = re.search(r'Application:\s*(.+?)(?:\s+========|$)', line, re.IGNORECASE)
        if app_match:
            data['application'] = app_match.group(1).strip()
        
        if data.get('url') and (data.get('username') or data.get('password')):
            data['type'] = 'stealer'
            data['full'] = line
            return data
        
        return None
        
    except Exception as e:
        return None

def parse_android_format(line):
    """Android formatını parse eder"""
    if not line.startswith('android://'):
        return None
    
    try:
        content = line[10:]
        if '@' not in content or '/:' not in content:
            return None
        
        token_part, rest = content.split('@', 1)
        package, credentials = rest.split('/:', 1)
        
        if ':' not in credentials:
            return None
        
        parts = credentials.split(':')
        if len(parts) >= 2:
            username = ':'.join(parts[:-1])
            password = parts[-1]
        else:
            username = parts[0]
            password = ''
        
        return {
            'type': 'android',
            'token': token_part,
            'package': package,
            'username': username.strip(),
            'password': password.strip(),
            'full': line
        }
    except:
        return None

def parse_standard_format(line):
    """Standart formatları parse eder"""
    if not line or ':' not in line:
        return None
    
    parts = line.split(':')
    
    # URL içeriyor mu kontrol et
    has_url = any('.' in part and ('://' in part or '/' in part) for part in parts)
    
    if has_url:
        if len(parts) >= 3:
            return {
                'type': 'url',
                'url': parts[0],
                'username': ':'.join(parts[1:-1]).strip(),
                'password': parts[-1].strip(),
                'full': line
            }
    else:
        if len(parts) == 2:
            return {
                'type': 'standard',
                'username': parts[0].strip(),
                'password': parts[1].strip(),
                'full': line
            }
        elif len(parts) > 2:
            return {
                'type': 'standard',
                'username': ':'.join(parts[:-1]).strip(),
                'password': parts[-1].strip(),
                'full': line
            }
    
    return None

def parse_any_format(line):
    """Her türlü formatı otomatik parse et"""
    if not line or line.startswith('#'):
        return None
    
    # Stealer log formatı
    result = parse_stealer_log(line)
    if result:
        return result
    
    # Android formatı
    result = parse_android_format(line)
    if result:
        return result
    
    # Standart format
    result = parse_standard_format(line)
    if result:
        return result
    
    # Hiçbir formata uymuyorsa ham olarak döndür
    return {
        'type': 'unknown',
        'full': line,
        'username': 'Unknown',
        'password': 'Unknown'
    }

# ============================================
# HIZLI ARAMA - TÜM DOSYALAR, TÜM FORMATLAR
# ============================================
def search_in_files_optimized(query):
    """Optimize edilmiş arama - Tüm dosyaları okur, tüm formatları otomatik parse eder"""
    if not query or query.strip() == '':
        return []
    
    all_results = []
    query_lower = query.lower().strip()
    max_results = 10000
    
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
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                stealer_buffer = []
                in_stealer = False
                
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    # Stealer log başlangıcı
                    if line.startswith('URL:'):
                        if stealer_buffer:
                            full_entry = ' '.join(stealer_buffer)
                            if query_lower in full_entry.lower():
                                parsed = parse_any_format(full_entry)
                                if parsed:
                                    parsed['file'] = file_name
                                    parsed['line_number'] = line_num
                                    all_results.append(parsed)
                                    
                                    if len(all_results) >= max_results:
                                        return all_results
                        stealer_buffer = []
                        stealer_buffer.append(line)
                        in_stealer = True
                    
                    # Stealer log devamı
                    elif in_stealer and (line.startswith('Username:') or line.startswith('Password:') or line.startswith('Application:')):
                        stealer_buffer.append(line)
                    
                    # Stealer log sonu
                    elif line.startswith('==============='):
                        if stealer_buffer:
                            full_entry = ' '.join(stealer_buffer)
                            if query_lower in full_entry.lower():
                                parsed = parse_any_format(full_entry)
                                if parsed:
                                    parsed['file'] = file_name
                                    parsed['line_number'] = line_num
                                    all_results.append(parsed)
                                    
                                    if len(all_results) >= max_results:
                                        return all_results
                        stealer_buffer = []
                        in_stealer = False
                    
                    # Normal satır
                    else:
                        if not in_stealer:
                            if query_lower in line.lower():
                                parsed = parse_any_format(line)
                                if parsed:
                                    parsed['file'] = file_name
                                    parsed['line_number'] = line_num
                                    all_results.append(parsed)
                                    
                                    if len(all_results) >= max_results:
                                        return all_results
                        else:
                            if line and not line.startswith('URL:'):
                                stealer_buffer.append(line)
                
                # Kalan buffer'ı işle
                if stealer_buffer:
                    full_entry = ' '.join(stealer_buffer)
                    if query_lower in full_entry.lower():
                        parsed = parse_any_format(full_entry)
                        if parsed:
                            parsed['file'] = file_name
                            parsed['line_number'] = 'end'
                            all_results.append(parsed)
            
            print(f"   ✅ {file_name} okundu, {len([r for r in all_results if r.get('file') == file_name])} sonuç")
            
        except Exception as e:
            print(f"   ❌ Okuma hatası ({file_name}): {e}")
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
        self.cache_duration = 30
    
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
    """Arama endpoint'i - Otomatik tüm formatları tarar"""
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
            stealer_buffer = []
            in_stealer = False
            
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                if not line:
                    continue
                
                if line.startswith('URL:'):
                    if stealer_buffer:
                        full_entry = ' '.join(stealer_buffer)
                        if query_lower in full_entry.lower():
                            parsed = parse_any_format(full_entry)
                            if parsed:
                                parsed['file'] = file_name
                                parsed['line_number'] = line_num
                                results.append(parsed)
                        stealer_buffer = []
                    
                    stealer_buffer.append(line)
                    in_stealer = True
                
                elif in_stealer and (line.startswith('Username:') or line.startswith('Password:') or line.startswith('Application:')):
                    stealer_buffer.append(line)
                
                elif line.startswith('==============='):
                    if stealer_buffer:
                        full_entry = ' '.join(stealer_buffer)
                        if query_lower in full_entry.lower():
                            parsed = parse_any_format(full_entry)
                            if parsed:
                                parsed['file'] = file_name
                                parsed['line_number'] = line_num
                                results.append(parsed)
                        stealer_buffer = []
                        in_stealer = False
                
                else:
                    if not in_stealer:
                        if query_lower in line.lower():
                            parsed = parse_any_format(line)
                            if parsed:
                                parsed['file'] = file_name
                                parsed['line_number'] = line_num
                                results.append(parsed)
                    else:
                        if line and not line.startswith('URL:'):
                            stealer_buffer.append(line)
            
            if stealer_buffer:
                full_entry = ' '.join(stealer_buffer)
                if query_lower in full_entry.lower():
                    parsed = parse_any_format(full_entry)
                    if parsed:
                        parsed['file'] = file_name
                        parsed['line_number'] = 'end'
                        results.append(parsed)
                    
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
        if r.get('type') == 'stealer':
            output.append(f"URL: {r.get('url', '')}")
            output.append(f"Username: {r.get('username', '')}")
            output.append(f"Password: {r.get('password', '')}")
            output.append(f"Application: {r.get('application', '')}")
            output.append("===============")
        else:
            output.append(r.get('full', ''))
    
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

@app.route('/formats', methods=['GET'])
def formats():
    """Desteklenen formatları listeler"""
    return jsonify({
        'success': True,
        'formats': [
            {
                'name': 'Stealer Log',
                'description': 'Otomatik tespit edilir',
                'example': 'URL: https://example.com/login\nUsername: user@email.com\nPassword: pass123\nApplication: Google_[Chrome]_Default'
            },
            {
                'name': 'Android Format',
                'description': 'Otomatik tespit edilir',
                'example': 'android://token123@com.example.app/:user1:pass123'
            },
            {
                'name': 'Standard Format',
                'description': 'Otomatik tespit edilir',
                'example': 'user@example.com:pass123'
            },
            {
                'name': 'URL Format',
                'description': 'Otomatik tespit edilir',
                'example': 'https://example.com:user:pass123'
            }
        ],
        'note': 'Tüm formatlar otomatik olarak tespit edilir, manuel seçim gerekmez',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def home():
    """API bilgileri"""
    return jsonify({
        'name': 'Account Search API - Universal Parser',
        'version': '4.0',
        'description': 'Otomatik format tespiti ile tüm dosyalarda arama',
        'features': [
            '📁 Tüm dosyalar okunur (büyük dosyalar dahil)',
            '🔄 Otomatik format tespiti (stealer, android, standard, url)',
            '⚡ Optimize edilmiş okuma',
            '💾 Cache desteği (30 saniye)',
            '📊 Maksimum 10,000 sonuç'
        ],
        'endpoints': {
            'search': '/search?q=QUERY',
            'search_file': '/search/file/FILENAME?q=QUERY',
            'stats': '/stats',
            'files': '/files',
            'formats': '/formats',
            'export': '/export?q=QUERY',
            'clear_cache': '/search/cache/clear (POST)'
        },
        'usage': 'Sadece ?q=parametresi ile arama yapın, format seçeneği gerekmez',
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
                f.write('android://token123@com.example.app/:user1:pass123\n')
                f.write('android://token456@com.test.app/:user2:pass456\n')
                f.write('alex:password123\n')
                f.write('test@example.com:testpass\n')
                f.write('192.168.1.1:admin:admin123\n')
                f.write('URL: https://example.com/login\n')
                f.write('Username: testuser@email.com\n')
                f.write('Password: testpass123\n')
                f.write('Application: Google_[Chrome]_Default\n')
                f.write('===============\n')
        print("✅ Örnek dosyalar oluşturuldu!")
    
    print("=" * 60)
    print("🚀 ACCOUNT SEARCH API - UNIVERSAL PARSER")
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
    print("📋 DESTEKLENEN FORMATLAR (OTOMATİK TESPİT):")
    print("   ✅ Stealer Log (URL, Username, Password, Application)")
    print("   ✅ Android Format (android://TOKEN@PACKAGE/:USER:PASS)")
    print("   ✅ Standart Format (username:password)")
    print("   ✅ URL Format (url:username:password)")
    print("   ✅ Tüm diğer formatlar (ham olarak)")
    print("=" * 60)
    print("📡 KULLANIM:")
    print("   # Sadece ?q=parametresi yeterli")
    print("   curl 'http://localhost:5000/search?q=testuser'")
    print("   curl 'http://localhost:5000/search?q=android'")
    print("   curl 'http://localhost:5000/search?q=hotmail.com'")
    print("=" * 60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True) 
