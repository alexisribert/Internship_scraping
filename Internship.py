import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Radar à Stages", page_icon="🎯", layout="wide")
st.title("🎯 Radar à Stages Multi-Sites")

# --- INITIALISATION DES VARIABLES ---
if 'sites_cibles' not in st.session_state:
    st.session_state.sites_cibles = pd.DataFrame({
        "Site": ["HelloWork", "Welcome to the Jungle", "Indeed", "LinkedIn"],
        "Actif": [True, True, False, False] # WTTJ activé pour tester
    })

if 'resultats' not in st.session_state:
    st.session_state.resultats = pd.DataFrame()

# --- FONCTIONS UTILITAIRES ---
def get_random_header():
    # On fait tourner les User-Agents pour tromper (un peu) les défenses
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0'
    ]
    return {'User-Agent': random.choice(user_agents)}

def est_valide(texte_complet, duree_choisie, mots_a_bannir):
    """Fonction centralisée pour valider une annonce selon les règles strictes"""
    texte = texte_complet.lower()
    
    # 1. Filtre de base : Est-ce un stage ?
    if 'stage' not in texte and 'intern' not in texte:
        return False
        
    # 2. Filtre d'exclusion (Liste noire)
    contient_interdit = False
    for mot in mots_a_bannir:
        if mot in texte:
            contient_interdit = True
            break
            
    # 3. Règle de tolérance
    if contient_interdit:
        if duree_choisie != "peu importe" and (duree_choisie in texte or duree_choisie.replace(" ", "") in texte):
            return True # Sauvé par la tolérance
        else:
            return False # Rejeté
            
    return True

# --- LA FONCTION DE RECHERCHE ---
def lancer_recherche(criteres, sites, zone_statut):
    offres_trouvees = []
    sites_actifs = sites[sites['Actif'] == True]['Site'].tolist()
    
    # Préparation de la liste noire
    toutes_durees = ["2 mois", "2mois", "4 mois", "4mois", "6 mois", "6mois", "césure", "cesure"]
    duree_choisie = criteres['duree'].lower()
    mots_a_bannir = []
    if duree_choisie != "peu importe":
        ds = duree_choisie.replace(" ", "")
        mots_a_bannir = [d for d in toutes_durees if d != duree_choisie and d != ds and d.replace('é','e') != duree_choisie.replace('é','e')]

    for site in sites_actifs:
        zone_statut.update(label=f"Interrogation de {site}...", state="running")
        headers = get_random_header()
        
        try:
            # ================= HELLOWORK =================
            if site == "HelloWork":
                mots = f"Stage {criteres['secteur']} {criteres['duree'] if criteres['duree'] != 'Peu importe' else ''}"
                url = f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={mots.replace(' ','+')}&l={criteres['lieu'].replace(' ','+')}&ray={criteres['rayon']}"
                
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    annonces = soup.find_all('h3')
                    
                    for i, annonce in enumerate(annonces):
                        lien_tag = annonce.parent
                        if lien_tag.name == 'a' and 'href' in lien_tag.attrs:
                            texte_surface = (lien_tag.get('aria-label', '') + " " + lien_tag.get_text(separator=' ')).lower()
                            
                            # Pré-filtrage rapide
                            if 'stage' not in texte_surface and 'intern' not in texte_surface: continue

                            lien = "https://www.hellowork.com" + lien_tag['href']
                            
                            # Deep Scraping
                            time.sleep(0.2)
                            try:
                                r_det = requests.get(lien, headers=headers, timeout=5)
                                if r_det.status_code == 200:
                                    txt_full = BeautifulSoup(r_det.text, 'html.parser').get_text(separator=' ')
                                    if est_valide(txt_full, duree_choisie, mots_a_bannir):
                                        p_titre = annonce.find('p', class_=lambda c: c and 'tw-typo-l' in c)
                                        p_ent = annonce.find('p', class_=lambda c: c and 'tw-typo-s' in c)
                                        offres_trouvees.append({
                                            "Titre": p_titre.text.strip() if p_titre else annonce.text.strip(),
                                            "Entreprise": p_ent.text.strip() if p_ent else "Non précisé",
                                            "Source": "HelloWork",
                                            "Lien": lien
                                        })
                            except: continue

            # ================= WELCOME TO THE JUNGLE =================
            elif site == "Welcome to the Jungle":
                # WTTJ est complexe. On utilise leur URL de recherche classique.
                # Note : WTTJ utilise beaucoup de JS, BeautifulSoup peut ne rien trouver si le rendu est client-side.
                mots = f"Stage {criteres['secteur']}"
                url = f"https://www.welcometothejungle.com/fr/jobs?aroundQuery={criteres['lieu']}&page=1&query={mots.replace(' ','%20')}"
                
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # WTTJ change souvent ses classes. On cherche les balises 'ol' (liste) puis 'li'
                    # Cette partie est fragile et peut casser si WTTJ change son HTML
                    articles = soup.find_all('li', class_=lambda x: x and 'ais-Hits-item' in x)
                    
                    # Si la classe spécifique échoue, on tente une recherche plus large
                    if not articles:
                        articles = soup.find_all('article')

                    for i, art in enumerate(articles):
                        zone_statut.update(label=f"WTTJ : Analyse offre {i+1}...", state="running")
                        
                        titre_tag = art.find('h4') # Souvent h4 sur WTTJ
                        if not titre_tag: titre_tag = art.find('h3')
                        
                        lien_tag = art.find('a')
                        
                        if titre_tag and lien_tag:
                            lien = "https://www.welcometothejungle.com" + lien_tag['href']
                            
                            # Deep Scraping (Nécessaire car la carte donne peu d'infos)
                            time.sleep(0.5) # Pause plus longue pour WTTJ
                            try:
                                r_det = requests.get(lien, headers=headers, timeout=5)
                                if r_det.status_code == 200:
                                    txt_full = BeautifulSoup(r_det.text, 'html.parser').get_text(separator=' ')
                                    if est_valide(txt_full, duree_choisie, mots_a_bannir):
                                        ent_tag = art.find('span', class_='sc-erbPQA') # Classe très variable
                                        ent = ent_tag.text.strip() if ent_tag else "Voir lien"
                                        
                                        offres_trouvees.append({
                                            "Titre": titre_tag.text.strip(),
                                            "Entreprise": ent,
                                            "Source": "WTTJ",
                                            "Lien": lien
                                        })
                            except: continue
                else:
                    st.error(f"WTTJ a bloqué la requête (Code {resp.status_code}).")

            # ================= INDEED (DIFFICILE) =================
            elif site == "Indeed":
                # Indeed bloque très vite les scripts Python.
                mots = f"Stage {criteres['secteur']}"
                url = f"https://fr.indeed.com/jobs?q={mots.replace(' ','+')}&l={criteres['lieu'].replace(' ','+')}"
                
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # Sélecteur commun pour les cartes Indeed
                    cartes = soup.find_all('td', class_='resultContent')
                    
                    for i, carte in enumerate(cartes):
                        zone_statut.update(label=f"Indeed : Analyse offre {i+1}...", state="running")
                        
                        titre_elem = carte.find('h2', class_='jobTitle')
                        lien_elem = titre_elem.find('a') if titre_elem else None
                        
                        if lien_elem:
                            lien = "https://fr.indeed.com" + lien_elem['href']
                            titre = titre_elem.text.strip()
                            ent_elem = carte.find('span', class_='companyName') # Ancienne classe
                            if not ent_elem: ent_elem = carte.find('span', {'data-testid': 'company-name'}) # Nouvelle
                            
                            # Indeed Deep Scraping est TRÈS risqué (blocage immédiat). 
                            # On se contente du titre pour l'instant ou on tente avec prudence.
                            # Pour cet exemple, on fait juste une vérification surface pour éviter le blocage.
                            if est_valide(titre, duree_choisie, mots_a_bannir):
                                offres_trouvees.append({
                                    "Titre": titre,
                                    "Entreprise": ent_elem.text.strip() if ent_elem else "Indeed",
                                    "Source": "Indeed",
                                    "Lien": lien
                                })
                else:
                    st.warning(f"Indeed a détecté le robot (Code {resp.status_code}). Réessaie plus tard.")

            # ================= LINKEDIN (EXTRÊME) =================
            elif site == "LinkedIn":
                # LinkedIn Public
                mots = f"Stage {criteres['secteur']}"
                url = f"https://fr.linkedin.com/jobs/search?keywords={mots.replace(' ','%20')}&location={criteres['lieu']}"
                
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    jobs = soup.find_all('li') # Structure très générique sur la page publique
                    
                    for job in jobs:
                        a_tag = job.find('a', class_='base-card__full-link')
                        if a_tag:
                            lien = a_tag['href']
                            titre = job.find('h3', class_='base-search-card__title').text.strip()
                            ent = job.find('h4', class_='base-search-card__subtitle').text.strip()
                            
                            # Pas de deep scraping sur LinkedIn sans login, c'est impossible.
                            # On filtre uniquement sur le titre.
                            if est_valide(titre, duree_choisie, mots_a_bannir):
                                offres_trouvees.append({
                                    "Titre": titre,
                                    "Entreprise": ent,
                                    "Source": "LinkedIn",
                                    "Lien": lien
                                })
                else:
                    st.warning("LinkedIn nécessite une connexion (AuthWall).")

        except Exception as e:
            st.error(f"Erreur sur {site}: {e}")
            
        time.sleep(1) # Pause entre les sites

    zone_statut.update(label=f"Terminé ! {len(offres_trouvees)} offres trouvées.", state="complete", expanded=False)
    return pd.DataFrame(offres_trouvees)


# --- UI ---
with st.sidebar:
    st.header("⚙️ Critères")
    lieu = st.text_input("📍 Lieu", value="Lille")
    rayon = st.slider("📏 Rayon (km)", 0, 100, 20)
    duree = st.selectbox("⏱️ Durée", ["Peu importe", "2 mois", "4 mois", "6 mois", "Césure"]) 
    secteur = st.text_input("🏢 Mot-clé", value="Data")
    
    st.markdown("---")
    
    if st.button("🚀 Lancer le Radar", type="primary"):
        criteres = {"lieu": lieu, "rayon": rayon, "duree": duree, "secteur": secteur}
        statut = st.status("Initialisation...", expanded=True)
        st.session_state.resultats = lancer_recherche(criteres, st.session_state.sites_cibles, statut)

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("🌐 Sources")
    st.session_state.sites_cibles = st.data_editor(st.session_state.sites_cibles, num_rows="dynamic")
    
    # Bouton Export CSV
    if not st.session_state.resultats.empty:
        csv = st.session_state.resultats.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger en CSV", data=csv, file_name="mes_stages.csv", mime="text/csv")

with col2:
    st.subheader("📋 Résultats")
    if not st.session_state.resultats.empty:
        st.dataframe(
            st.session_state.resultats,
            column_config={"Lien": st.column_config.LinkColumn("Voir l'offre")},
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Aucun résultat. Si Indeed/LinkedIn sont vides, c'est souvent à cause de leurs protections anti-bots.")
