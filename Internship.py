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
        "Actif": [True, False, False] # Seul HelloWork est actif par défaut
    })

if 'resultats' not in st.session_state:
    st.session_state.resultats = pd.DataFrame()

# --- LA FONCTION DE RECHERCHE (AVEC OUTILS DE DIAGNOSTIC) ---
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
                # --- BLOC DE DIAGNOSTIC ---
                st.info(f"🔍 URL cherchée : {url}")
                
                reponse = requests.get(url, headers=headers, timeout=10)
                
                st.write(f"📡 Code de réponse du serveur : {reponse.status_code}")
                
                if reponse.status_code == 200:
                    soup = BeautifulSoup(reponse.text, 'html.parser')
                    
                    annonces = soup.find_all('h3')
                    st.write(f"🏷️ Nombre de balises <h3> trouvées : {len(annonces)}")
                    
                    with st.expander("Voir les 500 premiers caractères du code source brut (Sert à repérer les protections Anti-Bot)"):
                        st.code(reponse.text[:500])

                    for annonce in annonces:
                        lien_tag = annonce.find('a')
                        if lien_tag and 'href' in lien_tag.attrs:
                            titre = lien_tag.text.strip()
                            lien_complet = "https://www.hellowork.com" + lien_tag['href']
                            
                            offres_trouvees.append({
                                "Titre": titre,
                                "Entreprise": "Non précisé",
                                "Lieu": criteres['lieu'],
                                "Source": "HelloWork",
                                "Lien": lien_complet
                            })
                else:
                    st.error(f"Le site a refusé la connexion. Code d'erreur HTTP : {reponse.status_code}")
                # --- FIN DU BLOC DE DIAGNOSTIC ---
                            
            except Exception as e:
                st.error(f"Erreur technique sur {site} : {e}")
                
        elif site == "Welcome to the Jungle":
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
        
        # Lancement de la recherche au clic
        st.session_state.resultats = lancer_recherche(criteres, st.session_state.sites_cibles)
            
        if not st.session_state.resultats.empty:
            st.success(f"{len(st.session_state.resultats)} offres trouvées !")
        else:
            st.warning("Aucune offre trouvée avec ces critères.")

# --- ZONE PRINCIPALE ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🌐 Sites sources")
    st.info("Coche les sites à fouiller. Actuellement, seul HelloWork est codé.")
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
                "Lien": st.column_config.LinkColumn("Lien vers l'offre (Clique ici)")
            },
            hide_index=True,
            use_container_width=True
        )
