import uvicorn
import os
from dotenv import load_dotenv

def main():
    """Lancer l'application FastAPI"""
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Configuration
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    print(f"""
    ================================
    Cap Table Management Application
    ================================
    
    🚀 Démarrage de l'application...
    
    📍 URL: http://{host}:{port}
    📚 Documentation: http://{host}:{port}/docs
    📖 ReDoc: http://{host}:{port}/redoc
    
    Appuyez sur Ctrl+C pour arrêter
    ================================
    """)
    
    try:
        # Lancer l'application
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=debug,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Application arrêtée par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur lors du démarrage: {e}")
        print("\nVérifiez que:")
        print("1. Le port n'est pas déjà utilisé")
        print("2. Les bases de données sont accessibles")
        print("3. Les migrations ont été exécutées")

if __name__ == "__main__":
    main()
