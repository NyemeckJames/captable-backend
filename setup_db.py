import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

def create_database():
    """Créer les bases de données nécessaires"""
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Configuration par défaut
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
    
    databases_to_create = ["captable", "captable_test"]
    
    try:
        print(f"Connexion a PostgreSQL sur {DB_HOST}:{DB_PORT} en tant que {DB_USER}")
        # Connexion à la base postgres par défaut
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        for db_name in databases_to_create:
            try:
                # Vérifier si la base existe déjà
                cursor.execute(
                    "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
                    (db_name,)
                )
                exists = cursor.fetchone()
                
                if not exists:
                    cursor.execute(f'CREATE DATABASE "{db_name}"')
                    print(f"✓ Base de données '{db_name}' créée avec succès")
                else:
                    print(f"✓ Base de données '{db_name}' existe déjà")
                    
            except Exception as e:
                print(f"✗ Erreur lors de la création de '{db_name}': {e}")
                
        cursor.close()
        conn.close()
        print("\n✓ Configuration des bases de données terminée")
        
    except Exception as e:
        print(f"✗ Erreur de connexion à PostgreSQL: {e}")
        print("\nVérifiez que:")
        print("1. PostgreSQL est démarré")
        print("2. Les paramètres de connexion sont corrects dans .env")
        print("3. L'utilisateur a les droits de création de base de données")
        return False
        
    return True

if __name__ == "__main__":
    print("Création des bases de données...")
    create_database()
