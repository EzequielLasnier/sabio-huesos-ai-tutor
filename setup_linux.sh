#!/bin/bash
#
# setup_linux.sh
# Script de configuración para "Sabio Huesos" en Linux Mint / Ubuntu
#
# Este script:
# 1. Actualiza los paquetes del sistema.
# 2. Instala Python 3.11, venv y las herramientas de desarrollo de Python.
# 3. Instala la biblioteca 'portaudio' (dependencia de PyAudio).
# 4. Pregunta al usuario si prefiere 'venv' o 'conda'.
# 5. Crea el entorno virtual seleccionado ('venv' o 'sabio_huesos' para conda).
# 6. Instala las dependencias de Python desde requirements.txt en ese entorno.
#

echo "--- Iniciando configuración de Sabio Huesos para Linux ---"

# 1 y 2: Actualizar e instalar Python y herramientas
echo "[PASO 1/5] Actualizando paquetes e instalando Python 3.11..."
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# 3: Instalar dependencias de sistema (PortAudio)
echo "[PASO 2/5] Instalando bibliotecas de sistema (PortAudio)..."
sudo apt-get install -y portaudio19-dev

# 4: Preguntar al usuario por el tipo de entorno
echo "[PASO 3/5] Seleccione el tipo de entorno virtual:"
read -p "¿Qué entorno deseas usar? [venv/conda] (default: venv): " ENV_CHOICE

# Normalizar la entrada (convertir a minúsculas)
ENV_CHOICE=$(echo "$ENV_CHOICE" | tr '[:upper:]' '[:lower:]')

# 5 y 6: Crear entorno e instalar dependencias
if [[ "$ENV_CHOICE" == "conda" ]]; then
    # --- Opción CONDA ---
    echo "[PASO 4/5] Creando entorno Conda 'sabio_huesos'..."
    if ! command -v conda &> /dev/null; then
        echo "❌ Error: Comando 'conda' no encontrado."
        echo "Por favor, instala Anaconda o Miniconda primero y vuelve a intentarlo."
        exit 1
    fi
    conda create --name sabio_huesos python=3.11 -y
    
    echo "[PASO 5/5] Instalando dependencias de Python en 'sabio_huesos'..."
    # Usamos 'conda run' para ejecutar pip dentro del entorno sin necesidad de activarlo
    conda run -n sabio_huesos pip install -r requirements.txt
    
    echo "--- ¡Configuración con Conda completada! ---"
    echo ""
    echo "Para activar el entorno, ejecuta:"
    echo "conda activate sabio_huesos"

elif [[ "$ENV_CHOICE" == "venv" || "$ENV_CHOICE" == "" ]]; then
    # --- Opción VENV (Default) ---
    echo "[PASO 4/5] Creando entorno virtual 'venv'..."
    python3.11 -m venv venv
    
    echo "[PASO 5/5] Instalando dependencias de Python en 'venv'..."
    ./venv/bin/pip install -r requirements.txt
    
    echo "--- ¡Configuración con venv completada! ---"
    echo ""
    echo "Para activar el entorno, ejecuta:"
    echo "source venv/bin/activate"

else
    echo "❌ Opción no válida. Por favor, ejecuta el script de nuevo y elige 'venv' o 'conda'."
    exit 1
fi

echo ""
echo "No olvides colocar tu 'service-account-key.json' y 'anatomia_huesos.pdf' en las carpetas correctas."