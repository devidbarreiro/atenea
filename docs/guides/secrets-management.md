# 🔐 Guía de Gestión de Secretos para el Equipo

Esta guía te ayudará a elegir e implementar una solución segura para compartir claves API con tu equipo.

## 📊 Comparación de Opciones

### 1. **Doppler** ⭐ RECOMENDADO
**Ideal para:** Equipos pequeños/medianos, desarrollo rápido

**Ventajas:**
- ✅ Gratis hasta 5 usuarios
- ✅ Interfaz web intuitiva
- ✅ CLI fácil de usar
- ✅ Sincronización automática con `.env`
- ✅ Control de acceso por proyecto/entorno
- ✅ Historial y auditoría
- ✅ Integración con Render, GitHub Actions, etc.

**Desventajas:**
- ⚠️ Requiere cuenta externa
- ⚠️ Límite en plan gratuito

**Costo:** Gratis hasta 5 usuarios, $7/usuario/mes después

---

### 2. **GCP Secret Manager** 
**Ideal para:** Si ya usas Google Cloud extensivamente

**Ventajas:**
- ✅ Ya tienes cuenta GCP
- ✅ Integración nativa con GCP
- ✅ Muy seguro y escalable
- ✅ Control de acceso granular (IAM)
- ✅ Versionado de secretos

**Desventajas:**
- ⚠️ CLI más complejo
- ⚠️ Requiere configuración de IAM
- ⚠️ Menos intuitivo para equipos no técnicos

**Costo:** ~$0.06 por secreto/mes + $0.03 por 10,000 operaciones

---

### 3. **1Password Secrets Automation**
**Ideal para:** Si ya usas 1Password para contraseñas

**Ventajas:**
- ✅ Integración con 1Password existente
- ✅ Interfaz familiar
- ✅ Muy seguro

**Desventajas:**
- ⚠️ Más caro
- ⚠️ Menos enfocado en desarrollo

**Costo:** Desde $7.99/usuario/mes

---

### 4. **Bitwarden Secrets Manager**
**Ideal para:** Equipos que prefieren open source

**Ventajas:**
- ✅ Open source
- ✅ Puede ser self-hosted
- ✅ Familiar si usas Bitwarden

**Desventajas:**
- ⚠️ Menos maduro para secretos de desarrollo
- ⚠️ Requiere más configuración

**Costo:** Gratis (self-hosted) o $3/usuario/mes

---

## 🚀 Implementación Recomendada: Doppler

### Paso 1: Crear cuenta y proyecto

1. Ve a [doppler.com](https://doppler.com) y crea una cuenta
2. Crea un nuevo proyecto llamado `atenea`
3. Crea 3 configuraciones (environments):
   - `dev` (desarrollo)
   - `staging` (pruebas)
   - `prod` (producción)

### Paso 2: Instalar CLI

```bash
# macOS
brew install dopplerhq/cli/doppler

# Linux
curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | sudo apt-key add -
echo "deb https://packages.doppler.com/public/cli/deb/debian any-version main" | sudo tee /etc/apt/sources.list.d/doppler-cli.list
sudo apt-get update && sudo apt-get install doppler

# Verificar instalación
doppler --version
```

### Paso 3: Autenticar

```bash
doppler login
```

### Paso 4: Sincronizar secretos

```bash
# Navegar al proyecto
cd /Users/david/dev/atenea

# Configurar proyecto y entorno
doppler setup --project atenea --config dev

# Subir secretos desde tu archivo .env (si ya tienes uno)
doppler secrets upload .env

# O agregar secretos manualmente
doppler secrets set OPENAI_API_KEY="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"
doppler secrets set GEMINI_API_KEY="AIzaSyCm6r39yoXxWJFks9RxWhzj7acA5KNFT9k"
# ... etc
```

### Paso 5: Descargar secretos localmente

```bash
# Generar .env desde Doppler
doppler secrets download --no-file --format env > .env

# O usar directamente sin archivo .env (más seguro)
doppler run -- python manage.py runserver
```

### Paso 6: Compartir con el equipo

1. En Doppler web, ve a tu proyecto
2. Click en "Access" → "Invite Members"
3. Invita a los miembros del equipo por email
4. Asigna permisos (Read, Write, Admin)

---

## 🔧 Integración con Render

### Opción A: Sincronización manual

1. En Doppler, ve a tu proyecto → `prod` config
2. Click en "Sync" → "Render"
3. Sigue las instrucciones para conectar tu cuenta de Render
4. Selecciona qué secretos sincronizar

### Opción B: Script de sincronización

Ver `scripts/sync-secrets-to-render.sh` (crear si es necesario)

---

## 🔧 Integración con GCP Secret Manager

Si prefieres usar GCP Secret Manager:

### Paso 1: Habilitar API

```bash
gcloud services enable secretmanager.googleapis.com
```

### Paso 2: Crear secretos

```bash
# Crear un secreto
echo -n "tu-api-key-aqui" | gcloud secrets create OPENAI_API_KEY \
  --data-file=- \
  --replication-policy="automatic" \
  --project=proeduca-472312

# O desde archivo
gcloud secrets create OPENAI_API_KEY \
  --data-file=api-key.txt \
  --replication-policy="automatic" \
  --project=proeduca-472312
```

### Paso 3: Dar acceso al equipo

```bash
# Dar acceso a un usuario
gcloud secrets add-iam-policy-binding OPENAI_API_KEY \
  --member="user:email@example.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=proeduca-472312
```

### Paso 4: Usar en código

```python
# Instalar dependencia
# pip install google-cloud-secret-manager

from google.cloud import secretmanager

def get_secret(secret_id: str, project_id: str = "proeduca-472312") -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Usar
OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
```

---

## 📝 Checklist de Migración

- [ ] Elegir herramienta (recomendado: Doppler)
- [ ] Crear cuenta y proyecto
- [ ] Instalar CLI
- [ ] Subir todas las claves API
- [ ] Configurar acceso del equipo
- [ ] Actualizar documentación del equipo
- [ ] Configurar integración con Render/GCP
- [ ] Eliminar `API_KEYS_ORGANIZED.md` del repositorio (solo local)
- [ ] Añadir `API_KEYS_ORGANIZED.md` al `.gitignore`
- [ ] Probar que todo funciona en desarrollo
- [ ] Probar en staging/producción

---

## 🛡️ Mejores Prácticas

1. **Nunca commitees secretos** - Ya está en `.gitignore`, pero verifica
2. **Usa diferentes secretos por entorno** - dev, staging, prod
3. **Rota secretos regularmente** - Especialmente si se comprometen
4. **Audita accesos** - Revisa quién accede a qué
5. **Principio de menor privilegio** - Solo da acceso necesario
6. **No compartas por chat/email** - Usa siempre la herramienta de secretos

---

## 🔄 Scripts Útiles

### Sincronizar desde Doppler a .env local

```bash
#!/bin/bash
# scripts/sync-doppler-to-env.sh

doppler secrets download --no-file --format env > .env
echo "✅ Secretos sincronizados desde Doppler"
```

### Listar todos los secretos (sin valores)

```bash
doppler secrets
```

### Comparar secretos entre entornos

```bash
doppler secrets --config dev
doppler secrets --config prod
```

---

## 📚 Recursos

- [Doppler Docs](https://docs.doppler.com)
- [GCP Secret Manager Docs](https://cloud.google.com/secret-manager/docs)
- [1Password Secrets Automation](https://1password.com/secrets/)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

