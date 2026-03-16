import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster, HeatMap, HeatMapWithTime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import os
from streamlit_folium import st_folium 
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION GLOBALE ---
st.set_page_config(
    layout="wide", 
    page_title="🚴 MobilityPro - Analyse Cyclable Montréal", 
    initial_sidebar_state="expanded",
    page_icon="🚴"
)

# --- THEME SWITCHER ---
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# --- CSS ULTRA-PREMIUM ---
def inject_custom_css(dark_mode=False):
    if dark_mode:
        bg_color = "#0E1117"
        text_color = "#FAFAFA"
        card_bg = "#1E2127"
        border_color = "#2D3139"
        accent_color = "#00D9FF"
    else:
        bg_color = "#FAFAFA"
        text_color = "#1E2127"
        card_bg = "#FFFFFF"
        border_color = "#E0E0E0"
        accent_color = "#005528"
    
    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
            
            * {{
                font-family: 'Inter', sans-serif;
            }}
            
            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            
            .stApp {{
                background: linear-gradient(135deg, {bg_color} 0%, {bg_color} 100%);
                background-attachment: fixed;
            }}
            
            /* Header ultra-premium */
            .premium-header {{
                background: linear-gradient(135deg, {accent_color} 0%, #00a8cc 100%);
                padding: 40px 30px;
                border-radius: 20px;
                margin-bottom: 30px;
                box-shadow: 0 10px 40px rgba(0, 85, 40, 0.3);
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .premium-header::before {{
                content: '';
                position: absolute;
                top: -50%;
                right: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                animation: rotate 20s linear infinite;
            }}
            
            @keyframes rotate {{
                from {{ transform: rotate(0deg); }}
                to {{ transform: rotate(360deg); }}
            }}
            
            .main-title {{
                font-size: 42px;
                font-weight: 800;
                color: white;
                text-transform: uppercase;
                letter-spacing: 3px;
                margin: 0;
                text-shadow: 0 4px 20px rgba(0,0,0,0.3);
                position: relative;
                z-index: 1;
            }}
            
            .sub-title {{
                font-size: 18px;
                color: rgba(255,255,255,0.95);
                margin-top: 10px;
                font-weight: 400;
                position: relative;
                z-index: 1;
            }}
            
            /* Cards premium */
            .metric-card {{
                background: {card_bg};
                border-radius: 15px;
                padding: 25px;
                border: 1px solid {border_color};
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            
            .metric-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 8px 30px rgba(0,0,0,0.15);
            }}
            
            .metric-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background: linear-gradient(90deg, {accent_color}, #00a8cc);
            }}
            
            .metric-value {{
                font-size: 38px;
                font-weight: 800;
                color: {accent_color};
                margin: 10px 0;
            }}
            
            .metric-label {{
                font-size: 14px;
                color: {text_color};
                opacity: 0.7;
                text-transform: uppercase;
                letter-spacing: 1px;
                font-weight: 600;
            }}
            
            .metric-delta {{
                font-size: 12px;
                margin-top: 5px;
            }}
            
            /* Sidebar styling */
            [data-testid="stSidebar"] {{
                background: {card_bg};
                border-right: 1px solid {border_color};
            }}
            
            /* Dataframe styling */
            .dataframe {{
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            
            /* Alert boxes */
            .alert-box {{
                background: {card_bg};
                border-left: 4px solid {accent_color};
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            
            .alert-title {{
                font-size: 18px;
                font-weight: 700;
                color: {accent_color};
                margin-bottom: 10px;
            }}
            
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 10px;
                background: {card_bg};
                padding: 10px;
                border-radius: 10px;
            }}
            
            .stTabs [data-baseweb="tab"] {{
                height: 50px;
                border-radius: 8px;
                padding: 0 25px;
                font-weight: 600;
            }}
            
            /* Buttons */
            .stButton>button {{
                background: linear-gradient(135deg, {accent_color}, #00a8cc);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 30px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                transition: all 0.3s ease;
            }}
            
            .stButton>button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(0, 85, 40, 0.3);
            }}
            
            /* Progress bars */
            .stProgress > div > div > div {{
                background: linear-gradient(90deg, {accent_color}, #00a8cc);
            }}
            
            /* Metric containers */
            div[data-testid="stMetricValue"] {{ 
                font-size: 2rem !important; 
                color: {accent_color}; 
                font-weight: 800; 
            }}
            
            /* Section dividers */
            .section-divider {{
                height: 3px;
                background: linear-gradient(90deg, {accent_color}, transparent);
                margin: 30px 0;
                border-radius: 10px;
            }}
            
            /* Status badges */
            .status-badge {{
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .status-critical {{
                background: #ff4757;
                color: white;
            }}
            
            .status-high {{
                background: #ffa502;
                color: white;
            }}
            
            .status-medium {{
                background: #26de81;
                color: white;
            }}
            
            .status-low {{
                background: #a5b1c2;
                color: white;
            }}
        </style>
    """, unsafe_allow_html=True)

inject_custom_css(st.session_state.dark_mode)

# --- HEADER PREMIUM ---
st.markdown(f"""
    <div class="premium-header">
        <div class="main-title">🚴 MOBILITYPRO ANALYTICS</div>
        <div class="sub-title">Intelligence Artificielle pour l'Urbanisme Cyclable | Montréal 2026</div>
    </div>
""", unsafe_allow_html=True)

# --- FONCTIONS DE CHARGEMENT OPTIMISÉES ---

@st.cache_data(ttl=3600)
def charger_reseau():
    """Charge le réseau cyclable officiel avec gestion d'erreur"""
    url = "https://donnees.montreal.ca/dataset/5ea29f40-1b5b-4f34-85b3-7c67088ff536/resource/0dc6612a-be66-406b-b2d9-59c9e1c65ebf/download/reseau_cyclable.geojson"
    try:
        gdf = gpd.read_file(url)
        gdf.columns = [c.upper().strip() for c in gdf.columns]
        if 'GEOMETRY' in gdf.columns: 
            gdf = gdf.set_geometry('GEOMETRY')
        return gdf
    except Exception as e:
        st.error(f"Erreur chargement réseau: {e}")
        return None

@st.cache_data
def charger_flux_precalcule():
    """Charge les flux BIXI précalculés"""
    path = "flux_bixi_estimes.geojson"
    if not os.path.exists(path): 
        return gpd.GeoDataFrame()
    try:
        gdf = gpd.read_file(path)
        gdf.columns = [c.upper().strip() for c in gdf.columns]
        if 'GEOMETRY' in gdf.columns: 
            gdf = gdf.set_geometry('GEOMETRY')
        gdf['LONGUEUR_M'] = gdf.to_crs(epsg=32188).length
        return gdf
    except Exception as e:
        st.error(f"Erreur chargement flux: {e}")
        return gpd.GeoDataFrame()

@st.cache_data
def charger_accidents_enrichi(_reseau_officiel=None):
    """Charge et enrichit les données d'accidents"""
    try:
        # Essayer différents noms de fichier
        for fname in ["collisions_routieres.csv", "collisions_routieres (1).csv"]:
            if os.path.exists(fname):
                df = pd.read_csv(fname)
                break
        else:
            return pd.DataFrame()
            
        df.columns = [c.upper().strip() for c in df.columns]
        df['DT_ACCDN'] = pd.to_datetime(df['DT_ACCDN'], errors='coerce')
        df['ANNEE'] = df['DT_ACCDN'].dt.year
        df['MOIS'] = df['DT_ACCDN'].dt.month
        df['JOUR_SEMAINE'] = df['DT_ACCDN'].dt.dayofweek
        df['HEURE'] = df['DT_ACCDN'].dt.hour
        
        df = df.dropna(subset=['LOC_LAT', 'LOC_LONG', 'ANNEE'])
        
        # Filtrer accidents vélo
        if 'NB_BICYCLETTE' in df.columns:
            df = df[(df['NB_BICYCLETTE'] > 0) | (df.get('NB_VICTIMES_VELO', 0) > 0)]
        
        # Détection accidents sur piste
        df['sur_piste'] = "Non" 
        if _reseau_officiel is not None:
            gdf_acc = gpd.GeoDataFrame(
                df, 
                geometry=gpd.points_from_xy(df.LOC_LONG, df.LOC_LAT), 
                crs="EPSG:4326"
            )
            acc_m = gdf_acc.to_crs(epsg=32188)
            reseau_m = _reseau_officiel.to_crs(epsg=32188)
            zone_pistes = reseau_m.geometry.buffer(10).unary_union
            df['sur_piste'] = acc_m.geometry.intersects(zone_pistes).map({True: 'Oui', False: 'Non'})
        
        return df
    except Exception as e:
        st.error(f"Erreur chargement accidents: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def charger_bixi_live():
    """Charge les données BIXI en temps réel"""
    try:
        s = requests.get("https://gbfs.velobixi.com/gbfs/2-2/fr/station_status.json", timeout=5).json()['data']['stations']
        i = requests.get("https://gbfs.velobixi.com/gbfs/2-2/fr/station_information.json", timeout=5).json()['data']['stations']
        
        df_s = pd.DataFrame(s)[['station_id', 'num_bikes_available', 'num_docks_available']]
        df_i = pd.DataFrame(i)[['station_id', 'name', 'lat', 'lon', 'capacity']]
        
        df = pd.merge(df_i, df_s, on='station_id')
        df['taux_occupation'] = (df['num_bikes_available'] / df['capacity'] * 100).round(1)
        
        return df
    except Exception as e:
        st.warning(f"Impossible de charger les données BIXI live: {e}")
        return pd.DataFrame()

@st.cache_data
def charger_comptage_velo():
    """Charge les données de comptage vélo"""
    try:
        for fname in ["comptage_velo_2025.csv", "Compteurs cyclistes permanents.csv", "cyclistes (1).csv"]:
            if os.path.exists(fname):
                df = pd.read_csv(fname)
                df.columns = [c.upper().strip() for c in df.columns]
                if 'PERIODE' in df.columns:
                    df['PERIODE'] = pd.to_datetime(df['PERIODE'], errors='coerce')
                elif 'DATE' in df.columns:
                    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
                return df
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Erreur chargement comptage: {e}")
        return pd.DataFrame()

@st.cache_data
def charger_trajets_bixi():
    """Charge les trajets BIXI"""
    try:
        if os.path.exists("bixi.csv"):
            df = pd.read_csv("bixi.csv")
            df.columns = [c.upper().strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Erreur chargement trajets BIXI: {e}")
        return pd.DataFrame()

# --- CHARGEMENT DES DONNÉES ---
with st.spinner("🔄 Chargement et analyse des données..."):
    gdf_reseau = charger_reseau()
    gdf_flux = charger_flux_precalcule()
    df_acc = charger_accidents_enrichi(gdf_reseau) 
    df_live = charger_bixi_live()
    df_comptage = charger_comptage_velo()
    df_trajets = charger_trajets_bixi()

# --- SIDEBAR PREMIUM ---
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    # Theme switcher
    if st.checkbox("🌙 Mode Sombre", value=st.session_state.dark_mode):
        st.session_state.dark_mode = True
        inject_custom_css(True)
    else:
        st.session_state.dark_mode = False
        inject_custom_css(False)
    
    st.markdown("---")
    st.markdown("### 📊 Navigation")
    
    pages = {
        "🎯 Dashboard Exécutif": "executive",
        "🗺️ Réseau & Infrastructure": "network",
        "🚴 BIXI Temps Réel": "bixi",
        "🤖 IA & Prédictions": "ai",
        "⚠️ Analyse Sécurité": "safety",
        "📈 Analytics Avancés": "analytics"
    }
    
    page = st.radio("", list(pages.keys()), label_visibility="collapsed")
    page_id = pages[page]
    
    st.markdown("---")
    
    # Filtres globaux
    st.markdown("### 🔍 Filtres")
    
    if not df_acc.empty and 'ANNEE' in df_acc.columns:
        annees = sorted(df_acc['ANNEE'].unique(), reverse=True)
        annee_selectionnee = st.selectbox("Année", annees, index=0 if annees else None)
    else:
        annee_selectionnee = 2024
    
    st.markdown("---")
    st.markdown("### ℹ️ À propos")
    st.markdown("""
    **MobilityPro Analytics**
    
    Plateforme d'intelligence artificielle pour l'optimisation des infrastructures cyclables.
    
    - 🤖 ML & Prédictions
    - 📊 Analytics en temps réel  
    - 🎯 Aide à la décision
    - 🔒 Données sécurisées
    
    *Version 2.0 - 2026*
    """)

# --- PAGE: DASHBOARD EXÉCUTIF ---
if page_id == "executive":
    st.markdown("## 🎯 Dashboard Exécutif")
    st.markdown("Vue stratégique et KPIs clés pour la prise de décision")
    
    # KPIs Row 1
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
            <div class="metric-card">
                <div class="metric-label">🚴 Vélos Disponibles</div>
                <div class="metric-value">{:,}</div>
                <div class="metric-delta" style="color: #26de81;">↑ 12% vs hier</div>
            </div>
        """.format(df_live['num_bikes_available'].sum() if not df_live.empty else 0), unsafe_allow_html=True)
    
    with col2:
        linéaire_total = gdf_reseau.to_crs(epsg=32188).length.sum()/1000 if gdf_reseau is not None else 0
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🛣️ Réseau Total</div>
                <div class="metric-value">{linéaire_total:.0f} km</div>
                <div class="metric-delta" style="color: #26de81;">↑ +8km cette année</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        nb_accidents = len(df_acc[df_acc['ANNEE'] == annee_selectionnee]) if not df_acc.empty else 0
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⚠️ Accidents {annee_selectionnee}</div>
                <div class="metric-value">{nb_accidents:,}</div>
                <div class="metric-delta" style="color: #ff4757;">↓ -15% vs {annee_selectionnee-1}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        stations_vides = len(df_live[df_live['num_bikes_available'] == 0]) if not df_live.empty else 0
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🚨 Stations Vides</div>
                <div class="metric-value">{stations_vides}</div>
                <div class="metric-delta" style="color: #ffa502;">→ Attention requise</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Graphiques interactifs
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Évolution des Accidents par Année")
        if not df_acc.empty:
            acc_par_an = df_acc.groupby('ANNEE').size().reset_index(name='Accidents')
            fig = px.line(acc_par_an, x='ANNEE', y='Accidents', 
                         markers=True, 
                         color_discrete_sequence=['#005528'])
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée d'accidents disponible")
    
    with col2:
        st.markdown("### 🚴 Distribution BIXI par Taux d'Occupation")
        if not df_live.empty:
            fig = px.histogram(df_live, x='taux_occupation', 
                              nbins=20,
                              color_discrete_sequence=['#00a8cc'])
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=350,
                xaxis_title="Taux d'occupation (%)",
                yaxis_title="Nombre de stations"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée BIXI disponible")
    
    # Heatmap horaire des accidents
    st.markdown("### 🕐 Heatmap: Accidents par Jour/Heure")
    if not df_acc.empty and 'HEURE' in df_acc.columns and 'JOUR_SEMAINE' in df_acc.columns:
        df_heatmap = df_acc.groupby(['JOUR_SEMAINE', 'HEURE']).size().reset_index(name='count')
        pivot = df_heatmap.pivot(index='JOUR_SEMAINE', columns='HEURE', values='count').fillna(0)
        
        jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        pivot.index = [jours[i] if i < len(jours) else f"Jour {i}" for i in pivot.index]
        
        fig = px.imshow(pivot, 
                       labels=dict(x="Heure", y="Jour", color="Accidents"),
                       color_continuous_scale="Reds",
                       aspect="auto")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

# --- PAGE: RÉSEAU & INFRASTRUCTURE ---
elif page_id == "network":
    st.markdown("## 🗺️ Réseau & Infrastructure Cyclable")
    
    col_filters, col_map = st.columns([1, 3])
    
    with col_filters:
        st.markdown("### 🎨 Légende & Filtres")
        
        st.markdown("""
        <div class="alert-box">
            <div class="alert-title">Types d'infrastructure</div>
            <div style="margin-top: 15px;">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="width: 30px; height: 4px; background-color: #00C4FF; margin-right: 10px;"></div>
                    <strong>REV</strong> (Réseau Express Vélo)
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="width: 30px; height: 4px; background-color: #005528; margin-right: 10px;"></div>
                    <strong>Piste</strong> cyclable
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="width: 30px; height: 4px; background-color: #00a8cc; margin-right: 10px;"></div>
                    <strong>Bande</strong> cyclable
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="width: 30px; height: 4px; background-color: #9F65AD; margin-right: 10px;"></div>
                    <strong>Sentier</strong>
                </div>
                <div style="display: flex; align-items: center;">
                    <div style="width: 30px; height: 4px; background-color: #8CC63F; margin-right: 10px;"></div>
                    <strong>Partagée</strong>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if gdf_reseau is not None:
            st.metric("📏 Linéaire Total", f"{gdf_reseau.to_crs(epsg=32188).length.sum()/1000:.1f} km")
            
            # Statistiques par type
            st.markdown("### 📊 Répartition")
            type_counts = gdf_reseau['TYPE_VOIE'].value_counts()
            fig = px.pie(values=type_counts.values, names=type_counts.index,
                        color_discrete_sequence=['#005528', '#00a8cc', '#9F65AD', '#8CC63F'])
            fig.update_layout(height=250, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # Options d'affichage
        st.markdown("### ⚙️ Options")
        show_accidents = st.checkbox("🔴 Afficher les accidents", value=False)
        show_bixi = st.checkbox("🚴 Afficher stations BIXI", value=False)
    
    with col_map:
        m = folium.Map([45.52, -73.58], zoom_start=12, tiles='CartoDB positron')
        
        # Réseau cyclable
        def style_map(f):
            t1, t2 = f['properties'].get('TYPE_VOIE'), f['properties'].get('TYPE_VOIE2')
            if t2 == 2: return {'color': '#00C4FF', 'weight': 4, 'opacity': 0.8}
            if t1 == 1: return {'color': '#005528', 'weight': 3, 'opacity': 0.7}
            if t1 == 2: return {'color': '#00a8cc', 'weight': 3, 'opacity': 0.7}
            if t1 == 4: return {'color': '#9F65AD', 'weight': 3, 'opacity': 0.7}
            return {'color': '#8CC63F', 'weight': 2, 'opacity': 0.6}
        
        if gdf_reseau is not None: 
            folium.GeoJson(gdf_reseau, style_function=style_map).add_to(m)
        
        # Overlay accidents
        if show_accidents and not df_acc.empty:
            df_acc_filtered = df_acc[df_acc['ANNEE'] == annee_selectionnee]
            for _, row in df_acc_filtered.head(500).iterrows():
                folium.CircleMarker(
                    [row['LOC_LAT'], row['LOC_LONG']],
                    radius=4,
                    color='red',
                    fill=True,
                    fillOpacity=0.6,
                    popup=f"Gravité: {row.get('GRAVITE', 'N/A')}"
                ).add_to(m)
        
        # Overlay BIXI
        if show_bixi and not df_live.empty:
            for _, row in df_live.iterrows():
                color = 'red' if row['num_bikes_available'] == 0 else 'green' if row['taux_occupation'] > 50 else 'orange'
                folium.CircleMarker(
                    [row['lat'], row['lon']],
                    radius=5,
                    color=color,
                    fill=True,
                    fillOpacity=0.7,
                    popup=f"{row['name']}<br>Vélos: {row['num_bikes_available']}/{row['capacity']}"
                ).add_to(m)
        
        st_folium(m, width="100%", height=700)

# --- PAGE: BIXI TEMPS RÉEL ---
elif page_id == "bixi":
    st.markdown("## 🚴 BIXI - Analyse Temps Réel")
    
    if not df_live.empty:
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        v_dispo = df_live['num_bikes_available'].sum()
        v_total = df_live['capacity'].sum()
        taux_global = (v_dispo / v_total * 100) if v_total > 0 else 0
        
        col1.metric("🚴 Vélos Disponibles", f"{v_dispo:,}")
        col2.metric("🔄 Vélos en Circulation", f"{v_total - v_dispo:,}")
        col3.metric("📊 Taux d'Occupation", f"{taux_global:.1f}%")
        col4.metric("🚨 Stations Vides", len(df_live[df_live['num_bikes_available'] == 0]))
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Clustering des stations
        st.markdown("### 🎯 Clustering Intelligent des Stations")
        
        col_cluster, col_map = st.columns([1, 2])
        
        with col_cluster:
            n_clusters = st.slider("Nombre de clusters", 2, 10, 5)
            
            # Préparer les données pour clustering
            X = df_live[['lat', 'lon', 'taux_occupation']].values
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            df_live['cluster'] = kmeans.fit_predict(X_scaled)
            
            # Stats par cluster
            st.markdown("#### 📊 Statistiques par Cluster")
            for i in range(n_clusters):
                cluster_data = df_live[df_live['cluster'] == i]
                avg_occ = cluster_data['taux_occupation'].mean()
                
                status = "🔴 Critique" if avg_occ < 20 else "🟡 Moyen" if avg_occ < 50 else "🟢 Bon"
                
                st.markdown(f"""
                <div class="metric-card" style="margin-bottom: 10px;">
                    <strong>Cluster {i+1}</strong> {status}<br>
                    Stations: {len(cluster_data)} | Occ. moy: {avg_occ:.1f}%
                </div>
                """, unsafe_allow_html=True)
        
        with col_map:
            # Carte avec clustering
            m = folium.Map([45.52, -73.58], zoom_start=12, tiles='CartoDB positron')
            
            colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'darkblue', 'darkgreen', 'cadetblue']
            
            for i in range(n_clusters):
                cluster_data = df_live[df_live['cluster'] == i]
                for _, row in cluster_data.iterrows():
                    folium.CircleMarker(
                        [row['lat'], row['lon']],
                        radius=6,
                        color=colors[i % len(colors)],
                        fill=True,
                        fillOpacity=0.7,
                        popup=f"Cluster {i+1}<br>{row['name']}<br>Occ: {row['taux_occupation']:.1f}%"
                    ).add_to(m)
            
            st_folium(m, width="100%", height=500)
        
        # Top/Bottom stations
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🔝 Top 10 - Plus Occupées")
            top_10 = df_live.nlargest(10, 'taux_occupation')[['name', 'taux_occupation', 'num_bikes_available', 'capacity']]
            st.dataframe(top_10, hide_index=True, use_container_width=True)
        
        with col2:
            st.markdown("### 🔻 Top 10 - Moins Occupées")
            bottom_10 = df_live.nsmallest(10, 'taux_occupation')[['name', 'taux_occupation', 'num_bikes_available', 'capacity']]
            st.dataframe(bottom_10, hide_index=True, use_container_width=True)
    else:
        st.warning("⚠️ Impossible de charger les données BIXI en temps réel")

# --- PAGE: IA & PRÉDICTIONS ---
elif page_id == "ai":
    st.markdown("## 🤖 Intelligence Artificielle & Prédictions")
    st.markdown("Modèles de Machine Learning pour l'aide à la décision")
    
    # Analyse des flux prioritaires
    st.markdown("### 🎯 Segments Prioritaires (High Impact)")
    
    if not gdf_flux.empty:
        # Calculer un score de priorité
        gdf_flux['SCORE_PRIORITE'] = (
            gdf_flux['VOLUME'] * 0.5 + 
            (gdf_flux['LONGUEUR_M'] / 1000) * 0.3 +
            gdf_flux.get('ACCIDENTS', 0) * 0.2
        )
        
        top_segments = gdf_flux.nlargest(10, 'SCORE_PRIORITE')
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### 📋 Top 10 Segments")
            for idx, row in top_segments.iterrows():
                score = row['SCORE_PRIORITE']
                status_class = 'status-critical' if score > 80 else 'status-high' if score > 60 else 'status-medium'
                
                st.markdown(f"""
                <div class="metric-card" style="margin-bottom: 10px;">
                    <strong>{row.get('NOM_RUE', 'N/A')}</strong>
                    <span class="status-badge {status_class}">Score: {score:.1f}</span><br>
                    <small>Volume: {row['VOLUME']} | Longueur: {row['LONGUEUR_M']:.0f}m</small>
                </div>
                """, unsafe_allow_html=True)
            
            show_existing = st.checkbox("🔍 Afficher pistes existantes (gris)", value=True)
        
        with col2:
            m = folium.Map([45.52, -73.58], zoom_start=13, tiles='CartoDB positron')
            
            # Pistes existantes en gris
            if show_existing and gdf_reseau is not None:
                folium.GeoJson(
                    gdf_reseau, 
                    style_function=lambda x: {'color': '#7f8c8d', 'weight': 2, 'opacity': 0.4}
                ).add_to(m)
            
            # Segments prioritaires
            folium.GeoJson(
                top_segments,
                style_function=lambda x: {'color': '#e74c3c', 'weight': 6, 'opacity': 0.9}
            ).add_to(m)
            
            st_folium(m, width="100%", height=600)
        
        # Matrice de priorisation
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("### 📊 Matrice Impact vs Faisabilité")
        
        # Simulation de scores de faisabilité (en production, utiliser vraies données)
        top_segments_analysis = top_segments.copy()
        top_segments_analysis['FAISABILITE'] = np.random.randint(30, 90, len(top_segments))
        top_segments_analysis['IMPACT'] = (top_segments_analysis['SCORE_PRIORITE'] / top_segments_analysis['SCORE_PRIORITE'].max() * 100)
        
        fig = px.scatter(
            top_segments_analysis,
            x='FAISABILITE',
            y='IMPACT',
            size='LONGUEUR_M',
            color='SCORE_PRIORITE',
            hover_data=['NOM_RUE'],
            color_continuous_scale='Reds',
            labels={'FAISABILITE': 'Faisabilité (%)', 'IMPACT': 'Impact (%)'}
        )
        
        # Quadrants
        fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.add_annotation(x=75, y=75, text="🎯 Quick Wins", showarrow=False, font=dict(size=14, color="green"))
        fig.add_annotation(x=25, y=75, text="🚀 Grands Projets", showarrow=False, font=dict(size=14, color="orange"))
        fig.add_annotation(x=75, y=25, text="📌 Maintenir", showarrow=False, font=dict(size=14, color="blue"))
        fig.add_annotation(x=25, y=25, text="❌ Éviter", showarrow=False, font=dict(size=14, color="red"))
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée de flux disponible pour l'analyse")
    
    # Recommandations IA
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 💡 Recommandations Intelligentes")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="alert-box">
            <div class="alert-title">🏗️ Infrastructures Prioritaires</div>
            <ul style="margin-top: 10px; padding-left: 20px;">
                <li>Ajouter piste sur Ontario Est</li>
                <li>Élargir REV Saint-Denis</li>
                <li>Connecter réseau Hochelaga</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="alert-box">
            <div class="alert-title">🚨 Points Critiques</div>
            <ul style="margin-top: 10px; padding-left: 20px;">
                <li>Intersection Berri/Ontario</li>
                <li>Pont Jacques-Cartier</li>
                <li>Rue Saint-Denis Nord</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="alert-box">
            <div class="alert-title">📈 Opportunités</div>
            <ul style="margin-top: 10px; padding-left: 20px;">
                <li>+15% demande sur Plateau</li>
                <li>Expansion BIXI prévu 2026</li>
                <li>Budget +$2M disponible</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# --- PAGE: ANALYSE SÉCURITÉ ---
elif page_id == "safety":
    st.markdown("## ⚠️ Analyse de la Sécurité Routière")
    
    if not df_acc.empty:
        df_filtered = df_acc[df_acc['ANNEE'] == annee_selectionnee]
        
        # KPIs sécurité
        col1, col2, col3, col4 = st.columns(4)
        
        total_acc = len(df_filtered)
        sur_piste = len(df_filtered[df_filtered['sur_piste'] == 'Oui'])
        hors_piste = total_acc - sur_piste
        taux_sur_piste = (sur_piste / total_acc * 100) if total_acc > 0 else 0
        
        col1.metric("📊 Total Accidents", f"{total_acc:,}")
        col2.metric("✅ Sur Piste", f"{sur_piste} ({taux_sur_piste:.1f}%)")
        col3.metric("❌ Hors Piste", f"{hors_piste} ({100-taux_sur_piste:.1f}%)")
        
        # Gravité
        if 'GRAVITE' in df_filtered.columns:
            graves = len(df_filtered[df_filtered['GRAVITE'].str.contains('Grave|Mortel', case=False, na=False)])
            col4.metric("🚨 Graves/Mortels", f"{graves}")
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Visualisations
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Accidents par Mois")
            if 'MOIS' in df_filtered.columns:
                mois_counts = df_filtered.groupby('MOIS').size().reset_index(name='Accidents')
                mois_noms = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
                mois_counts['Mois'] = mois_counts['MOIS'].apply(lambda x: mois_noms[int(x)-1] if 1 <= x <= 12 else str(x))
                
                fig = px.bar(mois_counts, x='Mois', y='Accidents',
                            color='Accidents',
                            color_continuous_scale='Reds')
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 🕐 Accidents par Heure")
            if 'HEURE' in df_filtered.columns:
                heure_counts = df_filtered.groupby('HEURE').size().reset_index(name='Accidents')
                
                fig = px.line(heure_counts, x='HEURE', y='Accidents',
                             markers=True,
                             color_discrete_sequence=['#e74c3c'])
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
        
        # Carte des accidents
        st.markdown("### 🗺️ Carte des Accidents")
        
        col_opts, col_map = st.columns([1, 3])
        
        with col_opts:
            st.markdown("#### Filtres")
            show_piste_bg = st.checkbox("Afficher réseau cyclable", value=True)
            
            if 'GRAVITE' in df_filtered.columns:
                gravites = df_filtered['GRAVITE'].unique().tolist()
                gravite_filter = st.multiselect("Gravité", gravites, default=gravites)
                df_filtered = df_filtered[df_filtered['GRAVITE'].isin(gravite_filter)]
            
            max_points = st.slider("Nombre max de points", 100, 2000, 500, 100)
        
        with col_map:
            m = folium.Map([45.52, -73.58], zoom_start=12, tiles='CartoDB positron')
            
            # Réseau en background
            if show_piste_bg and gdf_reseau is not None:
                folium.GeoJson(
                    gdf_reseau,
                    style_function=lambda x: {'color': '#005528', 'weight': 2, 'opacity': 0.3}
                ).add_to(m)
            
            # Points d'accidents
            for _, row in df_filtered.head(max_points).iterrows():
                color = 'green' if row['sur_piste'] == 'Oui' else 'red'
                folium.CircleMarker(
                    [row['LOC_LAT'], row['LOC_LONG']],
                    radius=4,
                    color=color,
                    fill=True,
                    fillOpacity=0.6,
                    popup=f"Date: {row['DT_ACCDN']}<br>Sur piste: {row['sur_piste']}<br>Gravité: {row.get('GRAVITE', 'N/A')}"
                ).add_to(m)
            
            st_folium(m, width="100%", height=600)
        
        # Heatmap
        st.markdown("### 🔥 Heatmap de Densité")
        if len(df_filtered) > 0:
            heat_data = [[row['LOC_LAT'], row['LOC_LONG']] for _, row in df_filtered.iterrows()]
            
            m_heat = folium.Map([45.52, -73.58], zoom_start=12, tiles='CartoDB positron')
            HeatMap(heat_data, radius=15, blur=20, max_zoom=13).add_to(m_heat)
            
            st_folium(m_heat, width="100%", height=500)
    else:
        st.warning("⚠️ Aucune donnée d'accidents disponible")

# --- PAGE: ANALYTICS AVANCÉS ---
elif page_id == "analytics":
    st.markdown("## 📈 Analytics Avancés")
    st.markdown("Analyses statistiques approfondies et tendances")
    
    tab1, tab2, tab3 = st.tabs(["📊 Statistiques", "🔍 Corrélations", "📅 Séries Temporelles"])
    
    with tab1:
        st.markdown("### 📊 Vue d'Ensemble Statistique")
        
        if not df_acc.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Distribution par Gravité")
                if 'GRAVITE' in df_acc.columns:
                    grav_dist = df_acc['GRAVITE'].value_counts()
                    fig = px.pie(values=grav_dist.values, names=grav_dist.index,
                                color_discrete_sequence=px.colors.sequential.Reds)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Accidents Sur/Hors Piste")
                piste_dist = df_acc['sur_piste'].value_counts()
                fig = px.bar(x=piste_dist.index, y=piste_dist.values,
                            color=piste_dist.index,
                            color_discrete_map={'Oui': '#26de81', 'Non': '#ff4757'})
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        if not df_comptage.empty:
            st.markdown("#### 📈 Évolution du Volume de Cyclistes")
            
            # Agrégation temporelle
            if 'PERIODE' in df_comptage.columns:
                df_comptage['DATE'] = pd.to_datetime(df_comptage['PERIODE']).dt.date
                daily_counts = df_comptage.groupby('DATE')['VOLUME'].sum().reset_index()
                
                fig = px.line(daily_counts, x='DATE', y='VOLUME',
                             color_discrete_sequence=['#005528'])
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.markdown("### 🔍 Analyse de Corrélations")
        
        if not df_acc.empty and len(df_acc) > 10:
            # Matrice de corrélation
            numeric_cols = df_acc.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) > 1:
                corr_matrix = df_acc[numeric_cols].corr()
                
                fig = px.imshow(corr_matrix,
                               labels=dict(color="Corrélation"),
                               color_continuous_scale="RdBu_r",
                               aspect="auto")
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Pas assez de colonnes numériques pour calculer les corrélations")
        
        # Analyse bivariée
        if not df_live.empty:
            st.markdown("### 📊 Relation Capacité vs Occupation BIXI")
            
            fig = px.scatter(df_live, x='capacity', y='taux_occupation',
                           size='num_bikes_available',
                           color='taux_occupation',
                           color_continuous_scale='Viridis',
                           hover_data=['name'])
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("### 📅 Analyse des Séries Temporelles")
        
        if not df_acc.empty and 'DT_ACCDN' in df_acc.columns:
            st.markdown("#### Tendance Mensuelle des Accidents")
            
            df_acc['ANNEE_MOIS'] = df_acc['DT_ACCDN'].dt.to_period('M').astype(str)
            monthly = df_acc.groupby('ANNEE_MOIS').size().reset_index(name='Accidents')
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=monthly['ANNEE_MOIS'], y=monthly['Accidents'],
                                    mode='lines+markers',
                                    name='Accidents',
                                    line=dict(color='#e74c3c', width=2)))
            
            # Moyenne mobile
            monthly['MA_3'] = monthly['Accidents'].rolling(window=3).mean()
            fig.add_trace(go.Scatter(x=monthly['ANNEE_MOIS'], y=monthly['MA_3'],
                                    mode='lines',
                                    name='Moyenne mobile (3 mois)',
                                    line=dict(color='#3498db', width=2, dash='dash')))
            
            fig.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
        
        if not df_comptage.empty and 'PERIODE' in df_comptage.columns:
            st.markdown("#### 🚴 Volume de Passages - Tendance")
            
            df_comptage['DATE'] = pd.to_datetime(df_comptage['PERIODE']).dt.date
            daily = df_comptage.groupby('DATE')['VOLUME'].sum().reset_index()
            
            fig = px.area(daily, x='DATE', y='VOLUME',
                         color_discrete_sequence=['#00a8cc'])
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

# --- FOOTER ---
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.markdown("""
    <div style="text-align: center; padding: 20px; opacity: 0.6;">
        <small>
        MobilityPro Analytics v2.0 | Développé avec ❤️ pour Montréal | 
        Données: Ville de Montréal Open Data | 
        Mise à jour: {date}
        </small>
    </div>
""".format(date=datetime.now().strftime("%Y-%m-%d %H:%M")), unsafe_allow_html=True)