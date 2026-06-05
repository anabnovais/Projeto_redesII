
INTERFACE="eth0"

tc qdisc del dev $INTERFACE root 2>/dev/null

case "$1" in
    "A")
        echo "Aplicando Cenário A"
        tc qdisc add dev $INTERFACE root netem delay 10ms
        ;;
    "B")
        echo "Aplicando Cenário B"
        tc qdisc add dev $INTERFACE root netem delay 50ms loss 5%
        ;;
    "C")
        echo "Aplicando Cenário C"
        tc qdisc add dev $INTERFACE root netem delay 100ms loss 10%
        ;;
    "limpar")
        echo "Limpando regras"
        tc qdisc del dev $INTERFACE root
        ;;
    *)
        echo "Uso: ./simular_redes.sh [A|B|C|limpar]"
        ;;
esac