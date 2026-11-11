# Retrospectiva de incidente (sin culpa)

> El objetivo es aprender cómo falló el **sistema**, no buscar a quién culpar. Las personas toman decisiones razonables con la información que tienen; si un error fue posible, el sistema lo permitió.

## Resumen

| | |
|---|---|
| **Fecha** | |
| **Duración** | inicio → recuperación |
| **Severidad** | page / ticket |
| **Servicios afectados** | |
| **Presupuesto de error consumido** | |

**En una frase:** qué pasó y qué vieron los usuarios.

## Línea de tiempo

| Hora | Evento |
|---|---|
| | Cambio que inició el problema |
| | Se dispara la alerta |
| | Alguien la atiende |
| | Mitigación aplicada |
| | Alerta resuelta |

**Tiempo para detectar:** · **Tiempo para mitigar:**

## Impacto

- ¿Qué porcentaje de solicitudes falló?
- ¿Qué funciones siguieron funcionando?

## Causa

¿Qué cambió? ¿Por qué ese cambio provocó el problema? ¿Por qué no lo detectaron las pruebas o el CI?

## Qué funcionó bien

## Qué se puede mejorar

## Acciones

| Acción | Tipo (prevenir / detectar / mitigar) | Responsable | Fecha |
|---|---|---|---|
| | | | |

---

## Ejemplo: ensayo de la demo

| | |
|---|---|
| **Duración** | ≈ 4 min |
| **Servicios afectados** | `market-data` → `/api/market/quotes` |

**En una frase:** un cambio de configuración (`FAILURE_RATE=0.5`) hizo que market-data fallara la mitad de las veces; la tabla "Mi lista" mostró datos de ejemplo, el resto de la app siguió funcionando.

**Qué funcionó bien:**

- La alerta se disparó antes de que alguien reportara el problema.
- La API respondió 503 en lugar de caerse: suscripciones y dashboard no se afectaron.
- `rollout history` mostró el cambio exacto y `rollout undo` lo revirtió en segundos.

**Acciones:**

| Acción | Tipo |
|---|---|
| Los cambios de configuración pasan por PR y CI, no por `kubectl set env` | Prevenir |
| Smoke test automático después de cada despliegue | Detectar |
