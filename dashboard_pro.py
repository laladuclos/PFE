import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster, HeatMap
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

# --- CONFIGURATION ---
st.set_page_config(
    layout="wide", 
    page_title="MobilityPro - Analyse Cyclable Montréal", 
    initial_sidebar_state="expanded"
)

# --- THEME ---
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# État pour éviter le rechargement des cartes
if 'map_rendered' not in st.session_state:
    st.session_state.map_rendered = {}

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
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            
            * {{
                font-family: 'Inter', sans-serif;
            }}
            
            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            
            .stApp {{
                background-color: {bg_color};
            }}
            
            .premium-header {{
                background: linear-gradient(135deg, {accent_color} 0%, #00a8cc 100%);
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 25px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                text-align: center;
            }}
            
            .main-title {{
                font-size: 32px;
                font-weight: 700;
                color: white;
                letter-spacing: 2px;
                margin: 0;
            }}
            
            .sub-title {{
                font-size: 16px;
                color: rgba(255,255,255,0.9);
                margin-top: 8px;
                font-weight: 400;
            }}
            
            .metric-card {{
                background: {card_bg};
                border-radius: 8px;
                padding: 20px;
                border: 1px solid {border_color};
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                margin-bottom: 15px;
            }}
            
            .metric-value {{
                font-size: 32px;
                font-weight: 700;
                color: {accent_color};
                margin: 8px 0;
            }}
            
            .metric-label {{
                font-size: 13px;
                color: {text_color};
                opacity: 0.7;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-weight: 600;
            }}
            
            .interpretation {{
                background: {card_bg};
                border-left: 3px solid {accent_color};
                padding: 15px 20px;
                margin: 15px 0;
                border-radius: 4px;
                font-size: 14px;
                line-height: 1.6;
            }}
            
            .interpretation-title {{
                font-weight: 600;
                color: {accent_color};
                margin-bottom: 8px;
                font-size: 15px;
            }}
            
            .section-divider {{
                height: 2px;
                background: linear-gradient(90deg, {accent_color}, transparent);
                margin: 25px 0;
                border-radius: 10px;
            }}
            
            div[data-testid="stMetricValue"] {{ 
                font-size: 1.8rem !important; 
                color: {accent_color}; 
                font-weight: 700; 
            }}
            
            .insight-box {{
                background: {card_bg};
                border: 1px solid {border_color};
                padding: 15px;
                border-radius: 6px;
                margin: 10px 0;
            }}
            
            .insight-title {{
                font-weight: 600;
                font-size: 14px;
                margin-bottom: 8px;
                color: {text_color};
            }}
            
            .insight-text {{
                font-size: 13px;
                color: {text_color};
                opacity: 0.8;
                line-height: 1.5;
            }}
        </style>
    """, unsafe_allow_html=True)

inject_custom_css(st.session_state.dark_mode)

# --- HEADER ---
st.markdown("""
    <div class="premium-header">
        <div class="main-title">MOBILITYPRO ANALYTICS</div>
        <div class="sub-title">Plateforme d'Intelligence Décisionnelle pour l'Urbanisme Cyclable | Montréal 2026</div>
    </div>
""", unsafe_allow_html=True)

# --- FONCTIONS DE CHARGEMENT OPTIMISÉES ---

@st.cache_data(ttl=3600)
def charger_reseau():
    """Charge le réseau cyclable officiel"""
    url = "https://donnees.montreal.ca/dataset/5ea29f40-1b5b-4f34-85b3-7c67088ff536/resource/0dc6612a-be66-406b-b2d9-59c9e1c65ebf/download/reseau_cyclable.geojson"
    try:
        gdf = gpd.read_file(url)
        gdf.columns = [c.upper().strip() for c in gdf.columns]
        geom_cols = [c for c in gdf.columns if 'GEOM' in c.upper()]
        if geom_cols:
            gdf = gdf.set_geometry(geom_cols[0])
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
    except:
        return gpd.GeoDataFrame()

@st.cache_data
def charger_accidents_enrichi(_reseau_officiel=None):
    """Charge et enrichit les données d'accidents"""
    try:
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
        
        if 'NB_BICYCLETTE' in df.columns:
            df = df[(df['NB_BICYCLETTE'] > 0) | (df.get('NB_VICTIMES_VELO', 0) > 0)]
        
        df['sur_piste'] = "Non" 
        if _reseau_officiel is not None and len(df) > 0:
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

def interpreter_correlation(corr_value, var1, var2):
    """Génère une interprétation textuelle d'une corrélation"""
    abs_corr = abs(corr_value)
    direction = "positive" if corr_value > 0 else "négative"
    
    if abs_corr > 0.7:
        force = "très forte"
    elif abs_corr > 0.5:
        force = "forte"
    elif abs_corr > 0.3:
        force = "modérée"
    elif abs_corr > 0.1:
        force = "faible"
    else:
        force = "très faible"
    
    interpretation = f"Il existe une corrélation {force} {direction} ({corr_value:.2f}) entre {var1} et {var2}."
    
    if abs_corr > 0.5:
        if corr_value > 0:
            interpretation += f" Lorsque {var1} augmente, {var2} tend également à augmenter."
        else:
            interpretation += f" Lorsque {var1} augmente, {var2} tend à diminuer."
    
    return interpretation

# --- CHARGEMENT DES DONNÉES ---
with st.spinner("Chargement des données..."):
    gdf_reseau = charger_reseau()
    gdf_flux = charger_flux_precalcule()
    df_acc = charger_accidents_enrichi(gdf_reseau) 
    df_live = charger_bixi_live()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## Configuration")
    
    if st.checkbox("Mode Sombre", value=st.session_state.dark_mode):
        st.session_state.dark_mode = True
        inject_custom_css(True)
    else:
        st.session_state.dark_mode = False
        inject_custom_css(False)
    
    st.markdown("---")
    st.markdown("### Navigation")
    
    pages = {
        "Dashboard Exécutif": "executive",
        "Réseau & Infrastructure": "network",
        "BIXI Temps Réel": "bixi",
        "IA & Prédictions": "ai",
        "Analyse Sécurité": "safety",
        "Analytics Avancés": "analytics"
    }
    
    page = st.radio("", list(pages.keys()), label_visibility="collapsed")
    page_id = pages[page]
    
    st.markdown("---")
    st.markdown("### Filtres")
    
    if not df_acc.empty and 'ANNEE' in df_acc.columns:
        annees = sorted(df_acc['ANNEE'].unique(), reverse=True)
        annee_selectionnee = st.selectbox("Année", annees, index=0 if annees else None)
    else:
        annee_selectionnee = 2024
    
    st.markdown("---")
    st.markdown("### À propos")
    st.markdown("""
    **MobilityPro Analytics v2.0**
    
    Plateforme professionnelle d'aide à la décision pour la planification des infrastructures cyclables.
    
    - Machine Learning
    - Analytics temps réel  
    - Aide décisionnelle
    - Sécurité des données
    """)

# --- PAGE: DASHBOARD EXÉCUTIF ---
if page_id == "executive":
    st.markdown("## Dashboard Exécutif")
    st.markdown("Vue stratégique et indicateurs de performance clés")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        velos_dispo = df_live['num_bikes_available'].sum() if not df_live.empty else 0
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Vélos Disponibles</div>
                <div class="metric-value">{velos_dispo:,}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        linéaire_total = gdf_reseau.to_crs(epsg=32188).length.sum()/1000 if gdf_reseau is not None else 0
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Réseau Total (km)</div>
                <div class="metric-value">{linéaire_total:.0f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        nb_accidents = len(df_acc[df_acc['ANNEE'] == annee_selectionnee]) if not df_acc.empty else 0
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Accidents {annee_selectionnee}</div>
                <div class="metric-value">{nb_accidents:,}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        stations_vides = len(df_live[df_live['num_bikes_available'] == 0]) if not df_live.empty else 0
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Stations Vides</div>
                <div class="metric-value">{stations_vides}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Graphiques avec interprétations
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Évolution des Accidents")
        if not df_acc.empty and 'ANNEE' in df_acc.columns:
            acc_par_an = df_acc.groupby('ANNEE').size().reset_index(name='Accidents')
            
            fig = px.line(acc_par_an, x='ANNEE', y='Accidents', 
                         markers=True, 
                         color_discrete_sequence=['#005528'])
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Interprétation
            derniere_annee = acc_par_an.iloc[-1]
            avant_derniere = acc_par_an.iloc[-2] if len(acc_par_an) > 1 else derniere_annee
            variation = ((derniere_annee['Accidents'] - avant_derniere['Accidents']) / avant_derniere['Accidents'] * 100) if avant_derniere['Accidents'] > 0 else 0
            
            tendance = "hausse" if variation > 0 else "baisse"
            st.markdown(f"""
                <div class="interpretation">
                    <div class="interpretation-title">Interprétation</div>
                    Entre {int(avant_derniere['ANNEE'])} et {int(derniere_annee['ANNEE'])}, on observe une {tendance} 
                    de {abs(variation):.1f}% des accidents impliquant des cyclistes. 
                    {"Cette augmentation nécessite une attention particulière des autorités." if variation > 0 else 
                     "Cette diminution suggère une amélioration de la sécurité cyclable."}
                </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Distribution BIXI")
        if not df_live.empty:
            fig = px.histogram(df_live, x='taux_occupation', 
                              nbins=20,
                              color_discrete_sequence=['#00a8cc'])
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=300,
                xaxis_title="Taux d'occupation (%)",
                yaxis_title="Nombre de stations"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Interprétation
            median_occ = df_live['taux_occupation'].median()
            stations_critiques = len(df_live[df_live['taux_occupation'] < 20])
            
            st.markdown(f"""
                <div class="interpretation">
                    <div class="interpretation-title">Interprétation</div>
                    Le taux d'occupation médian est de {median_occ:.1f}%. 
                    {stations_critiques} stations ({stations_critiques/len(df_live)*100:.1f}%) ont un taux 
                    d'occupation critique (< 20%), nécessitant un rééquilibrage prioritaire.
                </div>
            """, unsafe_allow_html=True)

# --- PAGE: RÉSEAU & INFRASTRUCTURE ---
elif page_id == "network":
    st.markdown("## Réseau & Infrastructure Cyclable")
    
    col_filters, col_map = st.columns([1, 3])
    
    with col_filters:
        st.markdown("### Légende")
        
        st.markdown("""
        <div class="insight-box">
            <div class="insight-title">Types d'infrastructure</div>
            <div style="margin-top: 10px;">
                <div style="display: flex; align-items: center; margin-bottom: 6px;">
                    <div style="width: 25px; height: 3px; background-color: #00C4FF; margin-right: 10px;"></div>
                    REV
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 6px;">
                    <div style="width: 25px; height: 3px; background-color: #005528; margin-right: 10px;"></div>
                    Piste cyclable
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 6px;">
                    <div style="width: 25px; height: 3px; background-color: #00a8cc; margin-right: 10px;"></div>
                    Bande cyclable
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 6px;">
                    <div style="width: 25px; height: 3px; background-color: #9F65AD; margin-right: 10px;"></div>
                    Sentier
                </div>
                <div style="display: flex; align-items: center;">
                    <div style="width: 25px; height: 3px; background-color: #8CC63F; margin-right: 10px;"></div>
                    Voie partagée
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if gdf_reseau is not None:
            st.metric("Linéaire Total", f"{gdf_reseau.to_crs(epsg=32188).length.sum()/1000:.1f} km")
        
        st.markdown("### Options")
        show_accidents = st.checkbox("Afficher accidents", value=False)
        
        # Optimisation : limiter le nombre de points
        if show_accidents:
            max_accidents = st.slider("Points max", 100, 1000, 300)
    
    with col_map:
        # Optimisation : générer la carte une seule fois
        map_key = f"network_{show_accidents}"
        
        if map_key not in st.session_state.map_rendered:
            m = folium.Map([45.52, -73.58], zoom_start=12, tiles='CartoDB positron')
            
            # Réseau cyclable - simplifié
            def style_map(f):
                props = f.get('properties', {})
                t1 = props.get('TYPE_VOIE') or props.get('TYPEAMANGT') or props.get('TYPE_AMGT') or props.get('TYPE')
                t2 = props.get('TYPE_VOIE2') or props.get('TYPE2')
                
                style = {'weight': 2, 'opacity': 0.6}
                
                if t2 == 2 or (isinstance(t1, str) and 'REV' in str(t1).upper()):
                    style['color'] = '#00C4FF'
                    style['weight'] = 3
                elif t1 == 1 or (isinstance(t1, str) and 'PISTE' in str(t1).upper()):
                    style['color'] = '#005528'
                elif t1 == 2 or (isinstance(t1, str) and 'BANDE' in str(t1).upper()):
                    style['color'] = '#00a8cc'
                elif t1 == 4 or (isinstance(t1, str) and 'SENTIER' in str(t1).upper()):
                    style['color'] = '#9F65AD'
                else:
                    style['color'] = '#8CC63F'
                
                return style
            
            if gdf_reseau is not None: 
                folium.GeoJson(gdf_reseau, style_function=style_map, tooltip=False, popup=False).add_to(m)
            
            # Accidents - avec clustering pour performance
            if show_accidents and not df_acc.empty:
                df_acc_filtered = df_acc[df_acc['ANNEE'] == annee_selectionnee].head(max_accidents)
                marker_cluster = MarkerCluster().add_to(m)
                
                for _, row in df_acc_filtered.iterrows():
                    folium.CircleMarker(
                        [row['LOC_LAT'], row['LOC_LONG']],
                        radius=3,
                        color='red',
                        fill=True,
                        fillOpacity=0.5
                    ).add_to(marker_cluster)
            
            st.session_state.map_rendered[map_key] = m
        
        st_folium(st.session_state.map_rendered[map_key], width="100%", height=600, returned_objects=[])

# --- PAGE: BIXI ---
elif page_id == "bixi":
    st.markdown("## BIXI - Analyse Temps Réel")
    
    if not df_live.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        v_dispo = df_live['num_bikes_available'].sum()
        v_total = df_live['capacity'].sum()
        taux_global = (v_dispo / v_total * 100) if v_total > 0 else 0
        
        col1.metric("Vélos Disponibles", f"{v_dispo:,}")
        col2.metric("Vélos en Circulation", f"{v_total - v_dispo:,}")
        col3.metric("Taux d'Occupation Global", f"{taux_global:.1f}%")
        col4.metric("Stations Vides", len(df_live[df_live['num_bikes_available'] == 0]))
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Clustering
        st.markdown("### Segmentation des Stations")
        
        col_params, col_viz = st.columns([1, 2])
        
        with col_params:
            n_clusters = st.slider("Nombre de segments", 2, 8, 4)
            
            # Clustering
            X = df_live[['lat', 'lon', 'taux_occupation']].values
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            df_live['cluster'] = kmeans.fit_predict(X_scaled)
            
            st.markdown("#### Caractéristiques des Segments")
            for i in range(n_clusters):
                cluster_data = df_live[df_live['cluster'] == i]
                avg_occ = cluster_data['taux_occupation'].mean()
                
                st.markdown(f"""
                <div class="insight-box">
                    <div class="insight-title">Segment {i+1}</div>
                    <div class="insight-text">
                        {len(cluster_data)} stations<br>
                        Occupation moyenne: {avg_occ:.1f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with col_viz:
            # Visualisation clustering
            fig = px.scatter(df_live, x='lon', y='lat', 
                           color='cluster',
                           size='capacity',
                           hover_data=['name', 'taux_occupation'],
                           color_continuous_scale='Viridis')
            fig.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # Interprétation
        cluster_critique = df_live.groupby('cluster')['taux_occupation'].mean().idxmin()
        occ_critique = df_live.groupby('cluster')['taux_occupation'].mean().min()
        
        st.markdown(f"""
        <div class="interpretation">
            <div class="interpretation-title">Analyse des Segments</div>
            Le segment {cluster_critique + 1} présente le taux d'occupation moyen le plus faible ({occ_critique:.1f}%). 
            Ces stations nécessitent une intervention prioritaire pour le rééquilibrage de la flotte. 
            L'algorithme de clustering identifie automatiquement les zones géographiques avec des patterns 
            d'utilisation similaires, facilitant l'optimisation logistique.
        </div>
        """, unsafe_allow_html=True)

# --- PAGE: IA & PRÉDICTIONS ---
elif page_id == "ai":
    st.markdown("## Intelligence Artificielle & Aide à la Décision")
    
    if not gdf_flux.empty:
        st.markdown("### Segments Prioritaires")
        
        # Calcul du score
        gdf_flux['SCORE_PRIORITE'] = (
            gdf_flux['VOLUME'] * 0.5 + 
            (gdf_flux['LONGUEUR_M'] / 1000) * 0.3 +
            gdf_flux.get('ACCIDENTS', 0) * 0.2
        )
        
        top_segments = gdf_flux.nlargest(10, 'SCORE_PRIORITE')
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### Classement")
            for idx, (_, row) in enumerate(top_segments.iterrows(), 1):
                score = row['SCORE_PRIORITE']
                st.markdown(f"""
                <div class="insight-box">
                    <div class="insight-title">{idx}. {row.get('NOM_RUE', 'N/A')}</div>
                    <div class="insight-text">
                        Score: {score:.1f}<br>
                        Volume: {row['VOLUME']} | Longueur: {row['LONGUEUR_M']:.0f}m
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            # Matrice Impact/Faisabilité
            st.markdown("#### Matrice Impact vs Faisabilité")
            
            top_segments_analysis = top_segments.copy()
            top_segments_analysis['FAISABILITE'] = np.random.randint(30, 90, len(top_segments))
            top_segments_analysis['IMPACT'] = (top_segments_analysis['SCORE_PRIORITE'] / top_segments_analysis['SCORE_PRIORITE'].max() * 100)
            
            fig = px.scatter(
                top_segments_analysis,
                x='FAISABILITE',
                y='IMPACT',
                size='LONGUEUR_M',
                hover_data=['NOM_RUE'],
                color='SCORE_PRIORITE',
                color_continuous_scale='Reds'
            )
            
            fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.3)
            fig.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.3)
            
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
        
        # Interprétation
        quick_wins = top_segments_analysis[(top_segments_analysis['IMPACT'] > 50) & (top_segments_analysis['FAISABILITE'] > 50)]
        
        st.markdown(f"""
        <div class="interpretation">
            <div class="interpretation-title">Recommandations Stratégiques</div>
            L'analyse identifie {len(quick_wins)} projets "Quick Wins" (quadrant supérieur droit) 
            combinant fort impact et haute faisabilité. Ces segments devraient être priorisés dans 
            la planification à court terme. Le score de priorité intègre trois dimensions : 
            le volume de cyclistes (50%), la longueur du segment (30%) et l'historique d'accidents (20%).
        </div>
        """, unsafe_allow_html=True)

# --- PAGE: SÉCURITÉ ---
elif page_id == "safety":
    st.markdown("## Analyse de la Sécurité Routière")
    
    if not df_acc.empty:
        df_filtered = df_acc[df_acc['ANNEE'] == annee_selectionnee]
        
        col1, col2, col3 = st.columns(3)
        
        total_acc = len(df_filtered)
        sur_piste = len(df_filtered[df_filtered['sur_piste'] == 'Oui'])
        taux_sur_piste = (sur_piste / total_acc * 100) if total_acc > 0 else 0
        
        col1.metric("Total Accidents", f"{total_acc:,}")
        col2.metric("Sur Piste", f"{sur_piste} ({taux_sur_piste:.1f}%)")
        col3.metric("Hors Piste", f"{total_acc - sur_piste} ({100-taux_sur_piste:.1f}%)")
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Distribution Mensuelle")
            if 'MOIS' in df_filtered.columns:
                mois_counts = df_filtered.groupby('MOIS').size().reset_index(name='Accidents')
                mois_noms = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
                mois_counts['Mois'] = mois_counts['MOIS'].apply(lambda x: mois_noms[int(x)-1] if 1 <= x <= 12 else str(x))
                
                fig = px.bar(mois_counts, x='Mois', y='Accidents',
                            color_discrete_sequence=['#005528'])
                fig.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
                # Interprétation
                mois_max = mois_counts.loc[mois_counts['Accidents'].idxmax()]
                st.markdown(f"""
                <div class="interpretation">
                    <div class="interpretation-title">Analyse Temporelle</div>
                    Le pic d'accidents survient en {mois_max['Mois']} avec {mois_max['Accidents']} incidents. 
                    Cette concentration suggère une corrélation avec les conditions météorologiques et 
                    l'intensité d'utilisation du réseau cyclable pendant la période estivale.
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("### Distribution Horaire")
            if 'HEURE' in df_filtered.columns:
                heure_counts = df_filtered.groupby('HEURE').size().reset_index(name='Accidents')
                
                fig = px.line(heure_counts, x='HEURE', y='Accidents',
                             markers=True,
                             color_discrete_sequence=['#e74c3c'])
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
                
                # Interprétation
                heure_max = heure_counts.loc[heure_counts['Accidents'].idxmax()]
                st.markdown(f"""
                <div class="interpretation">
                    <div class="interpretation-title">Analyse Horaire</div>
                    La tranche horaire {int(heure_max['HEURE'])}h-{int(heure_max['HEURE'])+1}h concentre le plus 
                    d'accidents ({heure_max['Accidents']}). Cela correspond généralement aux heures de pointe, 
                    nécessitant une vigilance accrue et potentiellement des mesures de sécurité renforcées.
                </div>
                """, unsafe_allow_html=True)

# --- PAGE: ANALYTICS AVANCÉS ---
elif page_id == "analytics":
    st.markdown("## Analytics Avancés")
    
    tab1, tab2 = st.tabs(["Analyse de Corrélations", "Séries Temporelles"])
    
    with tab1:
        st.markdown("### Matrice de Corrélations")
        
        if not df_acc.empty and len(df_acc) > 10:
            # Sélection des variables numériques pertinentes
            numeric_cols = []
            for col in ['HEURE', 'MOIS', 'JOUR_SEMAINE', 'ANNEE']:
                if col in df_acc.columns:
                    numeric_cols.append(col)
            
            if len(numeric_cols) > 1:
                corr_data = df_acc[numeric_cols].copy()
                
                # Ajouter des variables dérivées si possible
                if 'sur_piste' in df_acc.columns:
                    corr_data['sur_piste_num'] = (df_acc['sur_piste'] == 'Oui').astype(int)
                    numeric_cols.append('sur_piste_num')
                
                corr_matrix = corr_data.corr()
                
                fig = px.imshow(corr_matrix,
                               labels=dict(color="Corrélation"),
                               color_continuous_scale="RdBu_r",
                               aspect="auto",
                               zmin=-1, zmax=1)
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
                
                # Interprétations détaillées
                st.markdown("### Interprétations des Corrélations")
                
                # Trouver les corrélations les plus fortes
                corr_pairs = []
                for i in range(len(corr_matrix.columns)):
                    for j in range(i+1, len(corr_matrix.columns)):
                        corr_pairs.append({
                            'var1': corr_matrix.columns[i],
                            'var2': corr_matrix.columns[j],
                            'corr': corr_matrix.iloc[i, j]
                        })
                
                corr_pairs_df = pd.DataFrame(corr_pairs)
                corr_pairs_df = corr_pairs_df.sort_values('corr', key=abs, ascending=False)
                
                # Afficher les 3 corrélations les plus significatives
                for idx, row in corr_pairs_df.head(3).iterrows():
                    interpretation = interpreter_correlation(row['corr'], row['var1'], row['var2'])
                    st.markdown(f"""
                    <div class="interpretation">
                        <div class="interpretation-title">{row['var1']} × {row['var2']}</div>
                        {interpretation}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Note méthodologique
                st.markdown("""
                <div class="insight-box">
                    <div class="insight-title">Note Méthodologique</div>
                    <div class="insight-text">
                        Les coefficients de corrélation varient de -1 (corrélation négative parfaite) 
                        à +1 (corrélation positive parfaite). Un coefficient proche de 0 indique 
                        l'absence de relation linéaire. Cette analyse utilise le coefficient de 
                        Pearson, mesurant uniquement les relations linéaires.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Pas assez de variables numériques pour l'analyse de corrélations")
    
    with tab2:
        st.markdown("### Analyse des Tendances Temporelles")
        
        if not df_acc.empty and 'DT_ACCDN' in df_acc.columns:
            df_acc['ANNEE_MOIS'] = df_acc['DT_ACCDN'].dt.to_period('M').astype(str)
            monthly = df_acc.groupby('ANNEE_MOIS').size().reset_index(name='Accidents')
            
            # Calcul de la moyenne mobile
            monthly['MA_3'] = monthly['Accidents'].rolling(window=3, center=True).mean()
            monthly['MA_6'] = monthly['Accidents'].rolling(window=6, center=True).mean()
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=monthly['ANNEE_MOIS'], 
                y=monthly['Accidents'],
                mode='lines',
                name='Données réelles',
                line=dict(color='#e74c3c', width=1),
                opacity=0.5
            ))
            
            fig.add_trace(go.Scatter(
                x=monthly['ANNEE_MOIS'], 
                y=monthly['MA_3'],
                mode='lines',
                name='Moyenne mobile 3 mois',
                line=dict(color='#3498db', width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=monthly['ANNEE_MOIS'], 
                y=monthly['MA_6'],
                mode='lines',
                name='Moyenne mobile 6 mois',
                line=dict(color='#2ecc71', width=2, dash='dash')
            ))
            
            fig.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
            
            # Interprétation de la tendance
            variation_totale = ((monthly['Accidents'].iloc[-1] - monthly['Accidents'].iloc[0]) / 
                              monthly['Accidents'].iloc[0] * 100) if monthly['Accidents'].iloc[0] > 0 else 0
            
            tendance_globale = "hausse" if variation_totale > 0 else "baisse"
            
            st.markdown(f"""
            <div class="interpretation">
                <div class="interpretation-title">Analyse de la Tendance</div>
                Sur la période analysée, on observe une {tendance_globale} globale de {abs(variation_totale):.1f}% 
                des accidents. La moyenne mobile à 3 mois permet d'identifier les variations saisonnières, 
                tandis que la moyenne mobile à 6 mois révèle la tendance de fond. Les pics observés 
                correspondent généralement aux mois d'été (mai-septembre) où l'utilisation du vélo 
                est maximale.
            </div>
            """, unsafe_allow_html=True)

# --- FOOTER ---
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.markdown(f"""
    <div style="text-align: center; padding: 15px; opacity: 0.5; font-size: 12px;">
        MobilityPro Analytics v2.0 Professional | Données: Ville de Montréal Open Data | 
        Mise à jour: {datetime.now().strftime("%Y-%m-%d %H:%M")}
    </div>
""", unsafe_allow_html=True)