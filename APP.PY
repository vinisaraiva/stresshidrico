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
    """Busca séries do World Bank API (JSON) para uma lista de países (ISO3)."""
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
            if page >= meta.get("pages", 1):
                break
            page += 1
    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = df.dropna(subset=["year"]).sort_values(["countryiso3code","year"])
    return df

def years_intersection(*dfs):
    sets = []
    for d in dfs:
        if not d.empty:
            sets.append(set(d["year"].dropna().unique().tolist()))
    return sorted(list(set.intersection(*sets))) if sets else []

def years_union(*dfs):
    all_years = set()
    for d in dfs:
        if not d.empty:
            all_years |= set(d["year"].dropna().unique().tolist())
    return sorted(list(all_years))

# --------------------------- Países & Indicadores ---------------------------

COUNTRIES = {
    "Brazil": "BRA", "Argentina": "ARG", "Chile": "CHL", "Colombia": "COL", "Peru": "PER",
    "Uruguay": "URY", "Paraguay": "PRY", "Bolivia": "BOL", "Ecuador": "ECU", "Guyana": "GUY", "Suriname": "SUR"
}
iso_all = list(COUNTRIES.values())

IND_STRESS = "ER.H2O.FWST.ZS"   # Water stress (%)
IND_AGR    = "ER.H2O.FWAG.ZS"   # Agriculture share (%)
IND_IND    = "ER.H2O.FWIN.ZS"   # Industry share (%)
IND_DOM    = "ER.H2O.FWDM.ZS"   # Domestic share (%)
IND_TOT    = "ER.H2O.FWTL.K3"   # Total withdrawal (km³)
IND_SMDW   = "SH.H2O.SMDW.ZS"   # Safely managed drinking water (%)

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
    df_agr    = fetch_wb_series(iso_sel, IND_AGR)
    df_ind    = fetch_wb_series(iso_sel, IND_IND)
    df_dom    = fetch_wb_series(iso_sel, IND_DOM)
    df_tot    = fetch_wb_series(iso_sel, IND_TOT)
    df_smdw   = fetch_wb_series(iso_sel, IND_SMDW)

# intervalo para SÉRIES TEMPORAIS (novo: permite escolher ano inicial e final)
years_all = years_union(df_stress, df_tot, df_smdw)
if years_all:
    y_min, y_max = int(min(years_all)), int(max(years_all))
    if y_min < y_max:
        yr_start, yr_end = st.sidebar.slider(
            "Intervalo para séries temporais (e KPIs)",
            min_value=y_min, max_value=y_max, value=(y_min, y_max), step=1
        )
    else:
        yr_start = yr_end = y_min
        st.sidebar.info("Séries disponíveis apenas para um ano.")
else:
    yr_start = yr_end = 2020

# ANO para composição por setor (barras empilhadas) — escolhe dentro do conjunto comum
years_main = years_intersection(df_agr, df_ind, df_dom)
if years_main:
    # sugere o final do intervalo das séries, ou o último ano comum disponível
    default_year = yr_end if yr_end in years_main else max(years_main)
    sel_year = st.sidebar.select_slider(
        "Ano (para gráfico de composição por setor e tabela)",
        options=years_main, value=default_year
    )
else:
    sel_year = None

# --------------------------- KPIs (Brasil) ---------------------------

def latest_value_le(df, iso3, year_max=None):
    d = df[df["countryiso3code"]==iso3].dropna(subset=["value"])
    if year_max is not None:
        d = d[d["year"] <= year_max]
    if d.empty:
        return None, None
    row = d.sort_values("year").iloc[-1]
    return row["value"], int(row["year"])

k1, k2, k3, k4 = st.columns(4)
br_iso = "BRA"
v_stress, y_stress = latest_value_le(df_stress, br_iso, yr_end)
v_smdw,  y_smdw    = latest_value_le(df_smdw,  br_iso, yr_end)
v_tot,   y_tot     = latest_value_le(df_tot,   br_iso, yr_end)

k1.metric("🇧🇷 Estresse hídrico (últ. disp. ≤ fim do intervalo)", f"{v_stress:.1f}%" if v_stress==v_stress else "—", f"Ano {y_stress or '—'}")
k2.metric("Acesso à água segura (JMP)", f"{v_smdw:.1f}%" if v_smdw==v_smdw else "—", f"Ano {y_smdw or '—'}")
k3.metric("Retirada total (km³)", f"{v_tot:.1f}" if v_tot==v_tot else "—", f"Ano {y_tot or '—'}")
k4.metric("Países no painel", f"{len(sel_countries)}")

st.markdown("---")

# ------------- helpers de filtro por intervalo -------------
def filter_range(df, a, b):
    if df.empty: return df
    return df[(df["year"]>=a) & (df["year"]<=b)]

# --------------------------- Série temporal – Estresse hídrico ---------------------------

if not df_stress.empty:
    dplot = filter_range(df_stress.dropna(subset=["value"]), yr_start, yr_end)
    fig_stress = px.line(
        dplot, x="year", y="value", color="country",
        labels={"value":"Estresse hídrico (% retirada/recursos)", "year":"Ano", "country":"País"},
        title=f"ODS 6.4.2 – Estresse hídrico (série temporal) — {yr_start}–{yr_end}"
    )
    fig_stress.update_traces(mode="lines+markers")
    # destaca Brasil
    for tr in fig_stress.data:
        if tr.name == "Brazil":
            tr.update(line=dict(width=4))
        else:
            tr.update(line=dict(width=2))
    fig_stress.update_layout(margin=dict(l=20,r=20,t=60,b=20), height=420, legend_title_text="")
    st.plotly_chart(fig_stress, use_container_width=True)
else:
    st.info("Sem dados de estresse hídrico para os países selecionados.")

# --------------------------- Retiradas por setor (ano selecionado) ---------------------------

def pivot_year(df, name, year):
    d = df[df["year"]==year][["country","countryiso3code","value"]].rename(columns={"value":name})
    return d

if sel_year is not None:
    p_agr = pivot_year(df_agr, "Agro (%)", sel_year)
    p_ind = pivot_year(df_ind, "Indústria (%)", sel_year)
    p_dom = pivot_year(df_dom, "Doméstico (%)", sel_year)
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
        fig_stack.update_layout(barmode="stack", height=450, margin=dict(l=40,r=20,t=60,b=40), legend_title_text="")
        st.plotly_chart(fig_stack, use_container_width=True)
    with c2:
        st.dataframe(comp.style.format({"Agro (%)":"{:.1f}","Indústria (%)":"{:.1f}","Doméstico (%)":"{:.1f}"}), use_container_width=True)
else:
    st.info("Sem interseção de anos entre as séries setoriais para o gráfico de composição.")

# --------------------------- Série temporal – Retirada total (km³) ---------------------------

if not df_tot.empty:
    dplot = filter_range(df_tot.dropna(subset=["value"]), yr_start, yr_end)
    fig_tot = px.line(
        dplot, x="year", y="value", color="country",
        labels={"value":"Retirada total (km³)", "year":"Ano", "country":"País"},
        title=f"Retirada total de água doce (km³) — {yr_start}–{yr_end}"
    )
    fig_tot.update_traces(mode="lines+markers")
    fig_tot.update_layout(margin=dict(l=20,r=20,t=60,b=20), height=400, legend_title_text="")
    st.plotly_chart(fig_tot, use_container_width=True)

# --------------------------- Acesso à água segura (JMP) ---------------------------

if not df_smdw.empty:
    dplot = filter_range(df_smdw.dropna(subset=["value"]), yr_start, yr_end)
    fig_smdw = px.line(
        dplot, x="year", y="value", color="country",
        labels={"value":"Acesso à água potável gerenciada com segurança (% pop.)", "year":"Ano", "country":"País"},
        title=f"Acesso à água potável (JMP) — {yr_start}–{yr_end}"
    )
    fig_smdw.update_traces(mode="lines+markers")
    fig_smdw.update_layout(margin=dict(l=20,r=20,t=60,b=20), height=400, legend_title_text="")
    st.plotly_chart(fig_smdw, use_container_width=True)

st.markdown("---")

# --------------------------- Exportação dos dados filtrados ---------------------------

st.subheader("Exportar dados do painel")
def combine_for_export():
    parts = []
    for df, name in [
        (df_stress, IND_STRESS),
        (df_agr,    IND_AGR),
        (df_ind,    IND_IND),
        (df_dom,    IND_DOM),
        (df_tot,    IND_TOT),
        (df_smdw,   IND_SMDW),
    ]:
        if not df.empty:
            d = df[(df["year"]>=yr_start) & (df["year"]<=yr_end)].copy()
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
