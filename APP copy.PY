import streamlit as st
import pandas as pd
import plotly.express as px
import json

# --- Configuração da página ---
st.set_page_config(
    page_title="Pegada Hídrica Per Capita Anual por Estado",
    layout="wide"
)

st.title("📊 Pegada Hídrica Per Capita Anual por Estado")
st.markdown(
    """
    Análise interativa da **pegada hídrica per capita anual** (m³ por habitante/ano) das Unidades
    Federativas do Brasil, combinando dados de extração de água (SNIRH/ANA) em m³/s e população (IBGE).
    Use os filtros para explorar por ano, região e selecione quantos estados exibir.
    """
)

# --- Carrega dados ---
@st.cache_data
def load_data():
    df = pd.read_csv("uso-agua-estado.csv")
    df = df.rename(columns={
        "SGEST": "UF",
        "NMEST": "state_name",
        "VZTOTM3S": "flow_m3s",
        "ANO": "year"
    })
    seconds_per_year = 365 * 24 * 3600
    df["volume_annual_m3"] = df["flow_m3s"] * seconds_per_year
    df_pop = pd.read_csv("populacao_uf.csv")  # colunas: UF, populacao
    df = df.merge(df_pop, on="UF", how="left")
    df["pegada_per_capita_ano"] = df["volume_annual_m3"] / df["populacao"]
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
    # GeoJSON oficial com siglas em 'abbr'
    import requests
    url = (
        "https://raw.githubusercontent.com/"
        "codeforamerica/click_that_hood/master/"
        "public/data/brazil-states.geojson"
    )
    return requests.get(url).json()

# Dataframe principal e geojson
df = load_data()
geo = load_geojson()

def main():
    st.sidebar.header("Filtros")
    years = sorted(df['year'].unique())
    selected_year = st.sidebar.selectbox("Ano (SNIRH)", years, index=len(years)-1)
    regions = sorted(df['region'].dropna().unique())
    selected_regions = st.sidebar.multiselect("Regiões", regions, default=regions)
    max_states = df['state_name'].nunique()
    top_n = st.sidebar.slider("Top-N Estados", 1, max_states, min(10, max_states))

    df_sel = df[(df['year'] == selected_year) & (df['region'].isin(selected_regions))]
    df_sel = df_sel.dropna(subset=['pegada_per_capita_ano'])
    df_top = df_sel.sort_values('pegada_per_capita_ano', ascending=False).head(top_n)

    # Mapa coroplético completo
    fig_map = px.choropleth(
        df_sel,
        geojson=geo,
        locations='UF',
        featureidkey='properties.abbr',  # usa a propriedade 'abbr'
        color='pegada_per_capita_ano',
        color_continuous_scale='Viridis',
        projection='mercator',
        title=f"Pegada Hídrica Per Capita Anual – {selected_year}",
        labels={'pegada_per_capita_ano': 'm³ por hab·ano'},
        hover_name='state_name'
    )
    fig_map.update_traces(marker_line_color='black', marker_line_width=0.5)
    fig_map.update_geos(fitbounds='locations', visible=False)
    fig_map.update_layout(margin={'l':0,'r':0,'t':50,'b':0}, height=600)

    # Gráfico de barras para Top-N
    fig_bar = px.bar(
        df_top,
        x='pegada_per_capita_ano',
        y='state_name',
        orientation='h',
        title=f"Top {top_n} Estados – Pegada Hídrica Per Capita Anual",
        labels={'state_name': 'Estado', 'pegada_per_capita_ano': 'm³ por hab·ano'},
        text=df_top['pegada_per_capita_ano'].round(1)
    )
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_layout(yaxis=dict(dtick=1), margin={'l':140,'r':40,'t':60,'b':40}, height=600)

    # Layout mais largo
    col1, col2 = st.columns([5, 1])
    with col1:
        st.plotly_chart(fig_map, use_container_width=True)
    with col2:
        st.plotly_chart(fig_bar, use_container_width=True)

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
