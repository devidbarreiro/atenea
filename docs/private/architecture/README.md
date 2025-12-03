# 🏛️ Arquitectura de Atenea

> Entendimiento profundo del diseño del sistema

## Overview

Atenea sigue una **arquitectura orientada a servicios** con separación clara de responsabilidades.

## Documentos en esta Sección

1. **[Layers](layers.md)** - Arquitectura de 4 capas
2. **[CBV Pattern](cbv-pattern.md)** - Class-Based Views
3. **[Service Layer](service-layer.md)** - Business logic
4. **[Forms Validation](forms-validation.md)** - Sistema de validación
5. **[Workflows](workflows.md)** - Flujos principales
6. **[Design Decisions](design-decisions.md)** - ADRs

## Diagrama de Alto Nivel

```
┌─────────────┐
│  Templates  │ ← Presentación
└──────┬──────┘
       ↓
┌─────────────┐
│    Views    │ ← HTTP Handling
└──────┬──────┘
       ↓
┌─────────────┐
│  Services   │ ← Business Logic
└──────┬──────┘
       ↓
┌─────────────┐
│   Models    │ ← Data Layer
└─────────────┘
```

## Principios Arquitectónicos

1. **Separation of Concerns**
2. **Single Responsibility**
3. **DRY (Don't Repeat Yourself)**
4. **Testability First**
5. **Scalability**

## Ver También

- [Full Architecture Document](../../ARQUITECTURA_REFACTORIZADA.md)

