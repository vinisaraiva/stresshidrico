# app_ods64.py
# Streamlit – ODS 6.4.2 (Estresse hídrico) + Retiradas por setor + Acesso à água (JMP)
# Requisitos: pip install streamlit pandas requests plotly

import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="ODS 6.4.2 – Estresse Hídrico e Uso de Água", layout="wide")
st.title("💧 ODS 6.4.2 – Estresse Hídrico, Retiradas por Setor e Acesso à Água (Brasil e América do Sul)")

st.markdown("""
Painel com dados **oficiais** (World Bank/WDI e WHO–UNICEF/JMP).

**O que você vê aqui:**
- **Estresse hídrico** (retirada/recursos) – ODS 6.4.2.
- **Composição das retiradas** (% agro, indústria, doméstico) e **retirada total** (km³).
- **Acesso à água potável gerenciada com segurança** (% população).
- Comparação Brasil × América do Sul, com exportação dos dados filtrados.
""")

# --------------------------- Utilidades de API ---------------------------

WB_BASE = "https://api.worldbank.org/v2"

def fetch_wb_series(iso3_list, indicator, per_page=20000):
    """
    Busca séries do World Bank API (JSON) para uma lista de países (ISO3).
    Retorna DataFrame com colunas: countryiso3code, country, year, value, indicator.
    """
    all_rows = []
    for iso3 in iso3_list:
        page = 1
        while True:
            url = f"{WB_BASE}/country/{iso3}/indicator/{indicator}?format=json&per_page={per_page}&page={page}"
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            j = r.json()
            if not isinstance(j, list) or len(j) < 2 or j[1] is None:
                break
            meta, data = j[0], j[1]
            for rec in data:
                all_rows.append({
                    "countryiso3code": rec.get("countryiso3code"),
                    "country": rec.get("country", {}).get("value"),
                    "year": pd.to_numeric(rec.get("date"), errors="coerce"),
                    "value": pd.to_numeric(rec.get("value"), errors="coerce"),
                    "indicator": indicator
                })
            # paginação
            pages = meta.get("pages", 1)
            if page >= pages:
                break
            page += 1
    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = df.dropna(subset=["year"]).sort_values(["countryiso3code","year"])
    return df

# Lista de países (América do Sul) + Brasil
COUNTRIES = {
    "Brazil": "BRA", "Argentina": "ARG", "Chile": "CHL", "Colombia": "COL", "Peru": "PER",
    "Uruguay": "URY", "Paraguay": "PRY", "Bolivia": "BOL", "Ecuador": "ECU", "Guyana": "GUY", "Suriname": "SUR"
}
iso_all = list(COUNTRIES.values())

# Indicadores
IND_STRESS = "ER.H2O.FWST.ZS"   # Water stress (%)
IND_AGR = "ER.H2O.FWAG.ZS"      # Agriculture share of withdrawals (%)
IND_IND = "ER.H2O.FWIN.ZS"      # Industry share (%)
IND_DOM = "ER.H2O.FWDM.ZS"      # Domestic share (%)
IND_TOT = "ER.H2O.FWTL.K3"      # Total freshwater withdrawal (km3)
IND_SMDW = "SH.H2O.SMDW.ZS"     # Safely managed drinking water (% population)

# --------------------------- Sidebar ---------------------------

st.sidebar.header("Filtros")
sel_countries = st.sidebar.multiselect(
    "Países (comparação)",
    options=list(COUNTRIES.keys()),
    default=["Brazil","Argentina","Chile","Colombia","Peru"]
)
if not sel_countries:
    st.warning("Selecione ao menos 1 país.")
    st.stop()

iso_sel = [COUNTRIES[c] for c in sel_countries]

# --------------------------- Carregar dados ---------------------------

with st.spinner("Baixando séries do World Bank/JMP..."):
    df_stress = fetch_wb_series(iso_sel, IND_STRESS)
    df_agr = fetch_wb_series(iso_sel, IND_AGR)
    df_ind = fetch_wb_series(iso_sel, IND_IND)
    df_dom = fetch_wb_series(iso_sel, IND_DOM)
    df_tot = fetch_wb_series(iso_sel, IND_TOT)
    df_smdw = fetch_wb_series(iso_sel, IND_SMDW)

# recortar interseção de anos disponíveis entre principais séries
def years_available(*dfs):
    sets = []
    for d in dfs:
        if not d.empty:
            sets.append(set(d["year"].dropna().unique().tolist()))
    return sorted(list(set.intersection(*sets))) if sets else []

years_main = years_available(df_stress, df_agr, df_ind, df_dom)
if years_main:
    year_min, year_max = min(years_main), max(years_main)
else:
    year_min, year_max = 2000, 2022  # fallback

sel_year = st.sidebar.slider("Ano (para gráficos de composição e KPIs)", int(year_min), int(year_max), int(year_max))

# --------------------------- KPIs (Brasil) ---------------------------

def latest_value(df, iso3):
    d = df[df["countryiso3code"]==iso3].dropna(subset=["value"])
    if d.empty: return None, None
    row = d.sort_values("year").iloc[-1]
    return row["value"], int(row["year"])

k1, k2, k3, k4 = st.columns(4)
br_iso = "BRA"
v_stress, y_stress = latest_value(df_stress, br_iso)
v_smdw, y_smdw = latest_value(df_smdw, br_iso)
v_tot, y_tot = latest_value(df_tot, br_iso)

k1.metric("🇧🇷 Estresse hídrico (último ano disp.)", f"{v_stress:.1f}%" if v_stress==v_stress else "—", f"Ano {y_stress or '—'}")
k2.metric("Acesso à água segura (JMP)", f"{v_smdw:.1f}%" if v_smdw==v_smdw else "—", f"Ano {y_smdw or '—'}")
k3.metric("Retirada total (km³)", f"{v_tot:.1f}" if v_tot==v_tot else "—", f"Ano {y_tot or '—'}")
k4.metric("Países no painel", f"{len(sel_countries)}")

st.markdown("---")

# --------------------------- Série temporal – Estresse hídrico ---------------------------

if not df_stress.empty:
    fig_stress = px.line(
        df_stress.dropna(subset=["value"]),
        x="year", y="value", color="country",
        labels={"value":"Estresse hídrico (% retirada/recursos)", "year":"Ano", "country":"País"},
        title="ODS 6.4.2 – Estresse hídrico (série temporal)"
    )
    fig_stress.update_traces(mode="lines+markers")
    fig_stress.update_layout(margin=dict(l=20,r=20,t=60,b=20), height=420)
    st.plotly_chart(fig_stress, use_container_width=True)
else:
    st.info("Sem dados de estresse hídrico para os países selecionados.")

# --------------------------- Retiradas por setor (ano selecionado) ---------------------------

def pivot_year(df, name):
    d = df[df["year"]==sel_year][["country","countryiso3code","value"]].rename(columns={"value":name})
    return d

if not (df_agr.empty or df_ind.empty or df_dom.empty):
    p_agr = pivot_year(df_agr, "Agro (%)")
    p_ind = pivot_year(df_ind, "Indústria (%)")
    p_dom = pivot_year(df_dom, "Doméstico (%)")
    comp = p_agr.merge(p_ind, on=["country","countryiso3code"], how="outer").merge(p_dom, on=["country","countryiso3code"], how="outer")
    comp = comp.sort_values("country")
    comp_melt = comp.melt(id_vars=["country"], value_vars=["Agro (%)","Indústria (%)","Doméstico (%)"], var_name="Setor", value_name="Valor (%)")

    c1, c2 = st.columns([2,1])
    with c1:
        fig_stack = px.bar(
            comp_melt, x="country", y="Valor (%)", color="Setor",
            title=f"Composição das retiradas por setor – {sel_year}",
            labels={"country":"País"}
        )
        fig_stack.update_layout(barmode="stack", height=450, margin=dict(l=40,r=20,t=60,b=40))
        st.plotly_chart(fig_stack, use_container_width=True)
    with c2:
        st.dataframe(comp.style.format({"Agro (%)":"{:.1f}","Indústria (%)":"{:.1f}","Doméstico (%)":"{:.1f}"}), use_container_width=True)
else:
    st.info("Sem dados completos de composição por setor para o ano selecionado.")

# --------------------------- Série temporal – Retirada total (km³) ---------------------------

if not df_tot.empty:
    fig_tot = px.line(
        df_tot.dropna(subset=["value"]),
        x="year", y="value", color="country",
        labels={"value":"Retirada total (km³)", "year":"Ano", "country":"País"},
        title="Retirada total de água doce (km³) – série temporal"
    )
    fig_tot.update_traces(mode="lines+markers")
    fig_tot.update_layout(margin=dict(l=20,r=20,t=60,b=20), height=400)
    st.plotly_chart(fig_tot, use_container_width=True)

# --------------------------- Acesso à água segura (JMP) ---------------------------

if not df_smdw.empty:
    fig_smdw = px.line(
        df_smdw.dropna(subset=["value"]),
        x="year", y="value", color="country",
        labels={"value":"Acesso à água potável gerenciada com segurança (% pop.)", "year":"Ano", "country":"País"},
        title="Acesso à água potável (JMP) – série temporal"
    )
    fig_smdw.update_traces(mode="lines+markers")
    fig_smdw.update_layout(margin=dict(l=20,r=20,t=60,b=20), height=400)
    st.plotly_chart(fig_smdw, use_container_width=True)

st.markdown("---")

# --------------------------- Exportação dos dados filtrados ---------------------------

st.subheader("Exportar dados do painel")
def combine_for_export():
    parts = []
    for df, name in [
        (df_stress, "ER.H2O.FWST.ZS"),
        (df_agr, "ER.H2O.FWAG.ZS"),
        (df_ind, "ER.H2O.FWIN.ZS"),
        (df_dom, "ER.H2O.FWDM.ZS"),
        (df_tot, "ER.H2O.FWTL.K3"),
        (df_smdw, "SH.H2O.SMDW.ZS"),
    ]:
        if not df.empty:
            d = df.copy()
            d["indicator"] = name
            parts.append(d[["indicator","countryiso3code","country","year","value"]])
    if parts:
        out = pd.concat(parts, ignore_index=True)
        out = out[out["country"].isin(sel_countries)]
        return out.sort_values(["indicator","country","year"])
    return pd.DataFrame(columns=["indicator","countryiso3code","country","year","value"])

df_out = combine_for_export()
csv_bytes = df_out.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Baixar CSV filtrado", data=csv_bytes, file_name="ods64_panel_data.csv", mime="text/csv")

# --------------------------- Metodologia / Referências ---------------------------

with st.expander("Metodologia e Referências (APA)"):
    st.markdown("""
- **ODS 6.4.2 – Estresse hídrico (ER.H2O.FWST.ZS)**. World Bank, World Development Indicators; fonte primária FAO AQUASTAT.  
- **Retiradas por setor**: Agricultura (ER.H2O.FWAG.ZS), Indústria (ER.H2O.FWIN.ZS), Doméstico (ER.H2O.FWDM.ZS).  
- **Retirada total (km³)**: ER.H2O.FWTL.K3.  
- **Acesso à água potável gerenciada com segurança (JMP)**: SH.H2O.SMDW.ZS (WHO–UNICEF).  

**Citações (APA):**  
World Bank. (2025). *World Development Indicators*. https://data.worldbank.org/indicator/ER.H2O.FWST.ZS  
WHO/UNICEF JMP. (2024). *Drinking water – safely managed services*. https://washdata.org/  
    """)
