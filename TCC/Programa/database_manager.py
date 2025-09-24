import sqlite3
from datetime import datetime
import csv
import pandas as pd 

DB_FILE = "monitoring_history.db"

def setup_database():
    """Cria as tabelas no banco de dados se elas não existirem."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS speed_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            download_mbps REAL NOT NULL,
            upload_mbps REAL NOT NULL,
            ping_ms REAL NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ping_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            host TEXT NOT NULL,
            latency_ms REAL,
            jitter_ms REAL,
            packet_loss_percent REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            mac_address TEXT NOT NULL,
            vendor TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_speed_test(download, upload, ping):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO speed_history (timestamp, download_mbps, upload_mbps, ping_ms) VALUES (?, ?, ?, ?)",
                   (timestamp, download, upload, ping))
    conn.commit()
    conn.close()

def log_ping_result(host, latency, jitter, packet_loss):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO ping_history (timestamp, host, latency_ms, jitter_ms, packet_loss_percent) VALUES (?, ?, ?, ?, ?)",
                   (timestamp, host, latency, jitter, packet_loss))
    conn.commit()
    conn.close()

def log_device_change(event_type, ip, mac, vendor):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO device_log (timestamp, event_type, ip_address, mac_address, vendor) VALUES (?, ?, ?, ?, ?)",
                   (timestamp, event_type, ip, mac, vendor))
    conn.commit()
    conn.close()

def fetch_data_as_dataframe(table_name):
    """Busca todos os dados de uma tabela e retorna como um DataFrame do Pandas."""
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY timestamp DESC", conn)
        if 'id' in df.columns:
            df = df.drop(columns=['id'])
        return df
    except Exception as e:
        print(f"Erro ao buscar dados da tabela {table_name}: {e}")
        return pd.DataFrame()
    finally:
        conn.close()