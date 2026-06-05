# Projeto_redesII

# Análise de Desempenho e Confiabilidade em Camadas de Transporte (TCP vs. R-UDP)

## Descrição

Este projeto foi desenvolvido para a disciplina de **Redes de Computadores II** e tem como objetivo comparar o desempenho do protocolo **TCP** com uma implementação própria de **Reliable UDP (R-UDP)**.

O estudo foi realizado em um ambiente controlado utilizando contêineres Docker e simulação de condições de rede através do módulo `tc netem`, permitindo avaliar o comportamento dos protocolos sob diferentes cenários de latência e perda de pacotes.

Além da implementação dos protocolos, foram desenvolvidos scripts de automação, coleta de logs, análise estatística e validação cruzada utilizando capturas do Wireshark/TCPDump.

---

## Estrutura do Projeto

```
TrabalhoI_RedesII/
│
├── client/
│   ├── cliente_tcp.py
│   └── cliente_rudp.py
│
├── server/
│   ├── servidor_tcp.py
│   └── servidor_rudp.py
│
├── script/
│   ├── simulador_redes.sh
│   └── script_teste.sh
│
├── logs/
│   ├── *.csv
│
├── analysis/
│   ├── analise.py
│   └── validacaoCruzada.py
│
├── graficos/
│   ├── *.png
│
├── wireshark/
│   ├── arquivos CSV exportados
│
├── capturas/
│   ├── arquivos .pcap
│
├── docker-compose.yml
├── Dockerfile
└── arquivo_teste.bin
```



