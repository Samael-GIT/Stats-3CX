
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
import re

st.set_page_config(page_title="Analyseur 3CX", layout="wide")

def convert_to_seconds(time_str):
    try:
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s
    except:
        return 0

st.title("📊 Analyseur de Logs 3CX")

uploaded_file = st.file_uploader("📁 Importer un fichier CSV exporté depuis 3CX", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, skiprows=5, dtype=str)
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier : {e}")
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

    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    df = df.dropna(subset=["Date"])

    df["Conversation_sec"] = df["Conversation"].astype(str).apply(convert_to_seconds)
    df["Sonnerie_sec"] = df["Sonnerie"].astype(str).apply(convert_to_seconds)
    df["Totaux_sec"] = df["Totaux"].astype(str).apply(convert_to_seconds)
    df["EndDate"] = df["Date"] + pd.to_timedelta(df["Conversation_sec"], unit="s")

    st.success(f"Période réelle détectée : du {df['Date'].min()} au {df['Date'].max()}")

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
        times, usages = zip(*channel_usage)
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(times, usages, label="Canaux actifs")
        ax.set_title("Utilisation des canaux dans le temps")
        ax.set_xlabel("Date")
        ax.set_ylabel("Canaux")
        ax.grid(True)
        st.pyplot(fig)

    st.subheader("📅 Statistiques temporelles")
    df["Jour"] = df["Date"].dt.date
    df["Heure"] = df["Date"].dt.hour
    st.bar_chart(df.groupby("Jour").size(), height=200, use_container_width=True)
    st.bar_chart(df.groupby("Heure").size(), height=200, use_container_width=True)

    st.subheader("👤 Top 10 appelants")
    st.dataframe(df["Appelant"].value_counts().head(10))

    st.subheader("🎯 Top 10 destinations")
    st.dataframe(df["Destination"].value_counts().head(10))

    st.subheader("🧩 Statuts d’appel")
    st.dataframe(df["Statut"].value_counts())

    st.subheader("⏱️ Moyennes de durées")
    st.write(f"🎤 Conversation moyenne : {df['Conversation_sec'].mean():.2f} sec")
    st.write(f"🔔 Sonnerie moyenne : {df['Sonnerie_sec'].mean():.2f} sec")
    st.write(f"🕒 Totale moyenne : {df['Totaux_sec'].mean():.2f} sec")

    st.subheader("🔎 Appels courts (< 5s)")
    st.dataframe(df[df["Conversation_sec"] < 5][["Date", "Appelant", "Destination", "Conversation"]].head(10))
