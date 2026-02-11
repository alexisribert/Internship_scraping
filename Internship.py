import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Radar à Stages", page_icon="🎯", layout="wide")
st.title("🎯 Radar à Stages")

# --- INITIALISATION DES VARIABLES ---
if 'sites_cibles' not in st.session_state:
    st.session_state.sites_cibles = pd.DataFrame({
        "Site": ["HelloWork", "Welcome to the Jungle", "LinkedIn"],
        "Actif": [True, False, False]
    })

if 'resultats' not in st.session_state:
    st.session_state.resultats = pd.DataFrame()

# --- LA FONCTION DE RECHERCHE ---
def lancer_recherche(criteres, sites):
    offres_trouvees = []
    sites_actifs = sites[sites['Actif'] == True]['Site'].tolist()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for site in sites_actifs:
        if site == "HelloWork":
            mot_cle = criteres['secteur'].replace(' ', '+')
            lieu = criteres['lieu'].replace(' ', '+')
            url = f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={mot_cle}&l={lieu}&ray={criteres['rayon']}&ty=13"
            
            try:
                reponse = requests.get(url, headers=headers, timeout=10)
                
                if reponse.status_code == 200:
                    soup = BeautifulSoup(reponse.text, 'html.parser')
                    
                    annonces = soup.find_all('h3')

                    for annonce in annonces:
                        # LE CORRECTIF EST ICI : On vérifie si le parent du <h3> est un lien <a>
                        lien_tag = annonce.parent
                        
                        if lien_tag.name == 'a' and 'href' in lien_tag.attrs:
                            
                            # Extraction plus intelligente : on cherche les sous-balises <p>
                            # Le titre a généralement la classe 'tw-typo-l' et l'entreprise 'tw-typo-s'
                            p_titre = annonce.find('p', class_=lambda c: c and 'tw-typo-l' in c)
                            p_entreprise = annonce.find('p', class_=lambda c: c and 'tw-typo-s' in c)
                            
                            titre = p_titre.text.strip() if p_titre else annonce.text.strip()
                            entreprise = p_entreprise.text.strip() if p_entreprise else "Non précisé"
                            
                            lien_complet = "https://www.hellowork.com" + lien_tag['href']
                            
                            # Sécurité anti-doublons (Le code HTML de HelloWork affiche parfois le h3 en double)
                            if not any(offre['Lien'] == lien_complet for offre in offres_trouvees):
                                offres_trouvees.append({
                                    "Titre": titre,
                                    "Entreprise": entreprise,
                                    "Lieu": criteres['lieu'],
                                    "Source": "HelloWork",
                                    "Lien": lien_complet
                                })
                                
            except Exception as e:
                st.error(f"Erreur technique sur {site} : {e}")
                
        elif site == "Welcome to the Jungle":
            # API Welcome to the jungle à coder plus tard
            pass

        time.sleep(1) 

    return pd.DataFrame(offres_trouvees)


# --- BARRE LATÉRALE : CRITÈRES DE RECHERCHE ---
with st.sidebar:
    st.header("⚙️ Critères de recherche")
    
    lieu = st.text_input("📍 Lieu", value="Paris")
    rayon = st.slider("📏 Rayon (en km)", min_value=0, max_value=50, value=15, step=5)
    duree = st.selectbox("⏱️ Durée du stage", ["Peu importe", "4 mois", "6 mois"]) 
    secteur = st.text_input("🏢 Secteur / Mot-clé", value="Data")
    
    st.markdown("---")
    
    if st.button("🚀 Rafraîchir les offres", use_container_width=True, type="primary"):
        criteres = {"lieu": lieu, "rayon": rayon, "duree": duree, "secteur": secteur}
        
        # On remet l'animation visuelle de chargement
        with st.spinner("Recherche et extraction en cours... 🕵️‍♂️"):
            st.session_state.resultats = lancer_recherche(criteres, st.session_state.sites_cibles)
            
        if not st.session_state.resultats.empty:
            st.success(f"Bingo ! {len(st.session_state.resultats)} offres trouvées.")
        else:
            st.warning("Aucune offre trouvée avec ces critères.")

# --- ZONE PRINCIPALE ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🌐 Sites sources")
    st.info("Coche les sites à fouiller. (HelloWork = OK ✅)")
    st.session_state.sites_cibles = st.data_editor(
        st.session_state.sites_cibles, 
        num_rows="dynamic",
        use_container_width=True
    )

with col2:
    st.subheader("📋 Dernières offres trouvées")
    if st.session_state.resultats.empty:
        st.write("Aucune offre pour le moment. Remplis tes critères et clique sur 'Rafraîchir'.")
    else:
        st.dataframe(
            st.session_state.resultats,
            column_config={
                "Lien": st.column_config.LinkColumn("Postuler (Clique ici)")
            },
            hide_index=True,
            use_container_width=True
        )
