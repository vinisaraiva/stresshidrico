import pandas as pd

# passo 1: leia o CSV original
df = pd.read_csv("POP2024_20241230.xlsx - BRASIL E UFs.csv", sep=",")

# passo 2: renomeie e limpe
df.columns = ["state_name", "populacao"]
to_drop = ["Brasil", "Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
df = df[~df["state_name"].isin(to_drop)]

# passo 3: mapeie nome para UF
name2uf = { ... }  # seu dicionário de nomes → siglas
df["UF"] = df["state_name"].map(name2uf)

# passo 4: elimine linhas sem UF ou sem população
df = df.dropna(subset=["UF", "populacao"])

# passo 5: converta população para inteiro
# primeiro passe tudo pra string e só então remova pontos
df["populacao"] = (
    df["populacao"]
      .astype(str)                           # garante string
      .str.replace(".", "", regex=False)     # tira separador de milhar
      .str.replace(",", "", regex=False)     # em caso de vírgula decimal
)
# agora não há mais NaN: converte para int
df["populacao"] = df["populacao"].astype(int)

# passo 6: grave o CSV final
populacao_uf = df[["UF","populacao"]]
populacao_uf.to_csv("populacao_uf.csv", index=False)
