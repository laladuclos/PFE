"""
Script pour générer des données de démonstration
Utiliser si certains fichiers CSV sont manquants
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def generer_donnees_demo():
    """Génère des fichiers CSV de démonstration"""
    
    print("🔄 Génération des données de démonstration...")
    
    # 1. Générer données comptage vélo
    print("📊 Génération comptage_velo_2025.csv...")
    dates = pd.date_range(start='2025-01-01', end='2025-12-31', freq='D')
    comptage_data = []
    
    for date in dates:
        for heure in range(24):
            comptage_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'heure': f"{heure:02d}:00:00",
                'id_compteur': np.random.choice([100054073, 100003032, 100007390]),
                'nb_passages': np.random.poisson(50) if 7 <= heure <= 19 else np.random.poisson(10),
                'longitude': -73.58 + np.random.uniform(-0.05, 0.05),
                'latitude': 45.52 + np.random.uniform(-0.05, 0.05)
            })
    
    df_comptage = pd.DataFrame(comptage_data)
    df_comptage.to_csv('comptage_velo_2025.csv', index=False)
    print(f"✅ Créé: comptage_velo_2025.csv ({len(df_comptage)} lignes)")
    
    # 2. Générer données accidents
    print("🚨 Génération collisions_routieres.csv...")
    accidents_data = []
    
    for year in range(2020, 2026):
        n_accidents = np.random.randint(300, 500)
        
        for _ in range(n_accidents):
            date = datetime(year, 1, 1) + timedelta(days=np.random.randint(0, 365))
            
            accidents_data.append({
                'DT_ACCDN': date.strftime('%Y-%m-%d %H:%M:%S'),
                'LOC_LAT': 45.52 + np.random.uniform(-0.1, 0.1),
                'LOC_LONG': -73.58 + np.random.uniform(-0.1, 0.1),
                'NB_BICYCLETTE': 1,
                'GRAVITE': np.random.choice(['Léger', 'Grave', 'Mortel'], p=[0.7, 0.25, 0.05]),
                'NB_VICTIMES_VELO': 1
            })
    
    df_accidents = pd.DataFrame(accidents_data)
    df_accidents.to_csv('collisions_routieres.csv', index=False)
    print(f"✅ Créé: collisions_routieres.csv ({len(df_accidents)} lignes)")
    
    # 3. Générer données trajets BIXI
    print("🚴 Génération bixi.csv...")
    stations = [
        ('Métro Pie-IX', 45.554375, -73.55138),
        ('du Mont-Royal / Clark', 45.51941, -73.58685),
        ('Métro Joliette', 45.546993, -73.551155),
        ('Berri / Cherrier', 45.519268, -73.5693),
        ('Métro Verdun', 45.459373, -73.57201)
    ]
    
    trajets_data = []
    
    for start in stations:
        for end in stations:
            if start != end:
                trajets_data.append({
                    'STARTSTATIONNAME': start[0],
                    'ENDSTATIONNAME': end[0],
                    'STARTSTATIONLATITUDE': start[1],
                    'STARTSTATIONLONGITUDE': start[2],
                    'ENDSTATIONLATITUDE': end[1],
                    'ENDSTATIONLONGITUDE': end[2],
                    'occurrences': np.random.randint(100, 5000)
                })
    
    df_trajets = pd.DataFrame(trajets_data)
    df_trajets.to_csv('bixi.csv', index=False)
    print(f"✅ Créé: bixi.csv ({len(df_trajets)} lignes)")
    
    # 4. Générer GeoJSON de flux (simplifié)
    print("🗺️  Génération flux_bixi_estimes.geojson...")
    
    flux_geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    rues = [
        ("Ontario Est", [[-73.58, 45.52], [-73.54, 45.52]]),
        ("Saint-Denis", [[-73.56, 45.50], [-73.56, 45.54]]),
        ("Rachel", [[-73.60, 45.53], [-73.56, 45.53]]),
        ("Berri", [[-73.57, 45.51], [-73.57, 45.53]]),
        ("Mont-Royal", [[-73.59, 45.52], [-73.56, 45.52]])
    ]
    
    for nom_rue, coords in rues:
        flux_geojson["features"].append({
            "type": "Feature",
            "properties": {
                "NOM_RUE": nom_rue,
                "VOLUME": np.random.randint(1000, 10000),
                "COULEUR": "#FF0000" if np.random.random() > 0.5 else "#00FF00"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        })
    
    with open('flux_bixi_estimes.geojson', 'w') as f:
        json.dump(flux_geojson, f)
    
    print(f"✅ Créé: flux_bixi_estimes.geojson ({len(flux_geojson['features'])} segments)")
    
    print("\n✨ Toutes les données de démonstration ont été générées avec succès!")
    print("\n📁 Fichiers créés:")
    print("   • comptage_velo_2025.csv")
    print("   • collisions_routieres.csv")
    print("   • bixi.csv")
    print("   • flux_bixi_estimes.geojson")
    print("\n🚀 Vous pouvez maintenant lancer: streamlit run dashboard_insane.py")

if __name__ == "__main__":
    generer_donnees_demo()