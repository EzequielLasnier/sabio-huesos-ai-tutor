# Asistente de Voz "Sabio Huesos" con RAG

Características

- Conversación en Tiempo Real: Interacción fluida de voz a voz.
- Base de Conocimiento Personalizada: Responde preguntas utilizando la información del archivo anatomia_huesos.pdf.
- Arquitectura Segura: Implementa un backend para generar tokens de corta duración, y toda la autenticación se centraliza a través de una única clave de cuenta de servicio de Google Cloud.
- Rendimiento Robusto: Utiliza asyncio para concurrencia y multiprocessing para tareas pesadas de RAG, asegurando que la conversación no se interrumpa.

## Estructura del Proyecto

Estructura del Proyecto /Asistente_RAG/ | |-- /data/ |   |-- anatomia_huesos.pdf | |-- /faiss_index/           \<-- (Se crea automáticamente en la primera ejecución) | |-- langchain_client.py |-- token_server.py         \<-- Servidor de tokens |-- voice_gemini_bot.py \<-- Cliente de voz |-- requirements.txt |-- service-account-key.json  \<-- (Debes añadirlo tú) |-- README.md

## Instalación y Configuración

Sigue estos pasos para poner en marcha el asistente en una nueva PC.

- Prerrequisitos: Python 3.9 o superior.
- Un micrófono y altavoces configurados en el sistema.
- Acceso a la consola de Google Cloud para crear credenciales.
- Puedes usar venv (incluido en Python) o conda para gestionar el entorno.

### 1. Clonar o Descomprimir el Proyecto

Pasos Clonar o Descomprimir el Proyecto: Obtén todos los archivos y colócalos en una carpeta en tu computadora.

### 2. Crear y Activar un Entorno Virtual

#### Opción A: En Linux Mint / Ubuntu

Hemos incluido un script para automatizar este proceso.

1. Dale permisos de ejecución al script:

    ```sh
    chmod +x setup_linux.sh
    ```

2. Ejecuta el script:

    ```sh
    ./setup_linux.sh
    ```

3. Activa el entorno virtual creado:

    ```sh
    source venv/bin/activate
    ```

#### Opción B: En Windows

Usa `venv` (estándar de Python):

```cmd
# Navega a la carpeta del proyecto
cd Asistente_RAG

# Crea el entorno virtual
python -m venv venv

# Activa el entorno virtual
.\venv\Scripts\activate

#### Opción C: Usando conda (Multiplataforma)

# Crea el entorno virtual
conda create --name sabio_huesos python=3.11

# Activa el entorno virtual
conda activate sabio_huesos

### 3. Instalar las Dependencias (si no usaste el script de Linux)

Si no usaste el script setup_linux.sh (por ejemplo, en Windows o Conda), instala las librerías manualmente:

pip install -r requirements.txt

## 4. Configurar una Cuenta de Servicio de Google Cloud:

Este proyecto utiliza tokens seguros de corta duración. Para ello, necesitas una clave de cuenta de servicio de Google Cloud.  
     
   - Ve a la **Consola de Google Cloud -> IAM y Administración -> Cuentas de servicio**.  
   - Crea una **nueva cuenta de servicio**.  
   - Asígnale el rol de **"Usuario de API de Vertex AI"**.  
   - En la pestaña "Claves" de la cuenta, crea una **nueva clave de tipo JSON** y descárgala.  
   - Renombra el archivo descargado a `service-account-key.json` y colócalo en la carpeta raíz del proyecto.  
## Ejecución

    El sistema ahora consta de dos partes: el servidor de tokens y el cliente de voz. Deben ejecutarse en dos terminales separadas, ambas con el entorno virtual activado.

        1. **Terminal 1: Iniciar el Servidor de Tokens** Abre tu primera terminal, activa el entorno virtual (venv o conda) y ejecuta:  
     
            python token_server.py  
     
            El servidor se iniciará y esperará conexiones en `http://localhost:8000`.  
     
        2. **Terminal 2: Ejecutar el Cliente de Voz** Abre una segunda terminal, activa el mismo entorno virtual y ejecuta:  
     
            python voice_gemini_bot.py  
     
            El cliente primero solicitará un token al servidor y luego iniciará la conversación.  
     
        3. **Solución de Problemas (Troubleshooting)

            Error: ImportError: cannot import name 'genai' from 'google' Este error puede ser muy persistente y casi siempre se debe a una instalación corrupta o a un conflicto con el intérprete de Python. Sigue estos pasos en orden:  
         
            ### 2. Solución Intermedia: Limpieza de Caché y Recreación del Entorno

            Solución Intermedia: Limpieza de Caché y Recreación del Entorno Si el error persiste, la causa más probable es una caché de pip corrupta. Esta solución limpia todo desde cero.

                Paso A: Desactiva el entorno (si está activo):

                    deactivate

                Paso B: Limpia la caché de pip: Esto fuerza la descarga de nuevas versiones de las librerías.

                Paso C: Elimina el entorno virtual antiguo. El comando varía según tu terminal:

                En Símbolo del sistema (CMD):
                ```cmd
                rmdir /s /q venv
                ```

                En PowerShell:
                ```powershell
                Remove-Item -Recurse -Force venv
                ```

                En macOS/Linux:
                ```sh
                rm -rf venv
                ```

                rm -rf venv

                Paso D: Vuelve al "Paso 2 de la Configuración" y crea el entorno, actívalo e instala las dependencias de nuevo.

        4. Abre tus terminales y activa el entorno como de costumbre.

