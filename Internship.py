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

# --- LA FONCTION DE RECHERCHE PROFONDE ---
def lancer_recherche(criteres, sites, zone_statut):
    offres_trouvees = []
    sites_actifs = sites[sites['Actif'] == True]['Site'].tolist()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    toutes_durees_possibles = ["2 mois", "2mois", "4 mois", "4mois", "6 mois", "6mois", "césure", "cesure"]
    duree_choisie = criteres['duree'].lower()
    
    mots_a_bannir = []
    if duree_choisie != "peu importe":
        duree_sans_espace = duree_choisie.replace(" ", "")
        for d in toutes_durees_possibles:
            if d != duree_choisie and d != duree_sans_espace and d.replace('é', 'e') != duree_choisie.replace('é', 'e'):
                mots_a_bannir.append(d)

    for site in sites_actifs:
        if site == "HelloWork":
            zone_statut.update(label=f"Recherche de la liste des offres sur {site}...", state="running")
            
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
                    
                    total_annonces = len(annonces)
                    annonces_valides = 0

                    for i, annonce in enumerate(annonces):
                        # Mise à jour visuelle pour l'utilisateur
                        zone_statut.update(label=f"Analyse approfondie : offre {i+1} sur {total_annonces}...", state="running")
                        
                        lien_tag = annonce.parent
                        
                        if lien_tag.name == 'a' and 'href' in lien_tag.attrs:
                            
                            # 1. Analyse de surface (pour éliminer vite les CDI évidents)
                            texte_carte = lien_tag.get_text(separator=' ').lower()
                            aria_label = lien_tag.get('aria-label', '').lower()
                            texte_surface = aria_label + " " + texte_carte
                            
                            if 'stage' not in texte_surface and 'intern' not in texte_surface:
                                continue 
                            
                            lien_complet = "https://www.hellowork.com" + lien_tag['href']
                            
                            # 2. ANALYSE PROFONDE (Deep Scraping)
                            try:
                                # On fait une petite pause de 0.2s pour ne pas se faire bloquer par le site
                                time.sleep(0.2)
                                reponse_detail = requests.get(lien_complet, headers=headers, timeout=5)
                                
                                if reponse_detail.status_code == 200:
                                    soup_detail = BeautifulSoup(reponse_detail.text, 'html.parser')
                                    # On récupère tout le texte de la page de l'offre
                                    texte_profond = soup_detail.get_text(separator=' ').lower()
                                    
                                    # Filtre d'exclusion sur le texte de la page ENTIÈRE
                                    contient_autre_duree = False
                                    for mot_banni in mots_a_bannir:
                                        if mot_banni in texte_profond:
                                            contient_autre_duree = True
                                            break 
                                    
                                    if contient_autre_duree:
                                        if duree_choisie != "peu importe" and (duree_choisie in texte_profond or duree_choisie.replace(" ", "") in texte_profond):
                                            pass # Tolérance si la bonne durée est aussi là
                                        else:
                                            continue # REJETÉ ! L'annonce contient une mauvaise durée cachée dans le corps du texte.
                                            
                            except Exception:
                                # Si la page refuse de s'ouvrir, on l'ignore par sécurité
                                continue
                            
                            # Si l'annonce a survécu à l'analyse profonde, on la garde !
                            p_titre = annonce.find('p', class_=lambda c: c and 'tw-typo-l' in c)
                            p_entreprise = annonce.find('p', class_=lambda c: c and 'tw-typo-s' in c)
                            
                            titre = p_titre.text.strip() if p_titre else annonce.text.strip()
                            entreprise = p_entreprise.text.strip() if p_entreprise else "Non précisé"
                            
                            if not any(offre['Lien'] == lien_complet for offre in offres_trouvees):
                                offres_trouvees.append({
                                    "Titre": titre,
                                    "Entreprise": entreprise,
                                    "Lieu": criteres['lieu'],
                                    "Durée": criteres['duree'] if criteres['duree'] != "Peu importe" else "Non filtrée",
                                    "Source": "HelloWork",
                                    "Lien": lien_complet
                                })
                                annonces_valides += 1
                                
            except Exception as e:
                st.error(f"Erreur technique sur {site} : {e}")
                
        elif site == "Welcome to the Jungle":
            pass

    zone_statut.update(label=f"Recherche terminée ! {len(offres_trouvees)} offres parfaites trouvées.", state="complete", expanded=False)
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
        
        # Utilisation d'un composant de statut pour voir l'avancement du Deep Scraping
        statut = st.status("Démarrage du radar...", expanded=True)
        
        st.session_state.resultats = lancer_recherche(criteres, st.session_state.sites_cibles, statut)
            
        if not st.session_state.resultats.empty:
            st.success("Tableau mis à jour avec succès.")
        else:
            st.warning("Aucun stage trouvé avec ces critères après l'analyse profonde.")

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
