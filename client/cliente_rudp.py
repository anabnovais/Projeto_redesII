import socket
import hashlib
import time
import os
import json
import struct
import sys

MATRICULA = "20249010841"
NOME      = "Ana Beatriz Novais de Castro"

HOST           = "servidor_redes"
PORT           = 5001
BUFFER_SIZE    = 4096
MAX_TENTATIVAS = 10
LOG_FILE       = "/app/logs/log_rudp_cliente.csv"

HEADER_SIZE  = 21
PAYLOAD_SIZE = 1400
BUFFER_SIZE = HEADER_SIZE + PAYLOAD_SIZE
ACK  = b"ACK"
NACK = b"NACK"

# Timeout adequado para cada cenário
TIMEOUTS = {
    "A": 0.1,   # 10ms de atraso → 100ms de timeout
    "B": 0.3,   # 50ms de atraso + 5% perda → 300ms
    "C": 0.6,   # 100ms de atraso + 10% perda → 600ms
}


def gerarAuth():
    return hashlib.sha256((MATRICULA + NOME).encode()).hexdigest()


def empacotarPacote(seq, flag, payload):
    checksum_data = struct.pack("!I", seq) + struct.pack("!B", flag) + payload
    checksum = hashlib.md5(checksum_data).digest()

    cabecalho = (
        struct.pack("!I", seq)
        + struct.pack("!B", flag)
        + checksum
    )

    return cabecalho + payload


def enviarRetransmissao(sock, pacote, endereco, descricao="pacote"):
    retransmissoes = 0

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        sock.sendto(pacote, endereco)

        try:
            resposta, _ = sock.recvfrom(BUFFER_SIZE)

            if resposta[:3] == ACK:
                return True, resposta[3:], retransmissoes

            else:
                retransmissoes += 1
                print(f"[!] NACK para {descricao}, tentativa {tentativa}.")

        except socket.timeout:
            retransmissoes += 1
            print(f"[!] Timeout para {descricao}, tentativa {tentativa}.")

    print(f"[-] Falha apos {MAX_TENTATIVAS} tentativas para {descricao}.")
    return False, b"", retransmissoes


def enviar_arquivo(caminho_arquivo, cenario= "A"):
    if not os.path.exists(caminho_arquivo):
        print(f"[-] Arquivo '{caminho_arquivo}' nao encontrado.")
        return

    nome_arquivo    = os.path.basename(caminho_arquivo)
    tamanho_arquivo = os.path.getsize(caminho_arquivo)
    auth            = gerarAuth()
    endereco        = (HOST, PORT)
    timeout         = TIMEOUTS.get(cenario, 0.5)

    print(f"\n[*] Enviando via R-UDP: {nome_arquivo} ({tamanho_arquivo} bytes)")
    print(f"[*] Servidor : {HOST}:{PORT}")
    print(f"[*] Cenario  : {cenario} | Timeout: {timeout}s")
    print(f"[*] Auth     : {auth}")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)

        # INICIO
        meta = json.dumps({
            "auth":     auth,
            "filename": nome_arquivo,
            "filesize": tamanho_arquivo,
            "cenario": cenario
        }).encode()


        pacote_inicio = empacotarPacote(0, 1, meta)
        sucesso, _ , retransmissoes = enviarRetransmissao(sock, pacote_inicio, endereco, "pacote de inicio")
        if not sucesso:
            print("[-] Nao foi possivel iniciar a transferencia.")
            return
        print("[OK] Servidor aceitou a transferencia.")

        # DADOS
        seq            = 0
        bytes_enviados = 0
        retransmissoes = 0
        tempo_inicio   = time.perf_counter()

        with open(caminho_arquivo, "rb") as f:
            while True:
                bloco = f.read(PAYLOAD_SIZE)
                if not bloco:
                    break
                pacote  = empacotarPacote(seq, 0, bloco)
                sucesso, _ , retransmissoes_local = enviarRetransmissao(sock, pacote, endereco, f"bloco {seq}")
                retransmissoes += retransmissoes_local
                if not sucesso:
                    print(f"[-] Bloco {seq} falhou. Abortando.")
                    return
                bytes_enviados += len(bloco)
                seq += 1
                if seq % 100 == 0:
                    print(f"    Progresso: {bytes_enviados}/{tamanho_arquivo} bytes ({100*bytes_enviados//tamanho_arquivo}%)")

        tempo_fim  = time.perf_counter()
        duracao    = tempo_fim - tempo_inicio
        throughput = (bytes_enviados / duracao) / 1024 if duracao > 0 else 0

        print(f"\n[OK] Envio concluido.")
        print(f"    Blocos enviados : {seq}")
        print(f"    Bytes enviados  : {bytes_enviados}")
        print(f"    Duracao         : {duracao:.4f} s")
        print(f"    Throughput      : {throughput:.2f} KB/s")

        # FIM
        pacote_fim = empacotarPacote(seq, 2, b"fim")
        ok, resposta_extra , retransmissoes_fim = enviarRetransmissao(sock, pacote_fim, endereco, "pacote de fim")
        retransmissoes += retransmissoes_fim

        if ok and resposta_extra:
            try:
                resposta = json.loads(resposta_extra.decode())
                print(f"[*] Confirmacao do servidor: {resposta}")
            except Exception:
                print("[OK] Fim confirmado.")
        elif ok:
            print("[OK] Fim confirmado.")

        # LOG
        registro = {
            "protocolo":       "R-UDP",
            "cenario":         cenario,
            "arquivo":         nome_arquivo,
            "bytes_enviados":  bytes_enviados,
            "blocos":          seq,
            "retransmissoes":  retransmissoes,
            "duracao_s":       round(duracao, 6),
            "throughput_kBps": round(throughput, 4),
            "timestamp":       time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        salvar_log(registro)


def salvar_log(registro):
    import csv
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    escrever_header = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["protocolo","cenario","arquivo","bytes_enviados","blocos","retransmissoes","duracao_s","throughput_kBps","timestamp"])
        if escrever_header:
            writer.writeheader()
        writer.writerow(registro)


def main():
    print("=" * 50)
    print("  Cliente R-UDP - Redes de Computadores II")
    print("=" * 50)

    # Recebe cenário como argumento: python3 cliente_rudp.py A
    cenario = sys.argv[1] if len(sys.argv) > 1 else "A"

    arquivo_teste = "./arquivo_teste.bin"
    if not os.path.exists(arquivo_teste):
        print("[*] Criando arquivo de teste de 1MB...")
        with open(arquivo_teste, "wb") as f:
            f.write(os.urandom(1024 * 1024))

    enviar_arquivo(arquivo_teste, cenario)


if __name__ == "__main__":
    main()
