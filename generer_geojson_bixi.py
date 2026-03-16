import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
from shapely.geometry import LineString, Point
import os

# --- CONFIGURATION ---
NOUVEAU_FICHIER_BIXI = "/workspaces/PFE/bixi.csv"
OUTPUT_GEOJSON = "flux_bixi_estimes.geojson"
NOMBRE_TRAJETS_A_ANALYSER = 2000 # On remet 2000 pour avoir une vraie carte

print(f"🚀 Démarrage... Génération des {NOMBRE_TRAJETS_A_ANALYSER} trajets les plus fréquents.")

# 1. CHARGEMENT DONNÉES
if not os.path.exists(NOUVEAU_FICHIER_BIXI):
    print("❌ Erreur : Fichier bixi.csv introuvable.")
    exit()

df = pd.read_csv(NOUVEAU_FICHIER_BIXI)
df_top = df.sort_values(by='occurrences', ascending=False).head(NOMBRE_TRAJETS_A_ANALYSER)

# 2. CHARGEMENT CARTE
print("🌍 Téléchargement de la carte de Montréal (peut prendre 1-2 min)...")
try:
    G = ox.graph_from_place("Montreal, Canada", network_type='bike')
except Exception as e:
    print(f"❌ Erreur OSMnx : {e}")
    exit()

# Pondération (on préfère les pistes cyclables)
for u, v, k, data in G.edges(keys=True, data=True):
    type_route = data.get('highway', '')
    length = data.get('length', 0)
    if isinstance(type_route, list): type_route = type_route[0]
    
    # Si c'est une piste, le "coût" est normal. Sinon, on multiplie par 2.5 (on l'évite)
    if type_route in ['cycleway', 'path', 'track'] or 'cycleway' in data:
        data['cout_prefere'] = length
    else:
        data['cout_prefere'] = length * 2.5 

# 3. ROUTING
print("⚙️ Calcul des itinéraires en cours...")
usage_rues = {} 
compteur = 0

for index, row in df_top.iterrows():
    compteur += 1
    if compteur % 100 == 0: print(f"   Traitement : {compteur}/{NOMBRE_TRAJETS_A_ANALYSER}")
    
    try:
        # Trouver les noeuds les plus proches (C'est ici que scikit-learn est utilisé)
        orig = ox.nearest_nodes(G, row['STARTSTATIONLONGITUDE'], row['STARTSTATIONLATITUDE'])
        dest = ox.nearest_nodes(G, row['ENDSTATIONLONGITUDE'], row['ENDSTATIONLATITUDE'])
        
        if orig != dest:
            route = nx.shortest_path(G, orig, dest, weight='cout_prefere')
            volume = row['occurrences']
            
            # On compte le passage sur chaque segment de rue
            for i in range(len(route) - 1):
                u, v = route[i], route[i+1]
                edge_key = tuple(sorted((u, v))) # Clé unique pour le segment
                
                if edge_key in usage_rues:
                    usage_rues[edge_key] += volume
                else:
                    usage_rues[edge_key] = volume
    except Exception:
        continue # Si un trajet échoue, on passe au suivant sans planter

# 4. EXPORT
print("💾 Création du fichier GeoJSON final...")
geometries = []
volumes = []
noms_rues = []

for (u, v), vol in usage_rues.items():
    try:
        # Récupération des données du segment (géométrie + nom)
        if G.has_edge(u, v): edge_data = G.get_edge_data(u, v)[0]
        elif G.has_edge(v, u): edge_data = G.get_edge_data(v, u)[0]
        else: continue

        if 'geometry' in edge_data: geom = edge_data['geometry']
        else:
            p1 = Point(G.nodes[u]['x'], G.nodes[u]['y'])
            p2 = Point(G.nodes[v]['x'], G.nodes[v]['y'])
            geom = LineString([p1, p2])
            
        name = edge_data.get('name', 'Inconnu')
        if isinstance(name, list): name = name[0]
            
        geometries.append(geom)
        volumes.append(vol)
        noms_rues.append(str(name))
    except:
        pass

if len(geometries) > 0:
    gdf_flux = gpd.GeoDataFrame({
        'nom_rue': noms_rues, 
        'volume': volumes, 
        'geometry': geometries
    }, crs="EPSG:4326")

    gdf_flux.to_file(OUTPUT_GEOJSON, driver="GeoJSON")
    print(f"✅ SUCCÈS ! Fichier '{OUTPUT_GEOJSON}' généré avec {len(gdf_flux)} segments de rue.")
else:
    print("❌ Échec : Aucun segment n'a été généré.")