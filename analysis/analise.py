import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import numpy as np
from validacaoCruzada import (
    carregar_log_python,
    carregar_wireshark,
    metricas_wireshark
)

DIR      = "/app"
LOG_DIR  = f"{DIR}/logs"
GRAF_DIR = f"{DIR}/graficos"

os.makedirs(GRAF_DIR, exist_ok=True)

CORES_CENARIO = {"A": "#2196F3", "B": "#FF9800", "C": "#F44336"}
CENARIOS      = ["A", "B", "C"]
DESCRICAO     = {
    "A": "Cenário A\n(10ms, sem perda)",
    "B": "Cenário B\n(50ms, 5% perda)",
    "C": "Cenário C\n(100ms, 10% perda)",
}


def carregarLog():
    arquivos = {
        "TCP_servidor":  "log_tcp_servidor.csv",
        "TCP_cliente":   "log_tcp_cliente.csv",
        "RUDP_servidor": "log_rudp_servidor.csv",
        "RUDP_cliente":  "log_rudp_cliente.csv",
    }
    dfs = {}
    for nome, arquivo in arquivos.items():
        caminho = os.path.join(LOG_DIR, arquivo)
        if os.path.exists(caminho):
            dfs[nome] = pd.read_csv(caminho)
            print(f"[OK] {arquivo}: {len(dfs[nome])} registros")
        else:
            print(f"[!] Nao encontrado: {arquivo}")
    return dfs



def calcularEstatisticas(df, coluna="throughput_kBps"):
    stats = df.groupby("cenario")[coluna].agg(
        minimo="min",
        media="mean",
        maximo="max",
        desvio="std"
    ).round(2)
    return stats



def grafico_overhead_wireshark():

    fig, ax = plt.subplots(figsize=(9, 6))

    cenarios_txt = [
        "A\n(10ms, sem perda)",
        "B\n(50ms, 5% perda)",
        "C\n(100ms, 10% perda)"
    ]

    diff_tcp = []
    diff_rudp = []

    for cenario in CENARIOS:

        # ================= TCP =================

        df_python = carregar_log_python("TCP")
        df_python = df_python[
            df_python["cenario"] == cenario
        ].reset_index(drop=True)

        col_bytes = (
            "bytes"
            if "bytes" in df_python.columns
            else "bytes_enviados"
        )

        df_wire = carregar_wireshark("TCP", cenario)
        df_wire = metricas_wireshark(df_wire, len(df_python))

        media_diff = (
            abs(
                df_python[col_bytes].mean()
                - df_wire["bytes_wireshark"].mean()
            )
            / df_python[col_bytes].mean()
        ) * 100

        diff_tcp.append(media_diff)

        # ================= RUDP =================

        df_python = carregar_log_python("RUDP")
        df_python = df_python[
            df_python["cenario"] == cenario
        ].reset_index(drop=True)

        col_bytes = (
            "bytes"
            if "bytes" in df_python.columns
            else "bytes_enviados"
        )

        df_wire = carregar_wireshark("RUDP", cenario)
        df_wire = metricas_wireshark(df_wire, len(df_python))

        media_diff = (
            abs(
                df_python[col_bytes].mean()
                - df_wire["bytes_wireshark"].mean()
            )
            / df_python[col_bytes].mean()
        ) * 100

        diff_rudp.append(media_diff)

    x = np.arange(len(cenarios_txt))
    largura = 0.30

    ax.bar(
        x - largura / 2,
        diff_tcp,
        largura,
        label="TCP",
        color="#1565C0",
        edgecolor="black"
    )

    ax.bar(
        x + largura / 2,
        diff_rudp,
        largura,
        label="R-UDP",
        color="#F44336",
        edgecolor="black"
    )

    ax.axhline(
        y=5,
        color="gray",
        linestyle="--",
        linewidth=1.5,
        label="Limite 5%"
    )

    ax.set_title(
        "Diferença entre Python e Wireshark por Cenário",
        fontsize=13,
        fontweight="bold"
    )

    ax.set_ylabel("Diferença média (%)")
    ax.set_xlabel("Cenário de Rede")

    ax.set_xticks(x)
    ax.set_xticklabels(cenarios_txt)

    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for i in range(len(cenarios_txt)):
        ax.text(
            x[i] - largura / 2,
            diff_tcp[i] + 0.2,
            f"{diff_tcp[i]:.1f}%",
            ha="center",
            fontsize=8
        )

        ax.text(
            x[i] + largura / 2,
            diff_rudp[i] + 0.2,
            f"{diff_rudp[i]:.1f}%",
            ha="center",
            fontsize=8
        )

    plt.tight_layout()

    caminho = os.path.join(
        GRAF_DIR,
        "overhead_wireshark_cenarios.png"
    )

    plt.savefig(caminho, dpi=150)
    plt.close()

    print(f"[OK] Salvo: {caminho}")


def grafico_barras(df_tcp, df_rudp):
    stats_tcp  = calcularEstatisticas(df_tcp)
    stats_rudp = calcularEstatisticas(df_rudp)
 
    x      = np.arange(len(CENARIOS))
    width  = 0.35
 
    fig, ax = plt.subplots(figsize=(10, 6))
 
    medias_tcp  = [stats_tcp.loc[c, "media"]  if c in stats_tcp.index  else 0 for c in CENARIOS]
    desvios_tcp = [stats_tcp.loc[c, "desvio"] if c in stats_tcp.index  else 0 for c in CENARIOS]
 
    medias_rudp  = [stats_rudp.loc[c, "media"]  if c in stats_rudp.index else 0 for c in CENARIOS]
    desvios_rudp = [stats_rudp.loc[c, "desvio"] if c in stats_rudp.index else 0 for c in CENARIOS]
 
    bars1 = ax.bar(x - width/2, medias_tcp,  width, yerr=desvios_tcp,
                   label="TCP",   color="#64B5F6", capsize=5, edgecolor="black")
    bars2 = ax.bar(x + width/2, medias_rudp, width, yerr=desvios_rudp,
                   label="R-UDP", color="#FFB74D", capsize=5, edgecolor="black")
 
    ax.set_title("Throughput Médio por Cenário — TCP vs R-UDP", fontsize=13, fontweight="bold")
    ax.set_ylabel("Throughput Médio (KB/s)")
    ax.set_xlabel("Cenário de Rede")
    ax.set_xticks(x)
    ax.set_xticklabels([DESCRICAO[c] for c in CENARIOS])
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)
 
    # Valores nas barras
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 500,
                f"{bar.get_height():.0f}", ha="center", va="bottom", fontsize=8)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 500,
                f"{bar.get_height():.0f}", ha="center", va="bottom", fontsize=8)
 
    plt.tight_layout()
    caminho = os.path.join(GRAF_DIR, "barras_throughput.png")
    plt.savefig(caminho, dpi=150)
    plt.close()
    print(f"[OK] Salvo: {caminho}")

def grafico_linha(df_tcp, df_rudp):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Evolução do Throughput por Transferência", fontsize=13, fontweight="bold")
 
    for ax, (df, titulo) in zip(axes, [(df_tcp, "TCP"), (df_rudp, "R-UDP")]):
        for cenario in CENARIOS:
            dados = df[df["cenario"] == cenario]["throughput_kBps"].values
            ax.plot(range(1, len(dados)+1), dados,
                    marker="o", markersize=3,
                    color=CORES_CENARIO[cenario],
                    label=DESCRICAO[cenario].replace("\n", " "))
        ax.set_title(titulo, fontsize=11)
        ax.set_xlabel("Transferência #")
        ax.set_ylabel("Throughput (KB/s)" if titulo == "TCP" else "")
        ax.legend(fontsize=8)
        ax.grid(linestyle="--", alpha=0.4)
 
    plt.tight_layout()
    caminho = os.path.join(GRAF_DIR, "linha_throughput.png")
    plt.savefig(caminho, dpi=150)
    plt.close()
    print(f"[OK] Salvo: {caminho}")

def grafico_boxplot(df_tcp, df_rudp):
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), sharey=False)
    fig.suptitle("Distribuição do Throughput — TCP vs R-UDP", fontsize=14, fontweight="bold")
 
    for i, cenario in enumerate(CENARIOS):
        ax = axes[i]
        dados_tcp  = df_tcp[df_tcp["cenario"] == cenario]["throughput_kBps"].values
        dados_rudp = df_rudp[df_rudp["cenario"] == cenario]["throughput_kBps"].values
 
        bp = ax.boxplot(
            [dados_tcp, dados_rudp],
            tick_labels=["TCP", "R-UDP"],
            patch_artist=True,
            medianprops=dict(color="black", linewidth=2),
        )
        bp["boxes"][0].set_facecolor("#64B5F6")
        bp["boxes"][1].set_facecolor("#FFB74D")
 
        ax.set_title(DESCRICAO[cenario], fontsize=10)
        ax.set_ylabel("Throughput (KB/s)" if i == 0 else "")
        ax.set_xlabel("Protocolo")
        ax.grid(axis="y", linestyle="--", alpha=0.5)
 
    plt.tight_layout()
    caminho = os.path.join(GRAF_DIR, "boxplot_throughput.png")
    plt.savefig(caminho, dpi=150)
    plt.close()
    print(f"[OK] Salvo: {caminho}")
 
def imprimir_tabela(df_tcp, df_rudp):
    print("\n" + "="*60)
    print("  ESTATÍSTICAS — TCP (throughput_kBps)")
    print("="*60)
    print(calcularEstatisticas(df_tcp).to_string())
 
    print("\n" + "="*60)
    print("  ESTATÍSTICAS — R-UDP (throughput_kBps)")
    print("="*60)
    print(calcularEstatisticas(df_rudp).to_string())
    print()

def main():
    print("="*50)
    print("  Analise - Redes de Computadores II")
    print("="*50)
 
    dfs = carregarLog()
 
    if "TCP_servidor" not in dfs or "RUDP_servidor" not in dfs:
        print("[-] Logs do servidor nao encontrados. Rode os testes primeiro.")
        return
 
    df_tcp  = dfs["TCP_servidor"].copy()
    df_rudp = dfs["RUDP_servidor"].copy()
 
    imprimir_tabela(df_tcp, df_rudp)
 
    print("[*] Gerando graficos...")
    grafico_boxplot(df_tcp, df_rudp)
    grafico_barras(df_tcp, df_rudp)
    grafico_linha(df_tcp, df_rudp)
    #grafico_overhead_total()
    grafico_overhead_wireshark()
 
    print(f"\n[OK] Todos os graficos salvos em: {GRAF_DIR}/")
    print("     - boxplot_throughput.png")
    print("     - barras_throughput.png")
    print("     - linha_throughput.png")
    #print("     - overhead_protocolos.png")
    print("     - overhead_wireshark_cenarios.png")
 
if __name__ == "__main__":
    main()

    