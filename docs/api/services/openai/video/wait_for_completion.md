# Esperar Finalización - Sora

**Endpoint:** Polling sobre `GET /v1/videos/{video_id}`
**Función:** `wait_for_completion(video_id: str, max_wait_seconds: int = 600, poll_interval: int = 10) -> dict`

---

## Descripción

Espera a que un video generado se complete, realizando **polling** cada `poll_interval` segundos hasta `max_wait_seconds`.

---

## Parámetros principales

| Parámetro        | Tipo | Descripción                                         |
| ---------------- | ---- | --------------------------------------------------- |
| video_id         | str  | ID del video a esperar                              |
| max_wait_seconds | int  | Máximo tiempo de espera en segundos (default: 600)  |
| poll_interval    | int  | Intervalo entre consultas en segundos (default: 10) |

---

## Ejemplo (Python)

```python
final_status = client.wait_for_completion("video_123")
print(final_status['status'])
```

---

## Notas importantes

* Retorna el estado final (`completed`, `failed`, `timeout`).
* Permite usar `get_video_status` internamente para verificar progreso.
