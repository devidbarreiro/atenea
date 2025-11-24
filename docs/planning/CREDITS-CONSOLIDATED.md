# Sistema de Créditos - Documentación Consolidada

> **NOTA**: Esta documentación ha sido movida a la documentación oficial.
> 
> - **Documentación técnica**: `docs/api/services/overview/credits-system.md`
> - **Guía de usuario**: `docs/api/services/overview/credits-user-guide.md`
> 
> Este archivo se mantiene como referencia histórica del proceso de planificación.

---

## Estado: ✅ COMPLETADO

El sistema de créditos y rate limiting está completamente implementado y funcionando.

### Archivos de Planificación (Históricos)

Los siguientes archivos en `docs/planning/` contienen información histórica del proceso de planificación:

- `credit-charging-comparison.md` - Comparación de estrategias
- `credit-charging-points.md` - Puntos de cobro identificados
- `credit-charging-strategy.md` - Estrategia elegida
- `credit-implementation-plan.md` - Plan de implementación
- `credits-command-example.md` - Ejemplos de comandos
- `feature-final-status.md` - Estado final del feature
- `feature-status.md` - Estado durante desarrollo
- `implementation-summary.md` - Resumen de implementación
- `pricing-investigation.md` - Investigación de precios
- `rate-limiting-credits-plan.md` - Plan inicial

### Documentación Oficial

Toda la documentación actualizada está en:

- `docs/api/services/overview/credits-system.md` - Documentación técnica completa
- `docs/api/services/overview/credits-user-guide.md` - Guía de usuario
- `docs/api/services/overview/README.md` - Índice de documentación

---

## Resumen Rápido

### Comandos Disponibles

```bash
# Asignar créditos
python manage.py add_credits <username> <amount> [--description "Descripción"]

# Ver créditos de usuario
python manage.py show_user_credits <username> [--detailed]

# Resetear uso mensual
python manage.py reset_monthly_credits [--dry-run]

# Listar todos los usuarios con créditos
python manage.py list_users_credits [--min-credits MIN] [--sort-by SORT] [--active-only]

# Estadísticas generales del sistema
python manage.py stats_credits [--period PERIOD]
```

### Precios Principales

- **Gemini Veo**: 50 créditos/segundo
- **Sora-2**: 10 créditos/segundo
- **Gemini Image**: 2 créditos/imagen
- **HeyGen Avatar V2**: 5 créditos/segundo
- **HeyGen Avatar IV**: 15 créditos/segundo
- **ElevenLabs**: 0.017 créditos/carácter
- **Vuela.ai**: 3 créditos/segundo (orientativo)

### Equivalencia

**100 créditos Atenea = 1 USD**

---

Para más información, consulta la documentación oficial en `docs/api/services/overview/`.

