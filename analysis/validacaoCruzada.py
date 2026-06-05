import pandas as pd
import os

BASE_DIR = "/app"

LOG_DIR = os.path.join(BASE_DIR, "logs")
WIRE_DIR = os.path.join(BASE_DIR, "wireshark")
CENARIOS = ["A", "B", "C"]


def carregar_log_python(protocolo):
    arquivo = os.path.join(LOG_DIR, f"log_{protocolo.lower()}_servidor.csv")
    if not os.path.exists(arquivo):
        print(f"[!] Nao encontrado: {arquivo}")
        return None
    return pd.read_csv(arquivo)


def carregar_wireshark(protocolo, cenario):
    arquivo = os.path.join(WIRE_DIR, f"wireshark_{protocolo.lower()}_cenario{cenario}.csv")
    if not os.path.exists(arquivo):
        return None
    df = pd.read_csv(arquivo)
    df.columns = [c.strip().replace('"', '') for c in df.columns]
    return df


def metricas_wireshark(df_wire, repeticoes=15):
    if df_wire is None:
        return None

    df_wire["Time"]   = pd.to_numeric(df_wire["Time"],   errors="coerce")
    df_wire["Length"] = pd.to_numeric(df_wire["Length"], errors="coerce")
    df_wire = df_wire.dropna(subset=["Time", "Length"]).reset_index(drop=True)

    total   = len(df_wire)
    por_exec = total // repeticoes

    registros = []
    for i in range(repeticoes):
        inicio = i * por_exec
        fim    = (i + 1) * por_exec if i < repeticoes - 1 else total
        bloco  = df_wire.iloc[inicio:fim]

        bytes_total = bloco["Length"].sum()
        duracao     = bloco["Time"].iloc[-1] - bloco["Time"].iloc[0]
        throughput  = (bytes_total / duracao) / 1024 if duracao > 0 else 0

        registros.append({
            "execucao":                 i + 1,
            "bytes_wireshark":          int(bytes_total),
            "duracao_wireshark":        round(duracao, 6),
            "throughput_wireshark_kBps": round(throughput, 4),
        })

    return pd.DataFrame(registros)


def compararMetricas(protocolo, cenario, repeticoes=15):
    print(f"\n{'='*60}")
    print(f"  {protocolo} — Cenario {cenario}")
    print(f"{'='*60}")

    df_python = carregar_log_python(protocolo)
    if df_python is None:
        return

    col_bytes  = "bytes" if "bytes" in df_python.columns else "bytes_enviados"
    df_cenario = df_python[df_python["cenario"] == cenario].reset_index(drop=True)

    if df_cenario.empty:
        print(f"[!] Nenhum registro do cenario {cenario} no log Python.")
        return

    df_wire   = carregar_wireshark(protocolo, cenario)
    df_metrics = metricas_wireshark(df_wire, repeticoes)

    if df_metrics is None:
        print(f"[!] CSV do Wireshark nao encontrado.")
        print(f"    Salve em: {WIRE_DIR}/wireshark_{protocolo.lower()}_cenario{cenario}.csv")
        print(f"\n  Dados Python ({len(df_cenario)} execucoes):")
        print(f"  Bytes     — min: {df_cenario[col_bytes].min():.0f} | media: {df_cenario[col_bytes].mean():.0f} | max: {df_cenario[col_bytes].max():.0f}")
        print(f"  Duracao   — min: {df_cenario['duracao_s'].min():.4f}s | media: {df_cenario['duracao_s'].mean():.4f}s | max: {df_cenario['duracao_s'].max():.4f}s")
        print(f"  Throughput — min: {df_cenario['throughput_kBps'].min():.2f} | media: {df_cenario['throughput_kBps'].mean():.2f} | max: {df_cenario['throughput_kBps'].max():.2f} KB/s")
        return

    n = min(len(df_cenario), len(df_metrics))
    print(f"\n  {'Exec':>4} | {'Bytes Python':>14} | {'Bytes Wire':>12} | {'Dur Python':>12} | {'Dur Wire':>10} | {'Diff%':>6}")
    print(f"  {'-'*4}-+-{'-'*14}-+-{'-'*12}-+-{'-'*12}-+-{'-'*10}-+-{'-'*6}")

    for i in range(n):
        bp   = df_cenario[col_bytes].iloc[i]
        bw   = df_metrics["bytes_wireshark"].iloc[i]
        dp   = df_cenario["duracao_s"].iloc[i]
        dw   = df_metrics["duracao_wireshark"].iloc[i]
        diff = abs(bp - bw) / bp * 100 if bp > 0 else 0
        print(f"  {i+1:>4} | {bp:>14.0f} | {bw:>12.0f} | {dp:>12.4f}s | {dw:>10.4f}s | {diff:>5.1f}%")

    media_diff = abs(df_cenario[col_bytes].mean() - df_metrics["bytes_wireshark"].mean()) / df_cenario[col_bytes].mean() * 100
    media_dur  = abs(df_cenario["duracao_s"].mean() - df_metrics["duracao_wireshark"].mean())

    print(f"\n  Diferenca media em bytes  : {media_diff:.1f}%")
    print(f"  Diferenca media em duracao: {media_dur:.4f}s")
    print(f"  {'[OK] Validacao aprovada' if media_diff < 5 else '[!] Diferenca acima de 5%'}")


def main():
    print("=" * 60)
    print("  Validacao Cruzada Python vs Wireshark")
    print("  Redes de Computadores II")
    print("=" * 60)

    os.makedirs(WIRE_DIR, exist_ok=True)

    for cenario in CENARIOS:
        compararMetricas("TCP",  cenario)
        compararMetricas("RUDP", cenario)

    print(f"\n{'='*60}")
    print("  Para completar: exporte cada .pcap do Wireshark como CSV")
    print(f"  Salve em: {WIRE_DIR}/")
    print(f"  Ex: wireshark_tcp_cenarioA.csv")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
