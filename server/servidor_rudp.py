import socket
import hashlib
import time
import os
import json
import struct

MATRICULA = "20249010841"
NOME      = "Ana Beatriz Novais de Castro"

HOST        = "0.0.0.0"
PORT        = 5001
SAVE_DIR    = "/app/arquivos_recebidos"
LOG_FILE    = "/app/logs/log_rudp_servidor.csv"

HEADER_SIZE = 21
PAYLOAD_SIZE = 1400
BUFFER_SIZE = HEADER_SIZE + PAYLOAD_SIZE







def gerarAuth():
    return hashlib.sha256((MATRICULA + NOME).encode()).hexdigest()


def desempacotarPacote(dados):
    seq      = struct.unpack("!I", dados[0:4])[0]
    flag     = struct.unpack("!B", dados[4:5])[0]
    checksum = dados[5:21]
    payload  = dados[21:]
    return seq, flag, checksum, payload


def validarChecksum(seq, flag, payload, checksum):
    checksum_data = (
        struct.pack("!I", seq)
        + struct.pack("!B", flag)
        + payload
    )

    checksum_calculado = hashlib.md5(checksum_data).digest()

    return checksum_calculado == checksum


def receber_arquivo(sock):
    blocos           = {}
    nome_arquivo     = None
    tamanho_esperado = 0
    seq_esperado     = 0
    tempo_inicio     = None

    print("\n[*] Aguardando pacotes R-UDP...\n")

    while True:
        dados, endereco = sock.recvfrom(BUFFER_SIZE)

        if len(dados) < HEADER_SIZE:
            print(f"[-] Pacote muito pequeno ({len(dados)} bytes), ignorando.")
            continue

        seq, flag, checksum, payload = desempacotarPacote(dados)

        if flag == 1:
            try:
                meta = json.loads(payload.decode())
            except Exception:
                print("[-] Metadados invalidos.")
                sock.sendto(b"NACK", endereco)
                continue

            auth_recebido = meta.get("auth", "")
            if auth_recebido != gerarAuth():
                print("[-] AUTENTICACAO FALHOU.")
                sock.sendto(b"NACK", endereco)
                return

            nome_arquivo     = os.path.basename(meta.get("filename", "arquivo_rudp"))
            tamanho_esperado = int(meta.get("filesize", 0))
            seq_esperado     = 0
            blocos           = {}
            tempo_inicio     = time.perf_counter()

            print(f"[+] Transferencia iniciada de {endereco}")
            print(f"    Arquivo  : {nome_arquivo}")
            print(f"    Tamanho  : {tamanho_esperado} bytes")
            print(f"[OK] Autenticacao OK.")
            sock.sendto(b"ACK", endereco)
            continue

        if flag == 2:
            if nome_arquivo is None:
                sock.sendto(b"NACK", endereco)
                continue

            tempo_fim  = time.perf_counter()
            duracao    = tempo_fim - tempo_inicio if tempo_inicio else 0

            dados_completos = b""
            for i in range(len(blocos)):
                if i not in blocos:
                    print(f"[-] Bloco {i} faltando!")
                    sock.sendto(b"NACK", endereco)
                    return
                dados_completos += blocos[i]

            bytes_recebidos = len(dados_completos)
            throughput = (bytes_recebidos / duracao) / 1024 if duracao > 0 else 0

            os.makedirs(SAVE_DIR, exist_ok=True)
            caminho_saida = os.path.join(SAVE_DIR, nome_arquivo)
            with open(caminho_saida, "wb") as f:
                f.write(dados_completos)

            print(f"[OK] Arquivo salvo em: {caminho_saida}")
            print(f"    Duracao   : {duracao:.4f} s")
            print(f"    Throughput: {throughput:.2f} KB/s")
            print(f"    Recebidos : {bytes_recebidos}/{tamanho_esperado} bytes")
            print(f"    Blocos    : {len(blocos)}")

            registro = {
                "protocolo":       "R-UDP",
                "arquivo":         nome_arquivo,
                "bytes":           bytes_recebidos,
                "duracao_s":       round(duracao, 6),
                "throughput_kBps": round(throughput, 4),
                "cenario":         meta.get("cenario", "A"),
                "blocos":          len(blocos),
                "timestamp":       time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            salvar_log(registro)

            resposta = json.dumps({
                "status":          "ok",
                "bytes":           bytes_recebidos,
                "duracao_s":       round(duracao, 6),
                "throughput_kBps": round(throughput, 4),
            })
            sock.sendto(b"ACK" + resposta.encode(), endereco)
            return

        if nome_arquivo is None:
            sock.sendto(b"NACK", endereco)
            continue

        if not validarChecksum(seq, flag, payload, checksum):
            print(f"[!] Checksum invalido no bloco {seq}, enviando NACK.")
            sock.sendto(b"NACK", endereco)
            continue

        if seq in blocos:
            sock.sendto(b"ACK", endereco)
            continue

        if seq != seq_esperado:
            print(f"[!] Seq esperado {seq_esperado}, recebido {seq}, enviando NACK.")
            sock.sendto(b"NACK", endereco)
            continue

        blocos[seq] = payload
        seq_esperado += 1
        sock.sendto(b"ACK", endereco)


def salvar_log(registro):
    import csv
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    escrever_header = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["protocolo","cenario","arquivo","bytes","duracao_s","throughput_kBps","blocos","timestamp"])
        if escrever_header:
            writer.writeheader()
        writer.writerow(registro)

def main():
    print("=" * 50)
    print("  Servidor R-UDP - Redes de Computadores II")
    print("=" * 50)
    print(f"  Escutando em {HOST}:{PORT}")
    print(f"  Auth esperado: {gerarAuth()}")
    print("=" * 50)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((HOST, PORT))
        while True:
            try:
                receber_arquivo(sock)
            except Exception as e:
                print(f"[!] Erro: {e}")


if __name__ == "__main__":
    main()
