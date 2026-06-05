import socket
import hashlib
import time
import os
import json
import csv

MATRICULA = "20249010841"
NOME      = "Ana Beatriz Novais de Castro"

HOST        = "0.0.0.0"
PORT        = 5000
BUFFER_SIZE = 4096
SAVE_DIR    = "/app/arquivos_recebidos"
LOG_FILE    = "/app/logs/log_tcp_servidor.csv"


def gerarAuth():
    return hashlib.sha256((MATRICULA + NOME).encode()).hexdigest()


def receber_arquivo(conn, endereco):
    print(f"\n[+] Conexao de {endereco}")

    raw_meta = b""
    while b"\n" not in raw_meta:
        chunk = conn.recv(BUFFER_SIZE)
        if not chunk:
            print("[-] Conexao encerrada antes dos metadados.")
            return
        raw_meta += chunk

    linha_meta, restante = raw_meta.split(b"\n", 1)
    meta = json.loads(linha_meta.decode())

    auth_recebido    = meta.get("auth", "")
    nome_arquivo     = os.path.basename(meta.get("filename", "arquivo_recebido"))
    tamanho_esperado = int(meta.get("filesize", 0))

    print(f"    Arquivo   : {nome_arquivo}")
    print(f"    Tamanho   : {tamanho_esperado} bytes")
    print(f"    Auth rcvd : {auth_recebido}")

    if auth_recebido != gerarAuth():
        print("[-] AUTENTICACAO FALHOU.")
        conn.sendall(json.dumps({"status": "erro", "motivo": "auth_invalido"}).encode() + b"\n")
        return
    print("[OK] Autenticacao OK.")

    os.makedirs(SAVE_DIR, exist_ok=True)
    caminho_saida = os.path.join(SAVE_DIR, nome_arquivo)

    bytes_recebidos = len(restante)
    dados_arquivo   = restante
    tempo_inicio    = time.perf_counter()

    while bytes_recebidos < tamanho_esperado:
        chunk = conn.recv(BUFFER_SIZE)
        if not chunk:
            break
        dados_arquivo   += chunk
        bytes_recebidos += len(chunk)

    tempo_fim  = time.perf_counter()
    duracao    = tempo_fim - tempo_inicio
    throughput = (bytes_recebidos / duracao) / 1024 if duracao > 0 else 0

    with open(caminho_saida, "wb") as f:
        f.write(dados_arquivo[:tamanho_esperado])

    print(f"[OK] Arquivo salvo em: {caminho_saida}")
    print(f"    Duracao   : {duracao:.4f} s")
    print(f"    Throughput: {throughput:.2f} KB/s")
    print(f"    Recebidos : {bytes_recebidos}/{tamanho_esperado} bytes")

    registro = {
        "protocolo":       "TCP",
        "arquivo":         nome_arquivo,
        "bytes":           bytes_recebidos,
        "duracao_s":       round(duracao, 6),
        "throughput_kBps": round(throughput, 4),
        "cenario":         meta.get("cenario", "A"),
        "timestamp":       time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    salvar_log(registro)

    resposta = json.dumps({
        "status":          "ok",
        "bytes":           bytes_recebidos,
        "duracao_s":       round(duracao, 6),
        "throughput_kBps": round(throughput, 4),
    })
    conn.sendall(resposta.encode() + b"\n")


def salvar_log(registro):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    escrever_header = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["protocolo","cenario","arquivo","bytes","duracao_s","throughput_kBps","timestamp"])
        if escrever_header:
            writer.writeheader()
        writer.writerow(registro)


def main():
    print("=" * 50)
    print("  Servidor TCP - Redes de Computadores II")
    print("=" * 50)
    print(f"  Escutando em {HOST}:{PORT}")
    print(f"  Auth esperado: {gerarAuth()}")
    print("=" * 50)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(5)
        print("[*] Aguardando conexoes...\n")
        while True:
            conn, endereco = srv.accept()
            with conn:
                try:
                    receber_arquivo(conn, endereco)
                except Exception as e:
                    print(f"[-] Erro: {e}")


if __name__ == "__main__":
    main()
