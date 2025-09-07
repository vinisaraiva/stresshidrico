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
    Este painel exibe indicadores-chave da **extração hídrica per capita anual** (m³ por habitante por ano)
    nas Unidades Federativas do Brasil, combinando dados de extração (m³/s) do SNIRH/ANA e população (IBGE).
    Use os filtros para explorar por ano, região, escolha paleta de cores e visualize estatísticas descritivas,
    mapa coroplético, histograma de distribuição e ranking de estados.
    """
)

# --- Carregamento de dados ---
@st.cache_data
def load_data():
    # Leitura do CSV de extração (m³/s)
    df = pd.read_csv("uso-agua-estado.csv")
    df = df.rename(columns={
        "SGEST": "UF",
        "NMEST": "state_name",
        "VZTOTM3S": "flow_m3s",
        "ANO": "year"
    })
    # Converte fluxo m³/s para volume anual (m³)
    seconds_per_year = 365 * 24 * 3600
    df['extraction_annual_m3'] = df['flow_m3s'] * seconds_per_year

    # Leitura do CSV de população
    df_pop = pd.read_csv("populacao_uf.csv")  # colunas: UF, populacao
    df = df.merge(df_pop, on='UF', how='left')

    # Cálculo da extração per capita anual (m³/hab·ano)
    df['extraction_per_capita'] = df['extraction_annual_m3'] / df['populacao']

    # Mapeamento de regiões
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
    # Carrega geometrias locais
    with open('brazil_states.geojson', 'r', encoding='utf-8') as f:
        return json.load(f)

# Carrega dados e geojson
df = load_data()
geo = load_geojson()

# --- Função principal ---
def main():
    st.sidebar.header("Filtros")

    # Filtros
    years = sorted(df['year'].unique())
    selected_year = st.sidebar.selectbox("Ano de Extração", years, index=len(years)-1)

    regions = sorted(df['region'].dropna().unique())
    selected_regions = st.sidebar.multiselect("Regiões", regions, default=regions)

    max_states = df['state_name'].nunique()
    top_n = st.sidebar.slider("Top-N Estados", 1, max_states, value=min(10, max_states))

    colorscales = ['Blues', 'Viridis', 'Cividis']
    scale = st.sidebar.selectbox("Paleta de Cores", colorscales, index=0)

    # Filtragem dos dados
    df_sel = df[(df['year'] == selected_year) & (df['region'].isin(selected_regions))]
    df_sel = df_sel.dropna(subset=['extraction_per_capita'])
    df_top = df_sel.nlargest(top_n, 'extraction_per_capita')

    # Métricas (KPIs)
    mean_val = df_sel['extraction_per_capita'].mean()
    max_row = df_sel.loc[df_sel['extraction_per_capita'].idxmax()]
    min_row = df_sel.loc[df_sel['extraction_per_capita'].idxmin()]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Média Nacional", f"{mean_val:,.0f} m³/hab·ano")
    k2.metric("Maior Estado", max_row['state_name'], f"{max_row['extraction_per_capita']:,.0f}")
    k3.metric("Menor Estado", min_row['state_name'], f"{min_row['extraction_per_capita']:,.0f}")
    k4.metric("Estados em Análise", len(df_sel))

    # Botão de exportação
    st.download_button(
        label="📥 Exportar Dados (CSV)",
        data=df_sel.to_csv(index=False),
        file_name=f"extraction_{selected_year}.csv",
        mime='text/csv'
    )

    # --- Mapa Coroplético ---
    fig_map = px.choropleth(
        df_sel,
        geojson=geo,
        locations='state_name',
        featureidkey='properties.Estado',
        color='extraction_per_capita',
        color_continuous_scale=scale,
        projection='mercator',
        title=f"Extração Hídrica Per Capita – {selected_year}",
        labels={'extraction_per_capita':'m³ por hab·ano'},
        hover_data={'extraction_per_capita':':,.0f'}
    )
    fig_map.update_traces(
        marker_line_color='black',
        marker_line_width=1.5,
        hoverlabel=dict(bgcolor='white', font_size=12, font_color='black')
    )
    fig_map.update_geos(fitbounds='locations', visible=False)
    fig_map.update_layout(margin=dict(l=0, r=0, t=50, b=0), height=500)

    # --- Histograma de Distribuição ---
    fig_hist = px.histogram(
        df_sel,
        x='extraction_per_capita',
        nbins=20,
        title="Distribuição da Extração Per Capita",
        labels={'extraction_per_capita':'m³ por hab·ano'}
    )
    fig_hist.update_layout(margin=dict(l=40, r=40, t=50, b=40), height=300)

    # --- Gráfico de Barras Top-N ---
    fig_bar = px.bar(
        df_top,
        x='extraction_per_capita',
        y='state_name',
        orientation='h',
        title=f"Top {top_n} Estados – Extração Per Capita",
        labels={'state_name':'Estado', 'extraction_per_capita':'m³ por hab·ano'},
        text=df_top['extraction_per_capita'].round(0)
    )
    fig_bar.add_vline(
        x=mean_val,
        line_dash='dash',
        annotation_text='Média Nacional',
        annotation_position='top right'
    )
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_layout(margin=dict(l=140, r=40, t=60, b=40), height=500)

    # --- Layout de Colunas ---
    left, right = st.columns([2, 3])
    with left:
        st.plotly_chart(fig_map, use_container_width=True)
        st.plotly_chart(fig_hist, use_container_width=True)
    with right:
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