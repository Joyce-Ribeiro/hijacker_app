import subprocess  # Módulo para executar comandos do sistema, usado para gerar certificados e aplicar regras iptables
import sys  # Módulo para interagir com o sistema, como sair do programa em caso de erro
import os  # Módulo para operações no sistema de arquivos, como verificar existência de arquivos
import threading  # Módulo para criar threads, permitindo que servidores HTTP e HTTPS rodem em paralelo
import signal  # Módulo para lidar com sinais do sistema, como Ctrl+C para shutdown gracioso
from http.server import BaseHTTPRequestHandler, HTTPServer  # Classes para criar servidores HTTP simples
import time  # Módulo para pausas no loop principal
import ssl  # Módulo para suporte a SSL/TLS, necessário para o servidor HTTPS

# Flags e variáveis globais
# server_running: Flag para controlar o loop dos servidores (True enquanto rodando)
server_running = True
# httpd_http: Instância do servidor HTTP
httpd_http = None
# httpd_https: Instância do servidor HTTPS
httpd_https = None

# Classe manipuladora de requisições HTTP/HTTPS
# Herda de BaseHTTPRequestHandler para tratar GET, HEAD e POST com redirecionamento
class RedirectHandler(BaseHTTPRequestHandler):
    # Método para tratar requisições GET: Envia resposta 302 com Location para o repositório GitHub
    def do_GET(self):
        self.send_response(302)  # Código de status 302: Found (redirecionamento temporário)
        self.send_header('Location', 'https://github.com/Joyce-Ribeiro/SantaClaraPapelaria')  # Cabeçalho com URL de redirecionamento
        self.end_headers()  # Finaliza os cabeçalhos da resposta

    # Método para HEAD: Chama do_GET para reutilizar a lógica de redirecionamento
    def do_HEAD(self):
        self.do_GET()

    # Método para POST: Chama do_GET para redirecionar independentemente do método
    def do_POST(self):
        self.do_GET()

# Função para rodar o servidor HTTP em uma thread
def run_http_server():
    global httpd_http  # Acesso à variável global do servidor HTTP
    server_address = ('127.0.0.1', 8080)  # Endereço local (localhost) na porta 8080 para HTTP
    try:
        # Cria o servidor HTTP com o endereço e a classe manipuladora
        httpd_http = HTTPServer(server_address, RedirectHandler)
        print("Servidor de redirecionamento HTTP rodando na porta 8080...")  # Mensagem de inicialização
        # Loop para tratar requisições enquanto o servidor estiver rodando
        while server_running:
            httpd_http.handle_request()  # Trata uma requisição por vez para permitir shutdown gracioso
        # Fecha o servidor ao sair do loop
        httpd_http.server_close()
        print("Servidor HTTP encerrado.")  # Mensagem de encerramento
    except Exception as e:
        # Captura e imprime erros ao iniciar o servidor HTTP, saindo do programa
        print(f"Erro ao iniciar servidor HTTP: {e}")
        sys.exit(1)  # Sai com código de erro 1

# Função para rodar o servidor HTTPS em uma thread
def run_https_server(certfile, keyfile):
    global httpd_https  # Acesso à variável global do servidor HTTPS
    server_address = ('127.0.0.1', 8443)  # Endereço local (localhost) na porta 8443 para HTTPS
    try:
        # Cria o servidor HTTPS com o endereço e a classe manipuladora
        httpd_https = HTTPServer(server_address, RedirectHandler)
        # Cria contexto SSL para encriptação
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)  # Contexto para servidor TLS
        # Carrega certificado e chave privada
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        # Envolve o socket do servidor com SSL
        httpd_https.socket = context.wrap_socket(httpd_https.socket, server_side=True)
        print("Servidor de redirecionamento HTTPS rodando na porta 8443...")  # Mensagem de inicialização
        # Loop para tratar requisições enquanto o servidor estiver rodando
        while server_running:
            httpd_https.handle_request()  # Trata uma requisição por vez para permitir shutdown gracioso
        # Fecha o servidor ao sair do loop
        httpd_https.server_close()
        print("Servidor HTTPS encerrado.")  # Mensagem de encerramento
    except Exception as e:
        # Captura e imprime erros ao iniciar o servidor HTTPS, saindo do programa
        print(f"Erro ao iniciar servidor HTTPS: {e}")
        sys.exit(1)  # Sai com código de erro 1

# Função para gerar ou carregar certificado self-signed
def generate_self_signed_cert():
    certfile = "selfsigned.crt"  # Nome do arquivo de certificado
    keyfile = "selfsigned.key"  # Nome do arquivo de chave privada
    # Verifica se os arquivos já existem
    if not (os.path.exists(certfile) and os.path.exists(keyfile)):
        print("Gerando certificado self-signed...")  # Mensagem de geração
        # Comando OpenSSL para gerar certificado e chave
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", keyfile, "-out", certfile,
            "-days", "365", "-nodes", "-subj", "/CN=localhost"
        ]
        try:
            # Executa o comando e captura saída
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("Certificado gerado com sucesso.")  # Mensagem de sucesso
            print(result.stdout)  # Imprime saída do OpenSSL
        except subprocess.CalledProcessError as e:
            # Captura e imprime erros na geração do certificado
            print(f"Erro ao gerar certificado: {e}")
            print(f"Saída de erro: {e.stderr}")
            sys.exit(1)  # Sai com código de erro 1
    return certfile, keyfile  # Retorna caminhos dos arquivos

# Função para aplicar regras de iptables para redirecionamento
def apply_iptables_rules():
    # Lista de comandos iptables: 
    # Primeiro, exclusões para IPs do GitHub (para evitar loop infinito no redirecionamento)
    # Ranges obtidos da API do GitHub[](https://api.github.com/meta)
    # Em seguida, regras de redirecionamento para portas 80 (HTTP) e 443 (HTTPS)
    commands = [
        # Exclusões IPv4 para GitHub (evita hijacking do tráfego para o GitHub após redirecionamento)
        "iptables -t nat -A OUTPUT -p tcp -d 192.30.252.0/22 --dport 443 -j RETURN",
        "iptables -t nat -A OUTPUT -p tcp -d 185.199.108.0/22 --dport 443 -j RETURN",
        "iptables -t nat -A OUTPUT -p tcp -d 140.82.112.0/20 --dport 443 -j RETURN",
        "iptables -t nat -A OUTPUT -p tcp -d 143.55.64.0/20 --dport 443 -j RETURN",
        # Regras de redirecionamento gerais
        "iptables -t nat -A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 8080",
        "iptables -t nat -A OUTPUT -p tcp --dport 443 -j REDIRECT --to-port 8443",
    ]
    for cmd in commands:
        try:
            # Executa o comando com sudo e captura saída
            result = subprocess.run(["sudo", "sh", "-c", cmd], check=True, capture_output=True, text=True)
            print(f"Regra aplicada: {cmd}")  # Mensagem de sucesso para cada regra
        except subprocess.CalledProcessError as e:
            # Captura e imprime erros ao aplicar regras
            print(f"Erro ao aplicar regra: {cmd}\nErro: {e}\nSaída: {e.stderr}")
            sys.exit(1)  # Sai com código de erro 1
    # Mensagem final de aplicação das regras
    print("Regras de hijacking aplicadas! Todo tráfego HTTP/HTTPS será redirecionado para os servidores locais (exceto GitHub para evitar loop).")

# Função para limpar regras de iptables ao encerrar
def cleanup_iptables():
    try:
        # Executa comando para flushar a tabela nat (remove todas as regras adicionadas)
        subprocess.run(["sudo", "iptables", "-t", "nat", "-F"], check=True)
        print("Regras de iptables removidas.")  # Mensagem de sucesso
    except subprocess.CalledProcessError as e:
        # Captura e imprime erros na limpeza
        print(f"Erro ao limpar regras de iptables: {e}")

# Manipulador de sinais para shutdown gracioso (ex.: Ctrl+C)
def signal_handler(sig, frame):
    global server_running  # Acesso à flag global
    print("\nEncerrando aplicação...")  # Mensagem de encerramento
    server_running = False  # Para o loop dos servidores
    if httpd_http:
        httpd_http.server_close()  # Fecha servidor HTTP se existir
    if httpd_https:
        httpd_https.server_close()  # Fecha servidor HTTPS se existir
    cleanup_iptables()  # Limpa regras iptables
    sys.exit(0)  # Sai do programa

# Bloco principal do script
if __name__ == "__main__":
    # Verifica se rodando como root (necessário para iptables e portas <1024, mas usamos >1024)
    if os.geteuid() != 0:
        print("Execute como root: sudo python3 hijacker_app.py")
        sys.exit(1)  # Sai se não for root

    # Gera ou carrega certificado
    certfile, keyfile = generate_self_signed_cert()

    # Configura manipuladores de sinais para SIGINT (Ctrl+C) e SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Inicia thread do servidor HTTP
    http_thread = threading.Thread(target=run_http_server, daemon=True)  # Daemon para sair com o main
    http_thread.start()

    # Inicia thread do servidor HTTPS
    https_thread = threading.Thread(target=run_https_server, args=(certfile, keyfile), daemon=True)  # Daemon para sair com o main
    https_thread.start()

    # Aplica regras iptables (agora com exclusões para GitHub)
    apply_iptables_rules()

    # Mantém o thread principal vivo com um loop infinito
    try:
        while True:
            time.sleep(1)  # Pausa de 1 segundo para não consumir CPU
    except KeyboardInterrupt:
        # Captura Ctrl+C e chama o handler
        signal_handler(None, None)