import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random

# --- IMPORT SELENIUM ---
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Radar à Stages Ultimate", page_icon="🎯", layout="wide")
st.title("🎯 Radar à Stages : Hybride (Requests + Selenium)")

# --- FONCTION POUR CONFIGURER SELENIUM SUR STREAMLIT CLOUD ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # OBLIGATOIRE sur le Cloud (pas d'écran)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Astuce pour être moins détectable par Indeed
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    return webdriver.Chrome(options=chrome_options)

# --- INITIALISATION ---
if 'sites_cibles' not in st.session_state:
    st.session_state.sites_cibles = pd.DataFrame({
        "Site": ["HelloWork", "LinkedIn", "Welcome to the Jungle", "Indeed"],
        "Actif": [True, True, False, False] # Active WTTJ/Indeed avec prudence
    })

if 'resultats' not in st.session_state:
    st.session_state.resultats = pd.DataFrame()

# --- FONCTION DE VALIDATION (FILTRES) ---
def est_valide(texte_complet, duree_choisie, mots_a_bannir):
    texte = texte_complet.lower()
    if 'stage' not in texte and 'intern' not in texte: return False
    
    contient_interdit = False
    for mot in mots_a_bannir:
        if mot in texte:
            contient_interdit = True
            break
            
    if contient_interdit:
        if duree_choisie != "peu importe" and (duree_choisie in texte or duree_choisie.replace(" ", "") in texte):
            return True 
        else:
            return False
    return True

# --- MOTEUR DE RECHERCHE ---
def lancer_recherche(criteres, sites, zone_statut):
    offres_trouvees = []
    sites_actifs = sites[sites['Actif'] == True]['Site'].tolist()
    
    # Préparation filtres
    toutes_durees = ["2 mois", "2mois", "4 mois", "4mois", "6 mois", "6mois", "césure", "cesure"]
    duree_choisie = criteres['duree'].lower()
    mots_a_bannir = [d for d in toutes_durees if d != duree_choisie and d.replace(' ','') != duree_choisie.replace(' ','')] if duree_choisie != "peu importe" else []

    driver = None # On n'allume Selenium que si nécessaire

    for site in sites_actifs:
        try:
            # ================= MODE RAPIDE (REQUESTS) =================
            if site in ["HelloWork", "LinkedIn"]:
                zone_statut.update(label=f"🚀 Recherche rapide sur {site}...", state="running")
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                
                url = ""
                if site == "HelloWork":
                    mots = f"Stage {criteres['secteur']} {criteres['duree'] if criteres['duree'] != 'Peu importe' else ''}"
                    url = f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={mots.replace(' ','+')}&l={criteres['lieu'].replace(' ','+')}&ray={criteres['rayon']}"
                elif site == "LinkedIn":
                    mots = f"Stage {criteres['secteur']}"
                    url = f"https://fr.linkedin.com/jobs/search?keywords={mots.replace(' ','%20')}&location={criteres['lieu']}"

                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    items = []
                    if site == "HelloWork": items = soup.find_all('h3')
                    elif site == "LinkedIn": items = soup.find_all('li')

                    for item in items:
                        titre, ent, lien = "", "", ""
                        if site == "HelloWork":
                            if item.parent.name == 'a':
                                lien = "https://www.hellowork.com" + item.parent['href']
                                titre = item.text.strip()
                                ent = "Voir annonce" # Simplifié pour la vitesse
                        elif site == "LinkedIn":
                            a_tag = item.find('a', class_='base-card__full-link')
                            if a_tag:
                                lien = a_tag['href']
                                titre = item.find('h3', class_='base-search-card__title').text.strip()
                                ent = item.find('h4', class_='base-search-card__subtitle').text.strip()
                        
                        if titre and est_valide(titre, duree_choisie, mots_a_bannir):
                            offres_trouvees.append({"Titre": titre, "Entreprise": ent, "Source": site, "Lien": lien})

            # ================= MODE LOURD (SELENIUM) =================
            elif site in ["Welcome to the Jungle", "Indeed"]:
                zone_statut.update(label=f"🐢 Démarrage du navigateur pour {site} (Ça peut être long)...", state="running")
                
                if driver is None:
                    driver = get_driver() # On lance Chrome une seule fois

                if site == "Welcome to the Jungle":
                    mots = f"Stage {criteres['secteur']}"
                    # URL API directe WTTJ souvent plus efficace, mais ici on tente le front
                    url = f"https://www.welcometothejungle.com/fr/jobs?aroundQuery={criteres['lieu']}&query={mots.replace(' ','%20')}"
                    driver.get(url)
                    time.sleep(5) # Attente chargement JS
                    
                    # On récupère le HTML généré par le JS et on le parse avec BS4 (plus rapide)
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    articles = soup.find_all('li', class_=lambda x: x and 'ais-Hits-item' in x)
                    
                    for art in articles:
                        titre_tag = art.find('h4')
                        lien_tag = art.find('a')
                        if titre_tag and lien_tag:
                            lien = "https://www.welcometothejungle.com" + lien_tag['href']
                            if est_valide(titre_tag.text, duree_choisie, mots_a_bannir):
                                offres_trouvees.append({"Titre": titre_tag.text, "Entreprise": "WTTJ", "Source": "WTTJ", "Lien": lien})

                elif site == "Indeed":
                    mots = f"Stage {criteres['secteur']}"
                    url = f"https://fr.indeed.com/jobs?q={mots.replace(' ','+')}&l={criteres['lieu'].replace(' ','+')}"
                    driver.get(url)
                    
                    # Tentative de contournement Cloudflare
                    time.sleep(random.uniform(3, 6)) 
                    
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    # Sélecteurs Indeed (changent souvent)
                    cartes = soup.find_all('td', class_='resultContent')
                    
                    if not cartes: # Si vide, Indeed a peut-être bloqué
                        st.warning("Indeed a probablement bloqué l'accès (Captcha détecté).")

                    for carte in cartes:
                        titre_elem = carte.find('h2', class_='jobTitle')
                        if titre_elem:
                            lien_elem = titre_elem.find('a')
                            if lien_elem:
                                lien = "https://fr.indeed.com" + lien_elem['href']
                                titre = titre_elem.text.strip()
                                if est_valide(titre, duree_choisie, mots_a_bannir):
                                    offres_trouvees.append({"Titre": titre, "Entreprise": "Indeed", "Source": "Indeed", "Lien": lien})

        except Exception as e:
            st.error(f"Erreur sur {site}: {e}")

    # Nettoyage : On ferme Chrome à la fin
    if driver:
        driver.quit()

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
    
    if not st.session_state.resultats.empty:
        csv = st.session_state.resultats.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger CSV", data=csv, file_name="stages.csv", mime="text/csv")

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
        st.info("Aucun résultat.")
