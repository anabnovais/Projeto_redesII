import socket
import hashlib
import time
import os
import json
import csv
import sys

MATRICULA = "20249010841"
NOME      = "Ana Beatriz Novais de Castro"

HOST        = "servidor_redes"
PORT        = 5000
BUFFER_SIZE = 4096
LOG_FILE    = "/app/logs/log_tcp_cliente.csv"


def gerarAuth():
    return hashlib.sha256((MATRICULA + NOME).encode()).hexdigest()


def enviar_arquivo(caminho_arquivo, cenario="A"):
    if not os.path.exists(caminho_arquivo):
        print(f"[-] Arquivo nao encontrado: {caminho_arquivo}")
        return

    nome_arquivo = os.path.basename(caminho_arquivo)
    tamanho      = os.path.getsize(caminho_arquivo)
    auth         = gerarAuth()

    print(f"\n[*] Enviando: {nome_arquivo} ({tamanho} bytes)")
    print(f"[*] Servidor : {HOST}:{PORT}")
    print(f"[*] Cenario  : {cenario}")
    print(f"[*] Auth     : {auth}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        meta = json.dumps({
            "auth":     auth,
            "filename": nome_arquivo,
            "filesize": tamanho,
            "cenario":  cenario,
        })
        s.sendall(meta.encode() + b"\n")

        tempo_inicio = time.perf_counter()
        bytes_enviados = 0

        with open(caminho_arquivo, "rb") as f:
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                s.sendall(chunk)
                bytes_enviados += len(chunk)

        tempo_fim  = time.perf_counter()
        duracao    = tempo_fim - tempo_inicio
        throughput = (bytes_enviados / duracao) / 1024 if duracao > 0 else 0

        print(f"[OK] Envio concluido.")
        print(f"    Enviados  : {bytes_enviados} bytes")
        print(f"    Duracao   : {duracao:.4f} s")
        print(f"    Throughput: {throughput:.2f} KB/s")

        resposta_raw = b""
        while b"\n" not in resposta_raw:
            parte = s.recv(BUFFER_SIZE)
            if not parte:
                break
            resposta_raw += parte

        resposta = json.loads(resposta_raw.split(b"\n")[0].decode())
        print(f"[*] Resposta do servidor: {resposta}")

        if resposta.get("status") == "ok":
            print("[OK] Servidor confirmou o recebimento!")
        else:
            print(f"[-] Erro: {resposta.get('motivo')}")

        registro = {
            "protocolo":       "TCP",
            "cenario":         cenario,
            "arquivo":         nome_arquivo,
            "bytes_enviados":  bytes_enviados,
            "duracao_s":       round(duracao, 6),
            "throughput_kBps": round(throughput, 4),
            "timestamp":       time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        salvar_log(registro)


def salvar_log(registro):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    escrever_header = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["protocolo","cenario","arquivo","bytes_enviados","duracao_s","throughput_kBps","timestamp"])
        if escrever_header:
            writer.writeheader()
        writer.writerow(registro)


def main():
    print("=" * 50)
    print("  Cliente TCP - Redes de Computadores II")
    print("=" * 50)

    cenario = sys.argv[1] if len(sys.argv) > 1 else "A"

    arquivo_teste = "./arquivo_teste.bin"
    if not os.path.exists(arquivo_teste):
        print("[*] Criando arquivo de teste de 1MB...")
        with open(arquivo_teste, "wb") as f:
            f.write(os.urandom(1024 * 1024))

    enviar_arquivo(arquivo_teste, cenario)


if __name__ == "__main__":
    main()
