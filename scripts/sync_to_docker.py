"""
Sync local browser session to Docker volume directory (./data/browser_profile).
Run this once after logging in on Windows to make Docker Desktop run already authenticated.
"""
import shutil
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent.parent
    local_temp = Path.home() / "AppData" / "Local" / "Temp" / "academic-pdf" / "browser_profile"
    docker_data = root / "data" / "browser_profile"

    if not local_temp.exists():
        print(f"[!] No se encontró el perfil local en: {local_temp}")
        print("    Inicia sesión primero en la app ejecutando 'python run.py'.")
        sys.exit(1)

    docker_data.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Copiando perfil local desde:\n  {local_temp}\nhacia:\n  {docker_data} ...")
    
    try:
        shutil.copytree(local_temp, docker_data, dirs_exist_ok=True, ignore=shutil.ignore_patterns("lockfile", "*.lock", "Singleton*"))
        print("[+] ¡Perfil sincronizado con éxito para Docker!")
        print("    Ahora puedes abrir Docker Desktop y pulsar 'Play' en el contenedor.")
    except Exception as e:
        print(f"[!] Error al copiar perfil: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
