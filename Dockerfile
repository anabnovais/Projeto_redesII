# Usa o Ubuntu como base
FROM ubuntu:22.04

# Evita prompts interativos durante a instalação
ENV DEBIAN_FRONTEND=noninteractive

# Instala as ferramentas necessárias:
# - python3 e pip: para rodar seu código e gerar gráficos
# - iproute2: contém o comando 'tc' para simular atraso/perda
# - tcpdump: para capturar o tráfego (.pcap)
# - iputils-ping e net-tools: para testes básicos de conectividade
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    iproute2 \
    tcpdump \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Instala bibliotecas Python para análise de dados
RUN pip3 install pandas matplotlib

# Define o diretório de trabalho
WORKDIR /app

# Comando padrão (mantém o container vivo)
CMD ["tail", "-f", "/dev/null"]
