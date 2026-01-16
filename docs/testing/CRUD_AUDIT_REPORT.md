# Auditoría CRUD + Integración Frontend–Backend (Local)

Fecha: 2026-01-16

- Backend (Flask): `http://127.0.0.1:8081/api/v1`
- Frontend (React/Vite): `C:\Users\Miguel\Documents\Flask Projects\Front_finca`
- Credenciales de prueba: `ADMIN_IDENT=1098`, `ADMIN_PASS=12345678Ab`

## Resumen ejecutivo

- Backend: CRUD **OK** para **18** recursos (batería Swagger + CRUD core + imágenes + flujo de usuarios).
- Frontend: build **OK**; formularios/listados alineados con Swagger; relaciones activadas con `?include_relations=true`; acciones **Eliminar** habilitadas en pantallas principales.
- Correcciones clave realizadas:
  - `GET /fields/` estaba lento por N+1 al calcular `animal_count` → optimizado con prefetch en una sola consulta.
  - `vaccines` no incluía relaciones en `include_relations` → agregado `diseases` y `route_administration_rel` para renderizar nombres en UI.
- Riesgo de seguridad (por requerimiento): registro público permite seleccionar rol (incluye `Administrador`). Recomendación: definir allowlist/flujo para roles elevados.

## Pruebas ejecutadas (local)

### Backend

- `python scripts/smoke_backend.py`
- `python scripts/test_all_endpoints_swagger.py` (250 endpoints en swagger; CRUD automatizado para 18 recursos)
- `python scripts/test_crud_core.py`
- `python scripts/test_images_crud.py`
- `python scripts/test_route_administration_api.py`
- `python scripts/test_user_flow.py`
- `python scripts/verify_security_basic.py`
- `python scripts/verify_security.py`
- `python scripts/audit_frontend_backend_endpoints.py` → `docs/testing/frontend_backend_endpoint_map.md`

### Frontend

- `npm run build` (en `Front_finca/`)

## Estado CRUD por entidad (backend)

Evidencia principal: salida `ok=true` en `scripts/test_all_endpoints_swagger.py` + `scripts/test_crud_core.py`.

| Tabla / Recurso | Estado CRUD | Observaciones | Prioridad |
| --- | --- | --- | --- |
| `species` | Correcto | - | Baja |
| `breeds` | Correcto | - | Baja |
| `animals` | Correcto | - | Baja |
| `fields` | Correcto | Optimizado `animal_count` (rendimiento) | Media |
| `food_types` | Correcto | - | Baja |
| `diseases` | Correcto | - | Baja |
| `controls` | Correcto | - | Baja |
| `animal_fields` | Correcto | - | Baja |
| `animal_diseases` | Correcto | - | Baja |
| `route_administrations` | Correcto | - | Baja |
| `medications` | Correcto | - | Baja |
| `treatments` | Correcto | - | Baja |
| `treatment_medications` | Correcto | - | Baja |
| `treatment_vaccines` | Correcto | - | Baja |
| `vaccines` | Correcto | `include_relations` ampliado (UI) | Media |
| `vaccinations` | Correcto | - | Baja |
| `users` | Correcto | `POST /users/public` (público) permite `role` | Alta (seguridad) |
| `genetic-improvements` | Correcto | - | Baja |
| `animal_images` | Correcto | CRUD verificado por `test_images_crud.py` | Baja |
| `activity_log` | No aplica CRUD directo | Audit/analytics (principalmente lectura) | Baja |
| `activity_daily_agg` | No aplica CRUD directo | Agregados (lectura) | Baja |

## Integración Frontend (CRUD extremo a extremo)

Cambios principales en `Front_finca/`:

- Alineación de nombres de campos con Swagger (forms y tablas).
- Listados que requieren nombres de relaciones ahora usan `?include_relations=true`.
- Acciones **Eliminar** habilitadas (GenericTable + páginas con cards).
- Soporte completo a `route_administrations` (types/service/hook) para medicamentos y vacunas.
- Registro publico actualizado para usar `/users/public` con seleccion de rol en `signUp`.

Entidades con UI CRUD verificada (build + wiring):

| Entidad (UI) | Estado CRUD UI | Endpoints principales | Notas |
| --- | --- | --- | --- |
| Species | Completo | `/species/` | Incluye eliminar en `speciesAndBreeds.tsx` |
| Breeds | Completo | `/breeds/` | Incluye eliminar en `speciesAndBreeds.tsx` |
| Animals | Completo | `/animals/` | Incluye eliminar en `animals.tsx` |
| Fields | Completo | `/fields/` | Listado usa `include_relations` |
| Diseases | Completo | `/diseases/` | Listado/crear/editar/eliminar OK |
| Controls | Completo | `/controls/` | `health_status` alineado |
| Food types | Completo | `/food_types/` | - |
| Medications | Completo | `/medications/` + `/route-administrations/` | Usa `route_administration_rel.name` |
| Treatments | Completo | `/treatments/` | Incluye eliminar en dropdown de cards |
| Vaccines | Completo | `/vaccines/` + `/route-administrations/` | Usa `route_administration_rel` + `type` |
| Vaccinations | Completo | `/vaccinations/` | `vaccination_date` alineado |
| AnimalFields | Completo | `/animal-fields/` | - |
| AnimalDiseases | Completo | `/animal-diseases/` | - |
| Genetic improvements | Completo | `/genetic-improvements/` | - |
| Users | Completo | `/users/` (protegido), `/users/public` (publico) | Alta/editar/eliminar en admin + registro publico en `docs/frontend/api-usage-guide-frontend.md` |

## Inventario de endpoints y cobertura del frontend

- Mapa generado: `docs/testing/frontend_backend_endpoint_map.md`
- Auditoria de vistas: `docs/testing/frontend_backend_view_audit.md`
- Resultado actual: 250 endpoints en swagger; 138 marcados como “unused (best-effort)” (incluye analytics, activity, metadata/stats, preferences/navigation).
- Recomendación: definir con producto/UX qué módulos se implementan en UI vs endpoints de soporte interno.

## Notas para el frontend (lo que debes comunicar)

- Registro público: usar `POST /api/v1/users/public` (no requiere JWT). Roles: `Aprendiz`, `Instructor`, `Administrador`.
- CRUD autenticado: `POST/PUT/PATCH/DELETE` requieren JWT (cookies o `Authorization: Bearer`) y, si usas cookies+CSRF, enviar `X-CSRF-TOKEN`.
- Para renderizar relaciones (nombres en tablas), añadir `?include_relations=true` en listados que muestren objetos anidados.
