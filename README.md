# Gestión de Incidencias EEASA - OCR & Web UI

Este proyecto es una plataforma completa para extraer, procesar y visualizar incidencias desde archivos PDF generados por el sistema ADMS, utilizando OCR (Tesseract) y una base de datos PostgreSQL, todo orquestado con Docker.

## 🚀 Requisitos Previos

Para levantar este proyecto en otra computadora, necesitas tener instalado:

1. **[Docker Desktop](https://www.docker.com/products/docker-desktop)** (o Docker Compose en Linux)
2. **Git** (para clonar el repositorio)

## 🛠️ Instalación y Despliegue

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/d4vhost/trafos_web.git
   cd trafos_web
   ```

2. **Colocar los archivos PDF:**
   Crea una carpeta llamada `pdfs_incidencias` en la raíz del proyecto (junto a `docker-compose.yml`) si no existe, y coloca dentro todos los reportes PDF de incidencias que desees procesar.
   ```bash
   mkdir pdfs_incidencias
   ```

3. **Levantar los contenedores (Base de datos y Backend):**
   ```bash
   docker compose up -d --build
   ```
   *Esto descargará las imágenes de PostgreSQL, Python, instalará Tesseract (OCR) y todas las librerías necesarias.*

4. **Acceder a la aplicación:**
   Una vez que los contenedores estén corriendo, abre tu navegador web e ingresa a:
   [http://localhost:8000](http://localhost:8000)

## ⚙️ Uso del Sistema

* **Procesamiento de PDFs:** Si acabas de agregar nuevos PDFs a la carpeta `pdfs_incidencias`, haz clic en el botón azul superior derecho **"Procesar Carpeta Completa"**. Esto escaneará mediante OCR los documentos y poblará la base de datos de manera automática.
* **Visor PDF Integrado:** Dentro de los "Detalles" de cada incidencia, tienes un botón que te permite abrir y corroborar el PDF original.
* **Coordenadas de Google Maps:** Al extraerse coordenadas del texto (ej. Latitud y Longitud), la plataforma generará automáticamente enlaces clickeables que abren la ubicación en Google Maps.

## 🗃️ Estructura del Proyecto

* `docker-compose.yml`: Orquestación de la DB PostgreSQL y el servidor FastAPI.
* `backend/main.py`: Rutas del servidor FastAPI y vistas (Jinja2).
* `backend/models.py`: Estructura de la base de datos (SQLAlchemy).
* `backend/pdf_parser.py`: Lógica de extracción Regex y procesamiento de imágenes (Tesseract OCR).
* `backend/templates/`: Vistas de la aplicación HTML (diseño minimalista).
* `pdfs_incidencias/`: Volumen donde el servidor lee los PDFs (no se suben al repositorio por privacidad).

## 🔄 Reiniciar Base de Datos (Opcional)

Si necesitas borrar todos los datos y crear las tablas desde cero, ejecuta:
```bash
docker exec sistema_backend python -c "from database import engine, Base; import models; Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine);"
```
