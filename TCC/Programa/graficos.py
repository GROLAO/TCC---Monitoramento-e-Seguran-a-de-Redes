import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


latencias = []
jitters = []
perdas = []
velocidades_download = []
velocidades_upload = []

def registrar_latencia(host, latencia, jitter=None, packet_loss=None):
    tempo = datetime.now()
    latencias.append((host, latencia, tempo))
    if jitter is not None:
        jitters.append((host, jitter, tempo))
    if packet_loss is not None:
        perdas.append((host, packet_loss, tempo))

def registrar_velocidade(velocidade):
    tempo = datetime.now()
    velocidades_download.append((tempo, velocidade['download']))
    velocidades_upload.append((tempo, velocidade['upload']))


def obter_dados_para_graficos():
    if not latencias or not velocidades_download:
        return None
    hosts = list(set(host for host, _, _ in latencias))
    dados_graficos = {
        'latencia': {}, 'jitter': {}, 'perda': {},
        'velocidade': {
            'tempo_download': [t for t, _ in velocidades_download],
            'download': [v for _, v in velocidades_download],
            'tempo_upload': [t for t, _ in velocidades_upload],
            'upload': [v for _, v in velocidades_upload]
        }
    }
    for host in hosts:
        dados_graficos['latencia'][host] = {
            'x': [tempo for h, _, tempo in latencias if h == host],
            'y': [lat for h, lat, _ in latencias if h == host]
        }
        dados_graficos['jitter'][host] = {
            'x': [tempo for h, _, tempo in jitters if h == host],
            'y': [j for h, j, _ in jitters if h == host]
        }
        dados_graficos['perda'][host] = {
            'x': [tempo for h, _, tempo in perdas if h == host],
            'y': [p for h, p, _ in perdas if h == host]
        }
    return dados_graficos