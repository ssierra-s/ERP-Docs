
# ERP-Docs 📂

Módulo de gestión de documentos para ERP en **Django + DRF** con almacenamiento en **MinIO/S3** y validación jerárquica de aprobaciones.

Se busca diseñar e implementar (en Django) un módulo de gestión de documentos para un ERP que permita almacenar archivos en la nube (bucket), referenciarlos en base de datos y validarlos mediante un flujo jerárquico de aprobaciones.

## Base de datos

La base de datos se desplego en Supabase que esta basada en postgre

## 🚀 Deployment

Para correr el proyecto ejecutamos

```bash
  python manage.py runserver
```


## Variables de entorno

Crea un archivo `.env` en la raíz del proyecto con los valores de configuración:

```env
# Configuración de MinIO
MINIO_ACCESS_KEY_ID=changeme
MINIO_SECRET_ACCESS_KEY=changeme123
MINIO_REGION=us-east-1
MINIO_BUCKET_NAME=erp-docs-bucket
FILE_URL_TTL_SECONDS=900
MINIO_ENDPOINT_URL=http://localhost:9000

```

## Docker-compose.yml mínimo:
```bash
  version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_USER: postgres
      POSTGRES_DB: erpdocs
    ports:
      - "5432:5432"  # Para acceder a Postgres
    volumes:
      - pgdata:/var/lib/postgresql/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: changeme
      MINIO_ROOT_PASSWORD: changeme123
    ports:
      - "9000:9000"  # Para acceso al servicio de almacenamiento
      - "9001:9001"  # Para acceso a la consola web
    volumes:
      - minio:/data

volumes:
  pgdata:
  minio:

```

## 🛠️ Migraciones 
Migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```
## 📡 Ejemplos de requests

En el repositorio se encuentra un .json que

#### Autenticación: todos los endpoints requieren token de usuario.
Usa Authorization: Token <token> en los headers.


---

### Crear empresa

```http
POST /api/companies/
```

| Header         | Type     | Description                    |
| :------------- | :------- | :----------------------------- |
| `Content-Type` | `string` | **Required**. application/json |

**Body**

```json
{
  "legal_name": "Mi Empresa SA"
}
```

---

### Generar URL firmada para subir documento

```http
POST /api/documents/presign-upload/
```

| Header          | Type     | Description                          |
| :-------------- | :------- | :----------------------------------- |
| `Content-Type`  | `string` | **Required**. application/json       |
| `Authorization` | `string` | **Required**. Token de autenticación |

**Body**

```json
{
  "company_id": "0c61c4ef-ab01-4919-88a1-493bc30fa7ea",
  "bucket_key": "companies/0c61c4ef-ab01-4919-88a1-493bc30fa7ea/vehicles/eb606477-a1ff-4cd7-9acf-eed0c4b24fe1/docs/soat-2025.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 123456
}
```

---

### Registrar documento en sistema

```http
POST /api/companies/members/
```

| Header          | Type     | Description                          |
| :-------------- | :------- | :----------------------------------- |
| `Content-Type`  | `string` | **Required**. application/json       |
| `Authorization` | `string` | **Required**. Token de autenticación |

**Body**

```json
{
  "company_id": "0c61c4ef-ab01-4919-88a1-493bc30fa7ea",
  "entity": { "entity_type": "vehicle", "entity_id": "eb606477-a1ff-4cd7-9acf-eed0c4b24fe1" },
  "document": {
    "name": "soat.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 123456,
    "bucket_key": "companies/0c61c4ef-ab01-4919-88a1-493bc30fa7ea/vehicles/eb606477-a1ff-4cd7-9acf-eed0c4b24fe1/docs/soat-2025.pdf"
  },
  "validation_flow": {
    "enabled": true,
    "steps": [
      { "order": 1, "approver_user_id": "1" },
      { "order": 2, "approver_user_id": "2" },
      { "order": 3, "approver_user_id": "3" }
    ]
  }
}
```

---

### Subir archivo al bucket (PUT presignado)

```http
PUT /erp-docs-bucket/companies/{company_id}/vehicles/{vehicle_id}/docs/{file_name}.pdf
```

| Header         | Type     | Description                   |
| :------------- | :------- | :---------------------------- |
| `Content-Type` | `string` | **Required**. application/pdf |

**Body**
Archivo binario PDF.

---

### Descargar documento

```http
GET /api/documents/{document_id}/download
```

| Header          | Type     | Description                          |
| :-------------- | :------- | :----------------------------------- |
| `Content-Type`  | `string` | application/json                     |
| `Authorization` | `string` | **Required**. Token de autenticación |

---

### Subida directa (form-data)

```http
POST /api/documents/direct-upload
```

| Header          | Type     | Description                          |
| :-------------- | :------- | :----------------------------------- |
| `Content-Type`  | `string` | multipart/form-data                  |
| `Authorization` | `string` | **Required**. Token de autenticación |

**Form Data**

* `company_id`: string
* `entity_type`: string
* `entity_id`: string
* `file`: archivo PDF

---

### Registrar miembro en empresa

```http
POST /api/companies/members/
```

| Header          | Type     | Description                          |
| :-------------- | :------- | :----------------------------------- |
| `Content-Type`  | `string` | **Required**. application/json       |
| `Authorization` | `string` | **Required**. Token de autenticación |

**Body**

```json
{
  "company": "313bae24e359df4a06db8cf34a923c72ba78461f",
  "user_id": 2,
  "name": "Usuario L4",
  "approval_level": 2
}
```

---

### Registrar entidad

```http
POST /api/entities/
```

| Header          | Type     | Description                          |
| :-------------- | :------- | :----------------------------------- |
| `Content-Type`  | `string` | **Required**. application/json       |
| `Authorization` | `string` | **Required**. Token de autenticación |

**Body**

```json
{
  "company": "1a95e460-937d-4746-9b1b-20665266fe41",
  "entity_type": "personal",
  "external_id": "df7f8b16-5f7a-4220-b4ee-c94fe8ef74a8"
}
```

---

### Aprobar o rechazar documento

```http
POST /api/documents/{document_id}/approve
```

| Header          | Type     | Description                          |
| :-------------- | :------- | :----------------------------------- |
| `Content-Type`  | `string` | **Required**. application/json       |
| `Authorization` | `string` | **Required**. Token de autenticación |

**Body**

```json
{
  "actor_user_id": "3",
  "reason": "Cumple requisitos."
}
```

---




## 📖 Notas

Tamaño máximo de archivo: 30 MB.

Tipos permitidos: PDF, JPG, PNG.

Cada acción de validación registra auditoría (approve/reject).

Se registran también eventos de subida y descarga (DocumentEvent).

Usa la consola de MinIO en http://localhost:9001
 para verificar archivos.



## Authors

- [@ssierra](https://github.com/ssierra-s)

