# Generated from: Internship.ipynb
# Converted at: 2026-02-10T23:58:00.801Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

import streamlit as st
import pandas as pd
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Radar à Stages", page_icon="🎯", layout="wide")
st.title("🎯 Radar à Stages")

# --- INITIALISATION DES VARIABLES (Session State) ---
# Cela permet de garder les données en mémoire entre chaque rafraîchissement de la page
if 'sites_cibles' not in st.session_state:
    st.session_state.sites_cibles = pd.DataFrame({
        "Site": ["Welcome to the Jungle", "LinkedIn", "HelloWork", "Indeed"],
        "Actif": [True, True, True, False] # Case à cocher pour activer/désactiver
    })

if 'resultats' not in st.session_state:
    st.session_state.resultats = pd.DataFrame()

# --- FONCTION DE RECHERCHE (Simulée) ---
def lancer_recherche(criteres, sites):
    """
    C'est ici que tu placeras ton vrai code de scraping ou d'API.
    Pour l'instant, je simule une recherche pour te montrer le fonctionnement.
    """
    # On ne garde que les sites où "Actif" est True
    sites_actifs = sites[sites['Actif'] == True]['Site'].tolist()
    
    # Simulation d'un temps de recherche...
    with st.spinner(f"Recherche en cours sur {len(sites_actifs)} sites..."):
        time.sleep(2) # Remplace ça par ton vrai code
        
        # Données fictives générées à partir de tes critères
        donnees_trouvees = [
            {"Titre": "Stage Data Scientist", "Entreprise": "TechCorp", "Lieu": criteres['lieu'], "Durée": criteres['duree'], "Source": "Welcome to the Jungle", "Lien": "https://lien..."},
            {"Titre": f"Assistant(e) {criteres['secteur']}", "Entreprise": "InnovSect", "Lieu": f"À moins de {criteres['rayon']}km", "Durée": criteres['duree'], "Source": "LinkedIn", "Lien": "https://lien..."}
        ]
        return pd.DataFrame(donnees_trouvees)

# --- BARRE LATÉRALE : CRITÈRES DE RECHERCHE ---
with st.sidebar:
    st.header("⚙️ Critères de recherche")
    
    lieu = st.text_input("📍 Lieu", value="Paris")
    rayon = st.slider("📏 Rayon (en km)", min_value=0, max_value=100, value=10, step=5)
    duree = st.selectbox("⏱️ Durée du stage", ["4 mois", "6 mois", "Césure (1 an)"])
    secteur = st.text_input("🏢 Secteur de l'entreprise", value="Intelligence Artificielle")
    
    st.markdown("---")
    
    # Bouton principal qui déclenche la recherche
    if st.button("🚀 Rafraîchir les offres", use_container_width=True, type="primary"):
        criteres = {"lieu": lieu, "rayon": rayon, "duree": duree, "secteur": secteur}
        st.session_state.resultats = lancer_recherche(criteres, st.session_state.sites_cibles)

# --- ZONE PRINCIPALE ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🌐 Sites sources")
    st.info("Tu peux ajouter, modifier ou désactiver des sites directement dans ce tableau.")
    # Le composant magique data_editor permet de modifier le tableau directement sur l'interface !
    st.session_state.sites_cibles = st.data_editor(
        st.session_state.sites_cibles, 
        num_rows="dynamic", # Permet d'ajouter/supprimer des lignes
        use_container_width=True
    )

with col2:
    st.subheader("📋 Dernières offres trouvées")
    if st.session_state.resultats.empty:
        st.write("Aucune offre pour le moment. Remplis tes critères et clique sur 'Rafraîchir'.")
    else:
        # Affichage des résultats
        st.dataframe(
            st.session_state.resultats,
            column_config={
                "Lien": st.column_config.LinkColumn("Lien vers l'offre") # Transforme l'URL en lien cliquable
            },
            hide_index=True,
            use_container_width=True
        )