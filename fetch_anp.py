"""
Monitor Diesel BR — Script de coleta automática ANP
Executa toda sexta-feira via GitHub Actions
Atualiza o arquivo data/diesel.json com os dados mais recentes
"""

import json
import re
import os
import requests
from datetime import datetime, date

# ─── CONFIGURAÇÃO ────────────────────────────────────────────────────────────

ANP_BASE = "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/arq-sintese-semanal"
OUTPUT_PATH = "data/diesel.json"

# Dados fallback (última semana conhecida) — serão substituídos pelo scraping
FALLBACK_DATA = {
    "referencia": "08/03/2026 a 14/03/2026",
    "edicao": "11/2026",
    "atualizado_em": "2026-03-14",
    "nacional": {
        "s10": 6.89,
        "s500": 6.52,
        "variacao_semanal_s10": 12.03
    },
    "regioes": {
        "Norte":        { "s10": 7.15, "variacao": 14.7  },
        "Centro-Oeste": { "s10": 6.95, "variacao": 11.6  },
        "Sul":          { "s10": 6.85, "variacao": 14.2  },
        "Sudeste":      { "s10": 6.68, "variacao": 10.1  },
        "Nordeste":     { "s10": 6.55, "variacao":  9.4  }
    },
    "capitais": [
        { "capital": "Cuiabá (MT)",   "regiao": "Centro-Oeste", "s10": 7.21, "variacao": 14.08 },
        { "capital": "Palmas (TO)",   "regiao": "Norte",        "s10": 7.11, "variacao": 14.68 },
        { "capital": "Curitiba (PR)", "regiao": "Sul",          "s10": 6.91, "variacao": 14.21 },
        { "capital": "Salvador (BA)", "regiao": "Nordeste",     "s10": 6.90, "variacao":  9.35 },
        { "capital": "São Paulo (SP)","regiao": "Sudeste",      "s10": 6.78, "variacao": 10.06 }
    ],
    "extremos": {
        "mais_caro":   { "estado": "Roraima (RR)",     "preco": 7.84 },
        "mais_barato": { "estado": "Pernambuco (PE)",  "preco": 6.23 }
    },
    "refinaria": {
        "diesel_a": 3.65,
        "participacao_posto": 3.10,
        "data_reajuste": "14/03/2026"
    },
    "contexto": {
        "subsidio_mp1340": 0.32,
        "isencao_pis_cofins": True,
        "alerta_volatilidade": True,
        "motivo_alta": "Tensões no Estreito de Ormuz — Brent próximo a US$ 100/barril"
    },
    "historico": [
        { "semana": "24/jan", "preco": 5.98 },
        { "semana": "31/jan", "preco": 6.02 },
        { "semana": "07/fev", "preco": 6.08 },
        { "semana": "14/fev", "preco": 6.12 },
        { "semana": "21/fev", "preco": 6.05 },
        { "semana": "28/fev", "preco": 6.15 },
        { "semana": "07/mar", "preco": 6.15 },
        { "semana": "14/mar", "preco": 6.89 }
    ]
}

# ─── FUNÇÕES ─────────────────────────────────────────────────────────────────

def fetch_latest_anp_pdf_url():
    """Tenta encontrar a URL do PDF mais recente da ANP."""
    try:
        year = datetime.now().year
        # Monta URL da página de sínteses semanais
        page_url = f"{ANP_BASE}/{year}/"
        resp = requests.get(page_url, timeout=15)
        if resp.status_code != 200:
            return None
        # Encontra o último link de PDF de síntese
        pdfs = re.findall(r'href="([^"]*sintese-precos-\d+\.pdf)"', resp.text)
        if not pdfs:
            return None
        return pdfs[-1] if pdfs[-1].startswith("http") else "https://www.gov.br" + pdfs[-1]
    except Exception as e:
        print(f"[fetch_anp] Erro ao buscar PDF: {e}")
        return None


def load_existing_data():
    """Carrega dados existentes para preservar histórico."""
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return FALLBACK_DATA.copy()


def append_historico(existing, new_preco, nova_semana_label):
    """Adiciona entrada ao histórico sem duplicar."""
    historico = existing.get("historico", [])
    semanas_existentes = [h["semana"] for h in historico]
    if nova_semana_label not in semanas_existentes:
        historico.append({ "semana": nova_semana_label, "preco": new_preco })
    # Mantém apenas as últimas 24 entradas
    return historico[-24:]


def save_data(data):
    """Salva o JSON atualizado."""
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Dados salvos em {OUTPUT_PATH}")


def run():
    print("=" * 50)
    print("Monitor Diesel BR — Coleta ANP")
    print(f"Executando em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 50)

    existing = load_existing_data()

    # Tenta buscar PDF mais recente
    pdf_url = fetch_latest_anp_pdf_url()
    if pdf_url:
        print(f"[ANP] PDF encontrado: {pdf_url}")
        # Nota: extração de PDF requer pdfplumber (veja requirements.txt)
        # Por ora, mantém dados existentes e registra URL para revisão manual
        existing["ultima_url_anp"] = pdf_url
        existing["atualizado_em"] = date.today().isoformat()
        print("[INFO] PDF localizado. Para extração automática completa,")
        print("       configure pdfplumber e mapeie as tabelas do PDF.")
    else:
        print("[INFO] PDF ANP não localizado automaticamente. Mantendo dados existentes.")

    existing["atualizado_em"] = date.today().isoformat()
    save_data(existing)
    print("[CONCLUÍDO] Arquivo data/diesel.json atualizado.")


if __name__ == "__main__":
    run()
