import json
import os

def fix_dashboard_titles():
    dashboard_files = [
        "orchestration_arbitrage_legs.json",
        "orchestration_decision_conf.json", 
        "orchestration_ia_health.json",
        "orchestration_slots_timeline.json",
        "orchestration_venue_health.json"
    ]
    
    for file in dashboard_files:
        filepath = file  # Já estamos na pasta dashboards
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"Processando: {file}")
            
            # Garantir que tem título
            if not data.get('title'):
                new_title = file.replace('.json', '').replace('_', ' ').title()
                data['title'] = new_title
                print(f"  ✅ Título corrigido: {new_title}")
            else:
                print(f"  ✅ Título já existe: {data['title']}")
            
            # Garantir que tem UID único
            if not data.get('uid'):
                new_uid = file.replace('.json', '').replace('_', '-')
                data['uid'] = new_uid
                print(f"  ✅ UID corrigido: {new_uid}")
            else:
                print(f"  ✅ UID já existe: {data.get('uid')}")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"  ✅ Arquivo salvo: {file}")
        else:
            print(f"  ❌ Arquivo não encontrado: {file}")

if __name__ == "__main__":
    print("Iniciando correção de títulos dos dashboards...")
    fix_dashboard_titles()
    print("Correção concluída!")
