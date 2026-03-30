"""
Cross-Selling Zuordnungs-Tool - Flask Web App

Standalone-Anwendung: Einfach mit `python app.py` starten.
Alle Abhängigkeiten werden automatisch geprüft und ggf. installiert.

Voraussetzungen:
  - Python 3.10+
  - data/zubehoer.csv (Pool aller CS-Artikel)
  - data/crossselling-kriterien.xlsx (Kriterien-Datei)

Dokumentation: Siehe DOCUMENTATION.md im Projektordner.
"""

import subprocess
import sys
import os

# Windows-Terminal UTF-8 Kompatibilität: Verhindert UnicodeEncodeError bei Emojis
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)


def check_and_install_dependencies():
    """Prüft ob alle Abhängigkeiten installiert sind und installiert fehlende."""
    required = {
        'pandas': 'pandas>=2.0.0',
        'openpyxl': 'openpyxl>=3.1.0',
        'flask': 'flask>=3.0.0',
    }
    missing = []
    for module, pip_name in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pip_name)
    
    if missing:
        print(f"\n[*] Installiere fehlende Pakete: {', '.join(missing)}")
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install'] + missing,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print("[OK] Alle Pakete erfolgreich installiert.\n")
        except subprocess.CalledProcessError:
            print("[FEHLER] Fehler beim Installieren der Pakete.")
            print(f"   Bitte manuell installieren: pip install {' '.join(missing)}")
            sys.exit(1)


# Abhängigkeiten prüfen BEVOR imports
check_and_install_dependencies()

from flask import Flask, render_template, request, jsonify, send_file, Response
import pandas as pd
from pathlib import Path
import shutil
import random
import socket
import webbrowser
import threading
import json
import time
import uuid

from data_loader import (
    load_zubehoer, load_kriterien, load_produkte, save_zubehoer,
    ensure_directories, ZUBEHOER_FILE, DATA_DIR, UPLOADS_DIR, OUTPUTS_DIR
)
from matching import process_all_products, find_crossselling_articles, get_value
from output_writer import save_result, format_preview_table

# ========================================
# KONFIGURATION
# ========================================
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 7877
AUTO_OPEN_BROWSER = True

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Globale Variablen für geladene Daten
zubehoer_df = None
kriterien = None
zubehoer_status = ""
kriterien_status = ""

# Verarbeitungsstatus für Fortschrittsanzeige
processing_jobs = {}  # {job_id: {progress, message, status, result}}


def init_data():
    """Initialisiert die Daten beim Start."""
    global zubehoer_df, kriterien, zubehoer_status, kriterien_status
    
    ensure_directories()
    
    zubehoer_df, zubehoer_status = load_zubehoer()
    kriterien, kriterien_status = load_kriterien()


# ========================================
# FLASK ROUTES
# ========================================

@app.route('/')
def index():
    """Hauptseite."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Gibt den aktuellen Status der Datenquellen zurück."""
    return jsonify({
        'zubehoer': {
            'loaded': zubehoer_df is not None,
            'status': zubehoer_status,
            'count': len(zubehoer_df) if zubehoer_df is not None else 0,
        },
        'kriterien': {
            'loaded': kriterien is not None,
            'status': kriterien_status,
        }
    })


@app.route('/api/upload-zubehoer', methods=['POST'])
def api_upload_zubehoer():
    """Ersetzt die Zubehör-Datenbank."""
    global zubehoer_df, zubehoer_status
    
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei hochgeladen'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Keine Datei ausgewählt'}), 400
    
    # Temporär speichern
    temp_path = UPLOADS_DIR / file.filename
    file.save(str(temp_path))
    
    success, msg = save_zubehoer(str(temp_path))
    
    if success:
        zubehoer_df, zubehoer_status = load_zubehoer()
    
    # Temporäre Datei aufräumen
    if temp_path.exists():
        temp_path.unlink()
    
    return jsonify({
        'success': success,
        'zubehoer': {
            'loaded': zubehoer_df is not None,
            'status': zubehoer_status,
            'count': len(zubehoer_df) if zubehoer_df is not None else 0,
        }
    })


@app.route('/api/process', methods=['POST'])
def api_process():
    """Startet die Verarbeitung einer Produktliste."""
    global zubehoer_df, kriterien
    
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei hochgeladen'}), 400
    
    if zubehoer_df is None:
        return jsonify({'error': 'Zubehör-Datenbank nicht geladen'}), 400
    
    if kriterien is None:
        return jsonify({'error': 'Kriterien-Datei nicht geladen'}), 400
    
    file = request.files['file']
    parallel_count = int(request.form.get('parallel_count', 10))
    
    # Datei speichern
    temp_path = UPLOADS_DIR / file.filename
    file.save(str(temp_path))
    
    # Job erstellen
    job_id = str(uuid.uuid4())
    processing_jobs[job_id] = {
        'progress': 0,
        'message': 'Starte Verarbeitung...',
        'status': 'running',
        'result': None,
        'error': None,
    }
    
    # Verarbeitung in eigenem Thread starten
    thread = threading.Thread(
        target=_process_worker,
        args=(job_id, str(temp_path), file.filename, parallel_count)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'job_id': job_id})


def _process_worker(job_id, file_path, original_filename, parallel_count):
    """Worker-Thread für die Verarbeitung."""
    global zubehoer_df, kriterien
    
    job = processing_jobs[job_id]
    
    try:
        produkte_df, status = load_produkte(file_path)
        
        if produkte_df is None:
            job['status'] = 'error'
            job['error'] = status
            return
        
        def update_progress(pct, msg):
            job['progress'] = round(pct * 100)
            job['message'] = msg
        
        result_df = process_all_products(
            produkte_df,
            zubehoer_df,
            kriterien,
            progress_callback=update_progress,
            parallel_count=parallel_count
        )
        
        output_path, save_status = save_result(result_df, original_filename, OUTPUTS_DIR)
        
        total = len(result_df)
        with_cs = len(result_df[result_df['crossselling'].str.len() > 0])
        without_cs = total - with_cs
        
        # Ergebnistabelle aufbauen
        rows = []
        for i in range(len(result_df)):
            row = result_df.iloc[i]
            prod = produkte_df.iloc[i]
            
            name = get_value(prod, ['produktname', 'name', 'bezeichnung', 'title']) or f'Produkt {i+1}'
            hersteller = get_value(prod, ['hersteller', 'marke', 'brand']) or ''
            artikelnr = get_value(prod, ['artikel_id', 'artikelnummer', 'id', 'sku', 'artikelnr']) or ''
            cs_namen = str(row.get('crossselling_namen', ''))
            cs_count = len(cs_namen.split(',')) if cs_namen else 0
            
            rows.append({
                'index': i,
                'nr': i + 1,
                'artikelnr': str(artikelnr),
                'hersteller': hersteller,
                'name': name,
                'cs_namen': cs_namen,
                'cs_count': cs_count,
            })
        
        job['status'] = 'done'
        job['progress'] = 100
        job['message'] = 'Abgeschlossen'
        job['result'] = {
            'total': total,
            'with_cs': with_cs,
            'without_cs': without_cs,
            'output_path': output_path,
            'output_filename': Path(output_path).name if output_path else '',
            'save_status': save_status,
            'rows': rows,
        }
        
        # Temporäre Upload-Datei aufräumen
        temp = Path(file_path)
        if temp.exists():
            temp.unlink()
    
    except Exception as e:
        job['status'] = 'error'
        job['error'] = str(e)


@app.route('/api/progress/<job_id>')
def api_progress(job_id):
    """SSE-Endpunkt für Fortschrittsupdates."""
    def generate():
        while True:
            job = processing_jobs.get(job_id)
            if not job:
                yield f"data: {json.dumps({'status': 'error', 'error': 'Job nicht gefunden'})}\n\n"
                break
            
            payload = {
                'progress': job['progress'],
                'message': job['message'],
                'status': job['status'],
            }
            
            if job['status'] == 'done':
                payload['result'] = job['result']
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break
            elif job['status'] == 'error':
                payload['error'] = job['error']
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break
            
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            time.sleep(0.3)
    
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/api/download/<path:filename>')
def api_download(filename):
    """Ergebnis-Datei herunterladen."""
    file_path = OUTPUTS_DIR / filename
    if file_path.exists():
        return send_file(str(file_path), as_attachment=True)
    return jsonify({'error': 'Datei nicht gefunden'}), 404


@app.route('/api/recalc', methods=['POST'])
def api_recalc():
    """Einzelnes Produkt neu berechnen."""
    global zubehoer_df, kriterien
    
    data = request.json
    job_id = data.get('job_id')
    product_index = data.get('index')
    
    job = processing_jobs.get(job_id)
    if not job or job['status'] != 'done':
        return jsonify({'error': 'Job nicht gefunden oder nicht abgeschlossen'}), 400
    
    output_path = job['result']['output_path']
    
    # Ergebnis-Datei neu laden
    result_df = pd.read_excel(output_path, engine='openpyxl')
    # Original-Produktdaten aus der Ergebnis-Datei holen
    produkt = result_df.iloc[product_index]
    
    articles, hinweise = find_crossselling_articles(
        produkt, zubehoer_df, kriterien, variation_index=random.randint(1, 1000)
    )
    
    cs_str = ""
    cs_n = ""
    if articles:
        cs_str = ";".join(f"{a['artikel_id']}:Accessory" for a in articles) + ";"
        cs_n = ", ".join(a['name'] for a in articles)
    
    # Sicherstellen dass Spalten als String-Typ vorliegen (vermeidet FutureWarning)
    for col in ['crossselling', 'crossselling_namen', 'cs_hinweis']:
        if col in result_df.columns:
            result_df[col] = result_df[col].astype(str)
    
    ridx = result_df.index[product_index]
    result_df.at[ridx, 'crossselling'] = cs_str
    result_df.at[ridx, 'crossselling_namen'] = cs_n
    result_df.at[ridx, 'cs_hinweis'] = "; ".join(hinweise) if hinweise else ""
    
    result_df.to_excel(output_path, index=False, engine='openpyxl')
    
    # Job-Ergebnis aktualisieren
    row_data = job['result']['rows'][product_index]
    row_data['cs_namen'] = cs_n
    row_data['cs_count'] = len(articles) if articles else 0
    
    # Statistiken neu berechnen
    total = len(result_df)
    with_cs = len(result_df[result_df['crossselling'].str.len() > 0])
    job['result']['with_cs'] = with_cs
    job['result']['without_cs'] = total - with_cs
    
    return jsonify({
        'success': True,
        'cs_namen': cs_n,
        'cs_count': len(articles) if articles else 0,
        'with_cs': with_cs,
        'without_cs': total - with_cs,
    })


# ========================================
# HILFSFUNKTIONEN
# ========================================

def is_port_in_use(host: str, port: int) -> bool:
    """Prüft ob ein Port bereits belegt ist."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_free_port(host: str, start_port: int) -> int:
    """Findet einen freien Port ab start_port."""
    port = start_port
    while is_port_in_use(host, port):
        print(f"[!] Port {port} ist belegt, versuche {port + 1}...")
        port += 1
        if port > start_port + 20:
            print("[FEHLER] Kein freier Port gefunden. Bitte andere Anwendungen schliessen.")
            sys.exit(1)
    return port


def print_startup_banner(host: str, port: int):
    """Zeigt Startup-Informationen im Terminal."""
    url = f"http://{host}:{port}"
    print("")
    print("=" * 60)
    print("  Cross-Selling Zuordnungs-Tool")
    print("=" * 60)
    print(f"  URL:     {url}")
    print(f"  Status:  {zubehoer_status}")
    print(f"  Status:  {kriterien_status}")
    print("-" * 60)
    print("  1. Produktliste (.xlsx) in der App hochladen")
    print("  2. 'Cross-Selling berechnen' klicken")
    print("  3. Ergebnis wird in outputs/ gespeichert")
    print("-" * 60)
    print("  Beenden: Ctrl+C im Terminal")
    print("=" * 60)
    print("")


if __name__ == "__main__":
    # Verzeichnisse & Daten initialisieren
    print("\n[*] Initialisiere Daten...")
    init_data()
    
    # Prüfe ob Pflichtdateien vorhanden sind
    if zubehoer_df is None:
        print(f"\n[!] WARNUNG: {ZUBEHOER_FILE} nicht gefunden!")
        print("   Die App startet trotzdem - bitte zubehoer.csv in der App hochladen.")
    
    if kriterien is None:
        print(f"\n[!] WARNUNG: Kriterien-Datei nicht gefunden!")
        print("   Bitte data/crossselling-kriterien.xlsx bereitstellen.")
    
    # Freien Port finden
    port = find_free_port(SERVER_HOST, SERVER_PORT)
    
    # Startup-Info anzeigen
    print_startup_banner(SERVER_HOST, port)
    
    # Browser automatisch öffnen
    if AUTO_OPEN_BROWSER:
        url = f"http://{SERVER_HOST}:{port}"
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    
    try:
        app.run(host=SERVER_HOST, port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\n[*] Server beendet (Ctrl+C).")
    except Exception as e:
        print(f"\n[FEHLER] Fehler beim Starten: {e}")
        print("   Versuche: pip install -r requirements.txt")
        sys.exit(1)
