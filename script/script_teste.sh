#!/bin/bash
# script_teste.sh
# Roda do WSL — não dentro do container
# Uso: bash script_teste.sh

REPETICOES=15
DIR="/app"
LOG_DIR="$DIR/logs"
PCAP_DIR="$DIR/capturas"

# Cria pastas locais e dentro dos containers
mkdir -p capturas logs
docker exec servidor_redes mkdir -p "$LOG_DIR" "$PCAP_DIR"
docker exec cliente_redes mkdir -p "$LOG_DIR"
docker exec servidor_redes rm -f "$LOG_DIR"/*.csv
docker exec cliente_redes rm -f "$LOG_DIR"/*.csv

# Limpa logs anteriores
rm -f logs/*.csv logs/*.log capturas/*.pcap

echo "=================================================="
echo "  Testes Automatizados - Redes de Computadores II"
echo "=================================================="

# ── Verifica se os containers estão rodando ───────────
for container in servidor_redes cliente_redes; do
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "[-] Container '$container' nao esta rodando. Execute: docker-compose up -d"
        exit 1
    fi
done
echo "[OK] Containers verificados."

# ── Função: aguarda servidor TCP subir ────────────────
aguardar_servidor() {
    local porta=$1
    for i in $(seq 1 10); do
        if docker exec cliente_redes bash -c "(echo > /dev/tcp/servidor_redes/$porta) 2>/dev/null"; then
            return 0
        fi
        sleep 0.3
    done
    echo "[-] Servidor nao subiu na porta $porta"
    return 1
}

# ── Função: roda N testes de um protocolo ─────────────
rodar_protocolo() {
    local protocolo=$1    # "tcp" ou "rudp"
    local cenario=$2      # "A", "B" ou "C"
    local repeticoes=$3

    if [ "$protocolo" == "tcp" ]; then
        local porta=5000
        local servidor="servidor_tcp.py"
        local cliente="cliente_tcp.py"
        local filtro="tcp port 5000"
    else
        local porta=5001
        local servidor="servidor_rudp.py"
        local cliente="cliente_rudp.py"
        local filtro="udp port 5001"
    fi

    local pcap="$PCAP_DIR/${protocolo}_cenario${cenario}.pcap"

    echo ""
    echo "--------------------------------------------------"
    echo "  Protocolo: ${protocolo^^} | Cenario: $cenario | Repeticoes: $repeticoes"
    echo "--------------------------------------------------"

    # Garante que não há processo anterior rodando
    docker exec servidor_redes pkill -f "server/$servidor" 2>/dev/null
    sleep 0.3

    # Inicia o servidor no container servidor
    docker exec -d servidor_redes python3 "$DIR/server/$servidor"
    echo "[OK] Servidor iniciado."

    if [ "$protocolo" == "tcp" ]; then
        aguardar_servidor $porta
    else
        sleep 1
    fi

    # Inicia tcpdump no container servidor
    docker exec -d servidor_redes tcpdump -i any "$filtro" -w "$pcap"
    sleep 0.5
    echo "[OK] tcpdump iniciado."

    echo "[*] Iniciando $repeticoes transferencias..."

    for i in $(seq 1 $repeticoes); do
        echo -n "    Transferencia $i/$repeticoes... "
        docker exec cliente_redes python3 "$DIR/client/$cliente" "$cenario" > /dev/null 2>&1
        echo "OK"
        sleep 0.2
    done

    # Para tcpdump e servidor
    docker exec servidor_redes pkill -f tcpdump 2>/dev/null
    docker exec servidor_redes pkill -f "server/$servidor" 2>/dev/null
    sleep 0.5

    echo "[OK] Captura salva em: $pcap"
}

# ══════════════════════════════════════════════
# CENÁRIO A — 10ms de atraso, sem perda
# ══════════════════════════════════════════════
echo ""
echo "========== CENARIO A (10ms, sem perda) =========="
echo "[*] Aplicando cenario A..."
docker exec servidor_redes bash /app/script/simulador_redes.sh A
sleep 1

rodar_protocolo "tcp"  "A" $REPETICOES
rodar_protocolo "rudp" "A" $REPETICOES

# ══════════════════════════════════════════════
# CENÁRIO B — 50ms de atraso, 5% de perda
# ══════════════════════════════════════════════
echo ""
echo "========== CENARIO B (50ms, 5% perda) =========="
echo "[*] Aplicando cenario B..."
docker exec servidor_redes bash /app/script/simulador_redes.sh B
sleep 1

rodar_protocolo "tcp"  "B" $REPETICOES
rodar_protocolo "rudp" "B" $REPETICOES

# ══════════════════════════════════════════════
# CENÁRIO C — 100ms de atraso, 10% de perda
# ══════════════════════════════════════════════
echo ""
echo "========== CENARIO C (100ms, 10% perda) =========="
echo "[*] Aplicando cenario C..."
docker exec servidor_redes bash /app/script/simulador_redes.sh C
sleep 1

rodar_protocolo "tcp"  "C" $REPETICOES
rodar_protocolo "rudp" "C" $REPETICOES

# ══════════════════════════════════════════════
# Remove limitações de rede ao final
# ══════════════════════════════════════════════
echo ""
echo "[*] Removendo limitacoes de rede..."
docker exec servidor_redes bash /app/script/simulador_redes.sh limpar 2>/dev/null

# ── Copia logs dos containers para pasta local ────────
echo "[*] Copiando logs..."
docker cp servidor_redes:/app/logs/log_tcp_servidor.csv  logs/ 2>/dev/null && echo "[OK] log_tcp_servidor.csv"
docker cp servidor_redes:/app/logs/log_rudp_servidor.csv logs/ 2>/dev/null && echo "[OK] log_rudp_servidor.csv"
docker cp cliente_redes:/app/logs/log_tcp_cliente.csv    logs/ 2>/dev/null && echo "[OK] log_tcp_cliente.csv"
docker cp cliente_redes:/app/logs/log_rudp_cliente.csv   logs/ 2>/dev/null && echo "[OK] log_rudp_cliente.csv"

echo ""
echo ""
echo "  Testes concluidos!"
echo ""
echo ""
echo "Logs gerados:"
ls -lh logs/*.csv 2>/dev/null
echo ""
echo "Capturas geradas:"
ls -lh capturas/*.pcap 2>/dev/null
echo ""
echo "Proximo passo: docker exec cliente_redes python3 /app/analise.py"