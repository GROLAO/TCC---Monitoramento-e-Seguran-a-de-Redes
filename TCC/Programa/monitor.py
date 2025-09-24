import platform
import subprocess
import time
import socket
from datetime import datetime
import os
import speedtest
from winsound import Beep
from colorama import Fore, Style, init

init(autoreset=True)  

# 🔁 Histórico de latência para cálculo de jitter
latencia_anterior = {}

# 📊 Contadores para packet loss
contagem_total = {}
contagem_falhas = {}

# 🧮 Função auxiliar para calcular jitter simples
def calcular_jitter(host, nova_latencia):
    if host not in latencia_anterior:
        latencia_anterior[host] = nova_latencia
        return 0.0
    jitter = abs(nova_latencia - latencia_anterior[host])
    latencia_anterior[host] = nova_latencia
    return round(jitter, 2)

# 🔢 Função auxiliar para calcular perda de pacotes em %
def calcular_packet_loss(host):
    total = contagem_total.get(host, 1)
    falhas = contagem_falhas.get(host, 0)
    return round((falhas / total) * 100, 2)

def ping(host):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    comando = ["ping", param, "1", host]

    contagem_total[host] = contagem_total.get(host, 0) + 1

    try:
        inicio = time.time()
        output = subprocess.check_output(comando, stderr=subprocess.STDOUT, universal_newlines=True)
        fim = time.time()
        latencia_calc = round((fim - inicio) * 1000, 2)

        ttl = None
        tempo_resposta = None
        for linha in output.splitlines():
            if "TTL=" in linha.upper():
                partes = linha.replace("=", " ").split()
                for i, parte in enumerate(partes):
                    if parte.upper() == "TTL":
                        try:
                            ttl = int(partes[i + 1])
                        except:
                            ttl = None
                    if parte.lower() == "tempo" or "time" in parte.lower():
                        try:
                            tempo_resposta = int(''.join(filter(str.isdigit, partes[i + 1])))
                        except:
                            pass

        try:
            nome = socket.gethostbyaddr(host)[0]
        except:
            nome = "Desconhecido"

        # ✅ Calcular jitter
        jitter = calcular_jitter(host, tempo_resposta or latencia_calc)

        return {
            "status": True,
            "host": host,
            "nome": nome,
            "tempo_resposta": tempo_resposta,
            "latencia_calc": latencia_calc,
            "ttl": ttl,
            "jitter": jitter,
            "packet_loss": calcular_packet_loss(host)
        }

    except subprocess.CalledProcessError:
        # ❌ Incrementar falha
        contagem_falhas[host] = contagem_falhas.get(host, 0) + 1
        return {
            "status": False,
            "host": host,
            "nome": None,
            "tempo_resposta": None,
            "latencia_calc": None,
            "ttl": None,
            "jitter": None,
            "packet_loss": calcular_packet_loss(host)
        }

def testar_velocidade():
    print(Fore.CYAN + "\n🚀 Testando velocidade da conexão...\n")
    st = speedtest.Speedtest()
    download = round(st.download() / 1_000_000, 2)
    upload = round(st.upload() / 1_000_000, 2)
    ping_valor = round(st.results.ping, 2)

    print(Fore.YELLOW + f"🡻 Download: {download} Mbps")
    print(Fore.YELLOW + f"🡹 Upload:   {upload} Mbps")
    print(Fore.YELLOW + f"📶 Ping:     {ping_valor} ms\n")

    return {
        "download": download,
        "upload": upload,
        "ping": ping_valor
    }

def salvar_log(mensagem):
    data = datetime.now().strftime("%Y-%m-%d")
    hora = datetime.now().strftime("%H:%M:%S")
    if not os.path.exists("logs"):
        os.makedirs("logs")
    with open(f"logs/{data}.log", "a") as f:
        f.write(f"[{hora}] {mensagem}\n")

def alerta_sonoro():
    Beep(1000, 500)