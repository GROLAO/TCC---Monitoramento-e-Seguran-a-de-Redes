import threading
import time
import math
import csv
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

import pandas as pd

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from graficos import registrar_latencia, registrar_velocidade, obter_dados_para_graficos
from monitor import ping, testar_velocidade
from network_scanner import scan_network
import database_manager

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitoramento de Rede - TCC")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1c1c1c")

        self.monitorando = False
        self.log_text = ""
        self.thread = None 
        self.velocidade_anterior_down = 0.0
        self.velocidade_anterior_up = 0.0
        self.known_devices_map = {}
        database_manager.setup_database()

        style = ttk.Style()
        style.theme_use('clam'); BG_DARK = "#1c1c1c"; FG_LIGHT = "#e0e0e0"; ACCENT_COLOR = "#00bfff"
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background="#2c2c2c", foreground="#a0a0a0", font=("Segoe UI", 10, "bold"), padding=[10, 5], relief="flat")
        style.map("TNotebook.Tab", background=[('selected', BG_DARK)], foreground=[('selected', FG_LIGHT)])
        style.configure("Dark.TButton", background="#333333", foreground=FG_LIGHT, font=("Segoe UI", 10, "bold"), padding=8, relief="flat")
        style.map("Dark.TButton", background=[('active', '#555555')])
        style.configure("Treeview", background="#222222", foreground=FG_LIGHT, fieldbackground="#222222", rowheight=28, font=("Segoe UI", 10))
        style.map("Treeview", background=[('selected', ACCENT_COLOR)])
        style.configure("Treeview.Heading", background="#333333", foreground=ACCENT_COLOR, font=("Segoe UI", 10, "bold"))

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.tab_monitoramento = Frame(self.notebook, bg=BG_DARK); self.notebook.add(self.tab_monitoramento, text="Monitoramento")
        self.tab_graficos = Frame(self.notebook, bg=BG_DARK); self.notebook.add(self.tab_graficos, text="Gráficos")
        self.tab_dispositivos = Frame(self.notebook, bg=BG_DARK); self.notebook.add(self.tab_dispositivos, text="Dispositivos na Rede")
        self.tab_historico = Frame(self.notebook, bg=BG_DARK); self.notebook.add(self.tab_historico, text="Histórico")
        
        self.criar_widgets_dispositivos()
        self.criar_widgets_monitoramento()
        self.criar_widgets_graficos()
        self.criar_widgets_historico()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def criar_widgets_dispositivos(self):
        top_device_frame = Frame(self.tab_dispositivos, bg="#1c1c1c"); top_device_frame.pack(fill=X, padx=15, pady=15)
        self.label_device_count = Label(top_device_frame, text="Dispositivos conectados: 0", font=("Segoe UI", 12, "bold"), bg="#1c1c1c", fg="#e0e0e0"); self.label_device_count.pack(side=LEFT)
        self.btn_refresh_devices = ttk.Button(top_device_frame, text="Escanear Rede", command=self.start_device_scan_thread, style="Dark.TButton"); self.btn_refresh_devices.pack(side=RIGHT)
        self.device_tree = ttk.Treeview(self.tab_dispositivos, columns=('ip', 'mac', 'vendor'), show='headings')
        self.device_tree.heading('ip', text='Endereço IP'); self.device_tree.heading('mac', text='Endereço MAC'); self.device_tree.heading('vendor', text='Fabricante / Modelo')
        self.device_tree.column('ip', width=150, anchor=CENTER); self.device_tree.column('mac', width=180, anchor=CENTER); self.device_tree.column('vendor', width=300)
        self.device_tree.pack(fill=BOTH, expand=True, padx=15, pady=5)
        
    def criar_widgets_monitoramento(self):
        monitor_frame = Frame(self.tab_monitoramento, bg="#1c1c1c"); monitor_frame.pack(fill=BOTH, expand=True)
        self.text_area = Text(monitor_frame, height=10, font=("Consolas", 12), bg="#2c2c2c", fg="#00ff00", insertbackground="white", relief="flat", bd=0, padx=10, pady=10, state="disabled")
        self.text_area.pack(fill=X, padx=15, pady=15)
        btn_frame = Frame(monitor_frame, bg="#1c1c1c"); btn_frame.pack(pady=5)
        self.btn_iniciar = ttk.Button(btn_frame, text="Iniciar Monitoramento", command=self.iniciar_monitoramento, style="Dark.TButton"); self.btn_iniciar.pack(side=LEFT, padx=10)
        self.btn_parar = ttk.Button(btn_frame, text="Parar Monitoramento", command=self.parar_monitoramento, style="Dark.TButton", state=DISABLED); self.btn_parar.pack(side=LEFT, padx=10)
        self.velocimetro_frame = Frame(self.tab_monitoramento, bg="#1c1c1c"); self.velocimetro_frame.pack(fill=BOTH, expand=True, pady=10, padx=15)
        self.fig_velo, self.ax_velo = plt.subplots(subplot_kw={'projection': 'polar'})
        self.canvas_velo = FigureCanvasTkAgg(self.fig_velo, master=self.velocimetro_frame); self.canvas_velo.get_tk_widget().pack(fill=BOTH, expand=True)
        self.configurar_velocimetro()

    def criar_widgets_graficos(self):
        top_graficos_frame = Frame(self.tab_graficos, bg="#1c1c1c"); top_graficos_frame.pack(fill=X, padx=15, pady=15)
        label_graficos_titulo = Label(top_graficos_frame, text="Gráficos de Desempenho", font=("Segoe UI", 12, "bold"), bg="#1c1c1c", fg="#e0e0e0"); label_graficos_titulo.pack(side=LEFT)
        self.btn_atualizar = ttk.Button(top_graficos_frame, text="Atualizar Gráficos", command=self.atualizar_graficos, style="Dark.TButton"); self.btn_atualizar.pack(side=RIGHT)
        bottom_frame = Frame(self.tab_graficos, bg="#1c1c1c"); bottom_frame.pack(fill=BOTH, expand=True, pady=10, padx=15)
        self.frame_graf1 = Frame(bottom_frame, bg="#1c1c1c"); self.frame_graf1.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)
        self.frame_graf2 = Frame(bottom_frame, bg="#1c1c1c"); self.frame_graf2.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)
        self.configurar_graficos()

    def criar_widgets_historico(self):
        historico_frame = Frame(self.tab_historico, bg="#1c1c1c"); historico_frame.pack(pady=20, padx=20)
        Label(historico_frame, text="Exportar Dados Históricos", font=("Segoe UI", 16, "bold"), bg="#1c1c1c", fg="#e0e0e0").pack(pady=(0, 20))
        ttk.Button(historico_frame, text="Exportar Relatório Completo (Excel)", command=self.export_data_to_excel, style="Dark.TButton").pack(fill=X, pady=5)

    def on_closing(self):
        if self.monitorando: self.monitorando = False; self._check_if_thread_is_dead()
        else: self.root.destroy()

    def _check_if_thread_is_dead(self):
        if self.thread is not None and self.thread.is_alive(): self.root.after(100, self._check_if_thread_is_dead)
        else: self.root.destroy()

    def configurar_velocimetro(self):
        self.ax_velo.clear(); self.ax_velo.set_theta_zero_location('N'); self.ax_velo.set_theta_direction(-1); self.ax_velo.set_ylim(0, 1.1); self.ax_velo.set_facecolor('#1c1c1c'); self.fig_velo.patch.set_facecolor('#1c1c1c')
        self.ticks_config = {'0': 0.0, '5': 0.1, '10': 0.2, '50': 0.35, '100': 0.45, '250': 0.6, '500': 0.75, '750': 0.88, '1000': 1.0}
        total_angle = np.pi * 1.5; start_angle = -np.pi * 0.75
        for label, position in self.ticks_config.items():
            angle = start_angle + position * total_angle
            self.ax_velo.text(angle, 1.2, label, ha='center', va='center', color='#a0a0a0', fontsize=9)
        angles_base = np.linspace(start_angle, start_angle + total_angle, 100); radii_base = np.ones_like(angles_base)
        self.ax_velo.plot(angles_base, radii_base, color='#333333', linewidth=40, solid_capstyle='round')
        self.arco_download = self.ax_velo.plot([], [], color='#00bfff', linewidth=40, solid_capstyle='round')[0]
        self.arco_upload = self.ax_velo.plot([], [], color='#00ff7f', linewidth=40, solid_capstyle='round')[0]
        self.texto_velocidade_central = self.ax_velo.text(0, 0, "↓ 0.0 Mbps\n↑ 0.0 Mbps", ha='center', va='center', fontdict={'fontsize': 22, 'color': 'white', 'fontweight': 'bold', 'family': 'Segoe UI'})
        legend_line_down, = self.ax_velo.plot([], [], color='#00bfff', linewidth=5); legend_line_up, = self.ax_velo.plot([], [], color='#00ff7f', linewidth=5)
        self.ax_velo.legend([legend_line_down, legend_line_up], ['↓ Download', '↑ Upload'], loc='upper center', bbox_to_anchor=(0.5, 0.2), frameon=True, facecolor="#3a3a3a", edgecolor="#555555", labelcolor="white", fontsize=10)
        self.ax_velo.set_axis_off(); self.canvas_velo.draw()

    def atualizar_velocimetro(self, velocidade):
        val_final_down = velocidade['download']; val_final_up = velocidade['upload']
        self.animar_velocimetro(self.velocidade_anterior_down, val_final_down, self.velocidade_anterior_up, val_final_up)
        self.velocidade_anterior_down = val_final_down; self.velocidade_anterior_up = val_final_up

    def animar_velocimetro(self, val_inicial_down, val_final_down, val_inicial_up, val_final_up, duracao_ms=700):
        start_time = time.time(); total_angle = np.pi * 1.5; start_angle = -np.pi * 0.75
        speed_scale = [float(k) for k in self.ticks_config.keys()]; arc_scale = list(self.ticks_config.values())
        def ease_in_out_sine(x): return -(math.cos(math.pi * x) - 1) / 2
        def _step():
            elapsed = (time.time() - start_time) * 1000; progress = min(elapsed / duracao_ms, 1.0)
            eased_progress = ease_in_out_sine(progress)
            current_down = val_inicial_down + (val_final_down - val_inicial_down) * eased_progress
            current_up = val_inicial_up + (val_final_up - val_inicial_up) * eased_progress
            self.texto_velocidade_central.set_text(f"↓ {current_down:.1f} Mbps\n↑ {current_up:.1f} Mbps")
            download_frac = np.interp(current_down, speed_scale, arc_scale); upload_frac = np.interp(current_up, speed_scale, arc_scale)
            download_angle_end = start_angle + download_frac * total_angle; upload_angle_end = start_angle + upload_frac * total_angle
            self.arco_download.set_data(np.linspace(start_angle, download_angle_end, 100), np.ones(100))
            self.arco_upload.set_data(np.linspace(start_angle, upload_angle_end, 100), np.ones(100))
            self.canvas_velo.draw_idle()
            if progress < 1.0: self.root.after(15, _step)
        _step()
    
    def append_log(self, texto):
        if self.text_area.winfo_exists():
            self.text_area.config(state="normal"); self.log_text += texto + "\n"; self.text_area.delete(1.0, END); self.text_area.insert(END, self.log_text); self.text_area.see(END); self.text_area.config(state="disabled")

    def start_device_scan_thread(self):
        if self.btn_refresh_devices.winfo_exists(): self.btn_refresh_devices.config(state=DISABLED, text="Verificando...")
        if self.device_tree.winfo_exists(): [self.device_tree.delete(i) for i in self.device_tree.get_children()]
        if self.label_device_count.winfo_exists(): self.label_device_count.config(text="Procurando dispositivos...")
        scan_thread = threading.Thread(target=self.update_device_list, daemon=True); scan_thread.start()

    def update_device_list(self):
        try:
            devices = scan_network()
            current_devices_map = {d['mac']: d for d in devices}
            current_macs = set(current_devices_map.keys())
            known_macs = set(self.known_devices_map.keys())
            new_macs = current_macs - known_macs
            for mac in new_macs:
                device = current_devices_map[mac]
                database_manager.log_device_change('CONECTADO', device['ip'], device['mac'], device['vendor'])
            disconnected_macs = known_macs - current_macs
            for mac in disconnected_macs:
                device = self.known_devices_map[mac]
                database_manager.log_device_change('DESCONECTADO', device['ip'], device['mac'], device['vendor'])
            self.known_devices_map = current_devices_map
            if self.label_device_count.winfo_exists():
                 self.label_device_count.config(text=f"Dispositivos conectados: {len(devices)}")
                 for device in devices: self.device_tree.insert('', END, values=(device['ip'], device['mac'], device['vendor']))
        except Exception as e:
            messagebox.showerror("Erro", f"Erro na varredura de dispositivos: {e}")
        finally:
            if self.btn_refresh_devices.winfo_exists(): self.btn_refresh_devices.config(state=NORMAL, text="Atualizar Lista")

    def monitorar_loop(self):
        dispositivos = ["8.8.8.8", "github.com"]
        while self.monitorando:
            for host in dispositivos:
                if not self.monitorando: break
                resultado = ping(host)
                database_manager.log_ping_result(host=host, latency=resultado['tempo_resposta'], jitter=resultado.get('jitter'), packet_loss=resultado.get('packet_loss'))
                log_msg = f"{'ONLINE' if resultado['status'] else 'OFFLINE'} - {host} | Resp: {resultado['tempo_resposta'] or 'N/A'} ms | Jitter: {resultado.get('jitter', '-') if resultado.get('jitter') is not None else '-'} | Perda: {resultado.get('packet_loss', '-')}%"
                self.root.after(0, self.append_log, log_msg)
                registrar_latencia(host, resultado['tempo_resposta'] or 0, jitter=resultado.get('jitter'), packet_loss=resultado.get('packet_loss'))
            
            if not self.monitorando: break
            
            velocidade = testar_velocidade()
            database_manager.log_speed_test(download=velocidade['download'], upload=velocidade['upload'], ping=velocidade.get('ping', 0))
            self.root.after(0, self.append_log, f"Velocidade: ↓ {velocidade['download']:.2f} Mbps | ↑ {velocidade['upload']:.2f} Mbps")
            registrar_velocidade(velocidade)
            
            self.root.after(0, self.atualizar_velocimetro, velocidade)
            self.root.after(0, self.atualizar_graficos)
            self.root.after(0, self.start_device_scan_thread)

            for _ in range(30):
                if not self.monitorando: break
                time.sleep(1)

    def iniciar_monitoramento(self):
        if not self.monitorando:
            self.append_log("Iniciando monitoramento...")
            self.monitorando = True
            self.thread = threading.Thread(target=self.monitorar_loop, daemon=True)
            self.thread.start()
            self.btn_iniciar.config(state=DISABLED); self.btn_parar.config(state=NORMAL)
            
    def parar_monitoramento(self):
        if self.monitorando:
            self.append_log("Parando monitoramento...")
            self.monitorando = False
            self.btn_iniciar.config(state=NORMAL); self.btn_parar.config(state=DISABLED)

    def configurar_graficos(self):
        self.fig_lat, self.axs_lat = plt.subplots(2, 1, figsize=(8, 8), sharex=True); self.canvas_lat = FigureCanvasTkAgg(self.fig_lat, master=self.frame_graf1); self.canvas_lat.get_tk_widget().pack(fill=BOTH, expand=True)
        self.fig_vel_graf, self.axs_vel_graf = plt.subplots(2, 1, figsize=(8, 8), sharex=True); self.canvas_vel_graf = FigureCanvasTkAgg(self.fig_vel_graf, master=self.frame_graf2); self.canvas_vel_graf.get_tk_widget().pack(fill=BOTH, expand=True)
        self.linhas_latencia, self.linhas_jitter, self.linhas_perda = {}, {}, {}
        self.linha_download, = self.axs_vel_graf[0].plot([], [], label="Download (Mbps)", color="#00bfff"); self.linha_upload, = self.axs_vel_graf[0].plot([], [], label="Upload (Mbps)", color="#00ff7f")
        figs = {'latencia': self.fig_lat, 'velocidade': self.fig_vel_graf}
        for nome, fig in figs.items():
            fig.patch.set_facecolor('#1c1c1c')
            for ax in fig.axes:
                ax.set_facecolor('#2c2c2c'); ax.tick_params(colors='white'); [spine.set_color('#444444') for spine in ax.spines.values()]
                ax.title.set_color('#e0e0e0'); ax.xaxis.label.set_color('#a0a0a0'); ax.yaxis.label.set_color('#a0a0a0'); ax.grid(color='#444444', linestyle=':', linewidth=0.5)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.axs_lat[0].set_title("Latência por Host"); self.axs_lat[0].set_ylabel("Latência (ms)"); self.axs_lat[1].set_title("Jitter por Host"); self.axs_lat[1].set_ylabel("Jitter (ms)")
        self.axs_vel_graf[0].set_title("Velocidade da Conexão"); self.axs_vel_graf[0].set_ylabel("Mbps"); self.axs_vel_graf[1].set_title("Perda de Pacotes por Host"); self.axs_vel_graf[1].set_ylabel("Perda (%)")
        self.fig_lat.tight_layout(); self.fig_vel_graf.tight_layout()
            
    def atualizar_graficos(self):
        dados = obter_dados_para_graficos()
        if dados is None: return
        hosts = dados['latencia'].keys()
        for host in hosts:
            if host not in self.linhas_latencia:
                self.linhas_latencia[host], = self.axs_lat[0].plot([], [], label=host); self.linhas_jitter[host], = self.axs_lat[1].plot([], [], label=host); self.linhas_perda[host], = self.axs_vel_graf[1].plot([], [], label=host)
            self.linhas_latencia[host].set_data(dados['latencia'][host]['x'], dados['latencia'][host]['y']); self.linhas_jitter[host].set_data(dados['jitter'][host]['x'], dados['jitter'][host]['y']); self.linhas_perda[host].set_data(dados['perda'][host]['x'], dados['perda'][host]['y'])
        self.linha_download.set_data(dados['velocidade']['tempo_download'], dados['velocidade']['download']); self.linha_upload.set_data(dados['velocidade']['tempo_upload'], dados['velocidade']['upload'])
        for ax in self.fig_lat.axes: ax.relim(); ax.autoscale_view(); ax.legend(facecolor='#3a3a3a', edgecolor='#555555', labelcolor='white')
        for ax in self.fig_vel_graf.axes: ax.relim(); ax.autoscale_view(); ax.legend(facecolor='#3a3a3a', edgecolor='#555555', labelcolor='white')
        self.canvas_lat.draw(); self.canvas_vel_graf.draw()

    def export_data_to_excel(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Salvar Relatório Completo",
            initialfile=f"relatorio_monitoramento_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
        if not filepath:
            return
        try:
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                df_speed = database_manager.fetch_data_as_dataframe('speed_history')
                df_ping = database_manager.fetch_data_as_dataframe('ping_history')
                df_devices = database_manager.fetch_data_as_dataframe('device_log')
                if not df_speed.empty:
                    df_speed.to_excel(writer, sheet_name='Velocidade', index=False)
                    worksheet = writer.sheets['Velocidade']
                    for idx, col in enumerate(df_speed):
                        series = df_speed[col]
                        max_len = max((series.astype(str).map(len).max(), len(str(series.name)))) + 2
                        worksheet.set_column(idx, idx, max_len)
                if not df_ping.empty:
                    df_ping.to_excel(writer, sheet_name='Latencia_Jitter_Perda', index=False)
                    worksheet = writer.sheets['Latencia_Jitter_Perda']
                    for idx, col in enumerate(df_ping):
                        series = df_ping[col]
                        max_len = max((series.astype(str).map(len).max(), len(str(series.name)))) + 2
                        worksheet.set_column(idx, idx, max_len)
                if not df_devices.empty:
                    df_devices.to_excel(writer, sheet_name='Log_de_Dispositivos', index=False)
                    worksheet = writer.sheets['Log_de_Dispositivos']
                    for idx, col in enumerate(df_devices):
                        series = df_devices[col]
                        max_len = max((series.astype(str).map(len).max(), len(str(series.name)))) + 2
                        worksheet.set_column(idx, idx, max_len)
            messagebox.showinfo("Exportar Excel", f"Relatório exportado com sucesso para:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Erro ao Exportar", f"Ocorreu um erro ao salvar o arquivo Excel:\n{e}")

if __name__ == "__main__":
    root = Tk()
    app = App(root)
    root.mainloop()