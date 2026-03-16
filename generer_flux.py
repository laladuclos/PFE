import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
from shapely.geometry import LineString, Point
import os

# --- 1. CONFIGURATION ---
FICHIER_BIXI = "bixi.csv"
URL_RESEAU_VILLE = "https://donnees.montreal.ca/dataset/5ea29f40-1b5b-4f34-85b3-7c67088ff536/resource/0dc6612a-be66-406b-b2d9-59c9e1c65ebf/download/reseau_cyclable.geojson"

# RÈGLAGES V5 (Réalisme)
PENALITE_DANGER = 4.0   
BUFFER_TOLERANCE = 7.0  
NOMBRE_TRAJETS_A_ANALYSER = 2000 
CHUNK_SIZE = 100000 

print(f"🚀 DÉMARRAGE V6 : Extraction des NOMS DE RUES + Flux...")

# --- 2. LECTURE DES DONNÉES ---
cols_utiles = ['STARTSTATIONLATITUDE', 'STARTSTATIONLONGITUDE', 'ENDSTATIONLATITUDE', 'ENDSTATIONLONGITUDE']
aggregated_chunks = []

try:
    print("   Lecture CSV...")
    for chunk in pd.read_csv(FICHIER_BIXI, usecols=cols_utiles, chunksize=CHUNK_SIZE):
        counts = chunk.groupby(cols_utiles).size().reset_index(name='nb_voyages')
        aggregated_chunks.append(counts)
    
    df_full = pd.concat(aggregated_chunks)
    df_final = df_full.groupby(cols_utiles)['nb_voyages'].sum().reset_index()
    df_top = df_final.sort_values(by='nb_voyages', ascending=False).head(NOMBRE_TRAJETS_A_ANALYSER)
    print(f"   Analyse des {len(df_top)} axes principaux.")

except FileNotFoundError:
    print(f"❌ Erreur : '{FICHIER_BIXI}' introuvable.")
    exit()

# --- 3. PRÉPARATION DU GRAPHE ---
print("🌍 Téléchargement de la carte...")
G = ox.graph_from_place("Montreal, Canada", network_type='bike')

print("⚖️ Application de la pondération...")
for u, v, k, data in G.edges(keys=True, data=True):
    type_route = data.get('highway', '')
    if isinstance(type_route, list): type_route = type_route[0]
    
    is_cycle_friendly = False
    
    # 1. Analyse OSM
    if type_route in ['cycleway', 'path', 'track']:
        is_cycle_friendly = True
    elif 'cycleway' in data:
        cw = data['cycleway']
        if isinstance(cw, list): cw = cw[0] 
        if cw in ['lane', 'track', 'opposite', 'opposite_lane', 'share_busway', 'shared_lane']:
            is_cycle_friendly = True
    
    data['is_cycle_friendly'] = is_cycle_friendly
    
    # 2. Application du Coût
    length = data.get('length', 0)
    if is_cycle_friendly:
        data['cout_prefere'] = length 
    else:
        data['cout_prefere'] = length * PENALITE_DANGER

# --- 4. CALCUL DES ITINÉRAIRES ---
print("⚙️ Calcul des itinéraires et noms de rues...")
usage_segments = {} 
compteur = 0

for _, row in df_top.iterrows():
    compteur += 1
    if compteur % 200 == 0: print(f"   Traitement... {compteur}/{len(df_top)}")
    
    try:
        orig = ox.nearest_nodes(G, row['STARTSTATIONLONGITUDE'], row['STARTSTATIONLATITUDE'])
        dest = ox.nearest_nodes(G, row['ENDSTATIONLONGITUDE'], row['ENDSTATIONLATITUDE'])
        
        if orig != dest:
            route = nx.shortest_path(G, orig, dest, weight='cout_prefere')
            vol = row['nb_voyages']
            
            for i in range(len(route) - 1):
                u, v = route[i], route[i+1]
                
                # Récupération données complètes
                edge_data = G.get_edge_data(u, v)[0]
                
                # --- NOUVEAU : EXTRACTION DU NOM ---
                nom = edge_data.get('name', 'Inconnu')
                if isinstance(nom, list): nom = f"{nom[0]} et al." # Si plusieurs noms, on prend le premier
                
                is_osm_friendly = edge_data.get('is_cycle_friendly', False)

                if 'geometry' in edge_data: geom = edge_data['geometry']
                else: geom = LineString([Point(G.nodes[u]['x'], G.nodes[u]['y']), Point(G.nodes[v]['x'], G.nodes[v]['y'])])
                
                key = (u, v)
                if key in usage_segments:
                    usage_segments[key]['vol'] += vol
                    if is_osm_friendly: usage_segments[key]['osm_friendly'] = True
                else:
                    usage_segments[key] = {
                        'vol': vol, 
                        'geometry': geom,
                        'osm_friendly': is_osm_friendly,
                        'nom_rue': str(nom) # On sauvegarde le nom ici
                    }
    except: continue

# --- 5. VALIDATION GÉOMÉTRIQUE SOUPLE ---
print(f"🎯 Validation croisée...")

lignes = []
volumes = []
osm_status = []
noms = []

for k, v in usage_segments.items():
    lignes.append(v['geometry'])
    volumes.append(v['vol'])
    osm_status.append(v['osm_friendly'])
    noms.append(v['nom_rue'])

gdf_flux = gpd.GeoDataFrame({
    'nom_rue': noms,
    'volume': volumes, 
    'osm_friendly': osm_status,
    'geometry': lignes
}, crs="EPSG:4326")

try:
    reseau_ville = gpd.read_file(URL_RESEAU_VILLE)
    flux_m = gdf_flux.to_crs(epsg=32188)
    ville_m = reseau_ville.to_crs(epsg=32188)
    
    buffer_ville = ville_m.geometry.buffer(BUFFER_TOLERANCE).unary_union
    flux_m['ville_friendly'] = flux_m.geometry.intersects(buffer_ville)
    
    flux_m['sur_piste'] = flux_m['osm_friendly'] | flux_m['ville_friendly']
    gdf_final = flux_m.to_crs(epsg=4326)
    
except Exception as e:
    print(f"⚠️ Erreur validation ville : {e}")
    gdf_final = gdf_flux
    gdf_final['sur_piste'] = gdf_final['osm_friendly']

# --- 6. EXPORT ---
gdf_final['couleur'] = gdf_final['sur_piste'].apply(lambda x: '#3498db' if x else '#FF0000') 
gdf_final['etat'] = gdf_final['sur_piste'].apply(lambda x: 'Sur Piste' if x else 'Hors Piste (Missing Link)')

# On garde la colonne nom_rue !
gdf_final[['nom_rue', 'volume', 'etat', 'couleur', 'geometry']].to_file("flux_bixi_estimes.geojson", driver="GeoJSON")

print("✅ SUCCÈS V6 ! Les noms de rues sont inclus.")