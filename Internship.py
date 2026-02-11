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

    # Liste étendue pour attraper toutes les variations d'écriture
    toutes_durees_possibles = ["2 mois", "2mois", "4 mois", "4mois", "6 mois", "6mois", "césure", "cesure"]
    duree_choisie = criteres['duree'].lower()
    
    # Création de la liste noire en excluant la durée choisie (et sa version sans espace)
    mots_a_bannir = []
    if duree_choisie != "peu importe":
        duree_sans_espace = duree_choisie.replace(" ", "")
        for d in toutes_durees_possibles:
            if d != duree_choisie and d != duree_sans_espace and d.replace('é', 'e') != duree_choisie.replace('é', 'e'):
                mots_a_bannir.append(d)

    for site in sites_actifs:
        if site == "HelloWork":
            # On force le mot "Stage" et la durée directement dans les mots-clés
            mots_cles = f"Stage {criteres['secteur']}"
            if criteres['duree'] != "Peu importe":
                mots_cles += f" {criteres['duree']}"
                
            mot_cle_url = mots_cles.replace(' ', '+')
            lieu_url = criteres['lieu'].replace(' ', '+')
            
            url = f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={mot_cle_url}&l={lieu_url}&ray={criteres['rayon']}"
            
            try:
                reponse = requests.get(url, headers=headers, timeout=10)
                
                if reponse.status_code == 200:
                    soup = BeautifulSoup(reponse.text, 'html.parser')
                    annonces = soup.find_all('h3')

                    for annonce in annonces:
                        lien_tag = annonce.parent
                        
                        if lien_tag.name == 'a' and 'href' in lien_tag.attrs:
                            
                            # CORRECTIF MAJEUR : On lit MAINTENANT tout le texte de la carte d'annonce !
                            # get_text(separator=' ') permet d'éviter que deux mots se collent
                            texte_carte = lien_tag.get_text(separator=' ').lower()
                            aria_label = lien_tag.get('aria-label', '').lower()
                            
                            # On fusionne tout le texte visible et caché pour le scan
                            texte_complet_annonce = aria_label + " " + texte_carte
                            
                            # Filtre Anti-CDI
                            if 'stage' not in texte_complet_annonce and 'intern' not in texte_complet_annonce:
                                continue 
                            
                            # Filtre d'exclusion des autres durées
                            contient_autre_duree = False
                            for mot_banni in mots_a_bannir:
                                if mot_banni in texte_complet_annonce:
                                    contient_autre_duree = True
                                    break 
                            
                            # Règle de tolérance : Si une mauvaise durée est trouvée, on vérifie si la bonne y est aussi
                            if contient_autre_duree:
                                if duree_choisie != "peu importe" and (duree_choisie in texte_complet_annonce or duree_choisie.replace(" ", "") in texte_complet_annonce):
                                    # Les deux sont là (ex: "Stage 2 à 6 mois"), on garde !
                                    pass
                                else:
                                    # C'est bel et bien une mauvaise durée, on rejette.
                                    continue
                            
                            # Extraction propre des infos pour l'affichage
                            p_titre = annonce.find('p', class_=lambda c: c and 'tw-typo-l' in c)
                            p_entreprise = annonce.find('p', class_=lambda c: c and 'tw-typo-s' in c)
                            
                            titre = p_titre.text.strip() if p_titre else annonce.text.strip()
                            entreprise = p_entreprise.text.strip() if p_entreprise else "Non précisé"
                            
                            lien_complet = "https://www.hellowork.com" + lien_tag['href']
                            
                            if not any(offre['Lien'] == lien_complet for offre in offres_trouvees):
                                offres_trouvees.append({
                                    "Titre": titre,
                                    "Entreprise": entreprise,
                                    "Lieu": criteres['lieu'],
                                    "Durée": criteres['duree'] if criteres['duree'] != "Peu importe" else "Non filtrée",
                                    "Source": "HelloWork",
                                    "Lien": lien_complet
                                })
                                
            except Exception as e:
                st.error(f"Erreur technique sur {site} : {e}")
                
        elif site == "Welcome to the Jungle":
            pass

        time.sleep(1) 

    return pd.DataFrame(offres_trouvees)


# --- BARRE LATÉRALE : CRITÈRES DE RECHERCHE ---
with st.sidebar:
    st.header("⚙️ Critères de recherche")
    
    lieu = st.text_input("📍 Lieu", value="Lille")
    rayon = st.slider("📏 Rayon (en km)", min_value=0, max_value=50, value=30, step=5)
    duree = st.selectbox("⏱️ Durée du stage", ["Peu importe", "2 mois", "4 mois", "6 mois", "Césure"]) 
    secteur = st.text_input("🏢 Secteur / Mot-clé", value="Ingénieur")
    
    st.markdown("---")
    
    if st.button("🚀 Rafraîchir les offres", use_container_width=True, type="primary"):
        criteres = {"lieu": lieu, "rayon": rayon, "duree": duree, "secteur": secteur}
        
        with st.spinner("Recherche et filtrage intraitable en cours... 🕵️‍♂️"):
            st.session_state.resultats = lancer_recherche(criteres, st.session_state.sites_cibles)
            
        if not st.session_state.resultats.empty:
            st.success(f"Bingo ! {len(st.session_state.resultats)} stages trouvés.")
        else:
            st.warning("Aucun stage trouvé avec ces critères précis.")

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
