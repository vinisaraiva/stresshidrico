import streamlit as st
import pandas as pd
import plotly.express as px
import json

# --- Configuração da página ---
st.set_page_config(
    page_title="Extração Hídrica Per Capita Anual",
    layout="wide"
)

st.title("💧 Extração Hídrica Per Capita Anual por Estado")
st.markdown(
    """
    Este painel mostra a **extração hídrica per capita anual** (m³ por habitante por ano)
    nas Unidades Federativas do Brasil, com base nos dados de extração de água (m³/s) do SNIRH/ANA
    e população (IBGE). Use os filtros para explorar por ano, região e visualizar os Top-N estados.
    """
)

# --- Carregamento de dados ---
@st.cache_data
def load_data():
    # Leitura do CSV de extração (m³/s)
    df = pd.read_csv("uso-agua-estado.csv")
    df = df.rename(columns={
        "SGEST":    "UF",
        "NMEST":    "state_name",
        "VZTOTM3S": "flow_m3s",
        "ANO":      "year"
    })
    # Converter fluxo (m³/s) em volume anual (m³)
    seconds_per_year = 365 * 24 * 3600
    df["extraction_annual_m3"] = df["flow_m3s"] * seconds_per_year

    # Leitura do CSV de população
    df_pop = pd.read_csv("populacao_uf.csv")  # colunas: UF, populacao
    df = df.merge(df_pop, on="UF", how="left")

    # Cálculo da extração per capita (m³ por habitante/ano)
    df["extraction_per_capita"] = df["extraction_annual_m3"] / df["populacao"]

    # Mapeamento de regiões brasileiras
    region_map = {
        'RO':'Norte','AC':'Norte','AM':'Norte','RR':'Norte','PA':'Norte','AP':'Norte','TO':'Norte',
        'MA':'Nordeste','PI':'Nordeste','CE':'Nordeste','RN':'Nordeste','PB':'Nordeste','PE':'Nordeste','AL':'Nordeste','SE':'Nordeste','BA':'Nordeste',
        'MG':'Sudeste','ES':'Sudeste','RJ':'Sudeste','SP':'Sudeste',
        'PR':'Sul','SC':'Sul','RS':'Sul',
        'MT':'Centro-Oeste','MS':'Centro-Oeste','GO':'Centro-Oeste','DF':'Centro-Oeste'
    }
    df['region'] = df['UF'].map(region_map)
    return df

@st.cache_data
def load_geojson():
    # Carrega o GeoJSON local para as fronteiras dos estados
    with open("brazil_states.geojson", "r", encoding="utf-8") as f:
        return json.load(f)

# --- Dados e geometrias ---
df = load_data()
geo = load_geojson()

# --- Função principal ---
def main():
    # Sidebar de filtros
    st.sidebar.header("Filtros")
    years = sorted(df['year'].unique())
    selected_year = st.sidebar.selectbox("Ano de Extração", years, index=len(years)-1)
    regions = sorted(df['region'].dropna().unique())
    selected_regions = st.sidebar.multiselect("Regiões", regions, default=regions)
    max_states = df['state_name'].nunique()
    top_n = st.sidebar.slider("Top-N Estados", 1, max_states, min(10, max_states))

    # Aplicar filtros
    df_sel = df[(df['year'] == selected_year) & (df['region'].isin(selected_regions))]
    df_sel = df_sel.dropna(subset=['extraction_per_capita'])
    df_top = df_sel.sort_values('extraction_per_capita', ascending=False).head(top_n)

    # --- Mapa coroplético ---
    fig_map = px.choropleth(
        df_sel,
        geojson=geo,
        locations='state_name',
        featureidkey='properties.Estado',
        color='extraction_per_capita',
        color_continuous_scale='Blues',
        projection='mercator',
        title=f"Extração Hídrica Per Capita Anual – {selected_year}",
        labels={'extraction_per_capita':'m³ por hab·ano'},
        hover_data={'extraction_per_capita':':,.0f'}
    )
    fig_map.update_traces(marker_line_color='black', marker_line_width=1)
    fig_map.update_geos(fitbounds='locations', visible=False)
    fig_map.update_layout(margin=dict(l=0, r=0, t=50, b=0), height=600)

    # --- Gráfico de barras ---
    fig_bar = px.bar(
        df_top,
        x='extraction_per_capita',
        y='state_name',
        orientation='h',
        title=f"Top {top_n} Estados – Extração Per Capita",
        labels={'state_name':'Estado', 'extraction_per_capita':'m³ por hab·ano'},
        text=df_top['extraction_per_capita'].round(0)
    )
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_layout(yaxis=dict(dtick=1), margin=dict(l=140, r=40, t=60, b=40), height=600)

    # --- Layout de colunas ---
    col1, col2 = st.columns([4, 3])
    with col1:
        st.plotly_chart(fig_map, use_container_width=True)
    with col2:
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- Rodapé ---
    st.markdown('---')
    st.markdown(
        """
        **Fontes (APA):**  
        Agência Nacional de Águas – SNIRH. (2021). Uso da água por estado (m³/s). Dados Abertos ANA.  
        Instituto Brasileiro de Geografia e Estatística. (2021). População estimada por unidade da federação. SIDRA IBGE.  
        """
    )

if __name__ == '__main__':
    main()