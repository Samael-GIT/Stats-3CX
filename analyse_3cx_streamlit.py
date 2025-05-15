import streamlit as st
import pandas as pd
import altair as alt
from datetime import timedelta
import re
import os

st.set_page_config(page_title="Analyseur 3CX", layout="wide")

# Mode développement pour précharger un fichier
DEV_MODE = False  # Mettez à False quand vous déployez
TEST_FILE_PATH = "" # Chemin vers le fichier test

def convert_to_seconds(time_str):
    try:
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s
    except:
        return 0

st.title("📊 Analyseur de Logs 3CX")

uploaded_file = st.file_uploader("📁 Importer un fichier CSV exporté depuis 3CX", type=["csv"])

# Variable pour stocker le DataFrame
df = None

# En mode dev, utiliser automatiquement un fichier test si disponible
if DEV_MODE and not uploaded_file:
    if os.path.exists(TEST_FILE_PATH):
        st.info(f"Mode développement: utilisation du fichier test {TEST_FILE_PATH}")
        try:
            df = pd.read_csv(TEST_FILE_PATH, skiprows=5, dtype=str)
        except Exception as e:
            st.error(f"Erreur lors du chargement du fichier test: {e}")
            st.stop()
elif uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, skiprows=5, dtype=str)
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier: {e}")
        st.stop()

# Si aucun fichier n'a été chargé, arrêter l'exécution
if df is None:
    st.stop()

if "Date" not in df.columns:
    st.error("❌ Colonne 'Date' manquante.")
    st.stop()

# Nettoyage et filtrage
date_pattern = re.compile(r'^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$')
df = df[df["Date"].apply(lambda x: bool(date_pattern.match(str(x))))]

if df.empty:
    st.warning("Aucune ligne valide trouvée avec un format de date exploitable.")
    st.stop()

# Convertir la colonne Date en datetime
df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y %H:%M:%S")
    
# Conversion des durées en secondes
df["Conversation_sec"] = df["Conversation"].astype(str).apply(convert_to_seconds)
df["Sonnerie_sec"] = df["Sonnerie"].astype(str).apply(convert_to_seconds)
df["Totaux_sec"] = df["Totaux"].astype(str).apply(convert_to_seconds)

# Filtrer les lignes avec des durées de conversation cohérentes
df_filtered = df[df["Conversation_sec"] > 0]

# Calculer la date de fin en ajoutant la durée de conversation à la date de début
df["EndDate"] = df["Date"] + pd.to_timedelta(df["Conversation_sec"], unit="s")

st.success(f"Période détectée : du {df['Date'].min()} au {df['Date'].max()}")

# Canaux simultanés
timeline = []
for _, row in df.iterrows():
    if row["Conversation_sec"] > 0:
        timeline.append((row["Date"], 1))
        timeline.append((row["EndDate"], -1))
timeline.sort()

current = 0
max_channels = 0
channel_usage = []
for time, change in timeline:
    current += change
    channel_usage.append((time, current))
    max_channels = max(max_channels, current)

st.subheader("📈 Canaux Simultanés")
st.metric("Canaux simultanés maximum", max_channels)

if channel_usage:
    usage_df = pd.DataFrame(channel_usage, columns=["Temps", "Canaux"])
    
    chart = alt.Chart(usage_df).mark_area(
        color='#1f77b4',
        opacity=0.6,
        line=True
    ).encode(
        x=alt.X('Temps:T', title='Date', axis=alt.Axis(format='%d/%m/%Y', labelAngle=-45)),
        y=alt.Y('Canaux:Q', title='Canaux actifs', scale=alt.Scale(domain=[0, max_channels + 1])),
        tooltip=['Temps:T', 'Canaux:Q']
    ).properties(
        title='Utilisation des canaux dans le temps',
        width='container',
        height=400
    )
    
    st.altair_chart(chart, use_container_width=True)
    
# Afficher les statistiques de la période
st.subheader("📅 Statistiques temporelles")
df["Jour"] = df["Date"].dt.date
df["Heure"] = df["Date"].dt.hour
st.bar_chart(df.groupby("Jour").size(), height=200, use_container_width=True)
st.bar_chart(df.groupby("Heure").size(), height=200, use_container_width=True)

# colonnes pour les tableaux
col1, col2, col3 = st.columns(3)

# Afficher les tableaux dans les colonnes respectives
with col1:
    st.subheader("👤 Top 10 appelants")
    st.dataframe(df_filtered["Appelant"].value_counts().head(10))

with col2:
    st.subheader("🎯 Top 10 destinations")  
    st.dataframe(df_filtered["Destination"].value_counts().head(10))

with col3:
    st.subheader("🧩 Statuts d'appel")
    st.dataframe(df_filtered["Statut"].value_counts())
    
st.subheader("⏱️ Moyennes de durées")
st.write(f"🎤 Conversation moyenne : {df['Conversation_sec'].mean():.2f} sec")
st.write(f"🔔 Sonnerie moyenne : {df['Sonnerie_sec'].mean():.2f} sec")
st.write(f"🕒 Totale moyenne : {df['Totaux_sec'].mean():.2f} sec")

st.subheader("🔎 Appels courts (< 5s)")
st.dataframe(df_filtered[df["Conversation_sec"] < 5][["Date", "Appelant", "Destination", "Conversation"]].head(10))