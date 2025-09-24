import scapy.all as scapy
import socket
import netaddr  

def get_lan_ip():
    """Descobre o endereço IP local para definir o alvo da varredura."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def get_vendor_local(mac_address):
    """
    Busca o fabricante de um endereço MAC usando o banco de dados local do netaddr.
    """
    try:
        
        manuf = netaddr.EUI(mac_address).oui.registration().org
        return manuf
    except netaddr.NotRegisteredError:
        
        return "Desconhecido"
    except Exception:
        return "Desconhecido"

def scan_network():
    """
    Realiza uma varredura ARP na sub-rede local para descobrir dispositivos.
    """
    local_ip = get_lan_ip()
    target_ip = local_ip.rsplit('.', 1)[0] + '.0/24'
    
    print(f"🔎 Realizando varredura na rede: {target_ip}")
    
    arp_request = scapy.ARP(pdst=target_ip)
    broadcast = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
    arp_request_broadcast = broadcast / arp_request
    
    answered_list = scapy.srp(arp_request_broadcast, timeout=2, verbose=False)[0]
    
    clients_list = []

    for element in answered_list:
        ip_addr = element[1].psrc
        mac_addr = element[1].hwsrc
        
        
        vendor = get_vendor_local(mac_addr)

        clients_list.append({"ip": ip_addr, "mac": mac_addr, "vendor": vendor})
        
    print(f"✅ Varredura concluída. {len(clients_list)} dispositivos encontrados.")
    return clients_list

if __name__ == '__main__':
    devices = scan_network()
    print("\n--- Dispositivos Encontrados ---")
    for device in devices:
        print(f"IP: {device['ip']}\tMAC: {device['mac']}\tFabricante: {device['vendor']}")