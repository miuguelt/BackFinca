# Auditoria Frontend vs Backend (Vistas y Endpoints)

Fecha: 2026-01-16 01:21

- Swagger: `http://127.0.0.1:8081/api/v1/swagger.json`
- Frontend: `C:\Users\Miguel\Documents\Flask Projects\Front_finca`

## Resumen

- Endpoints backend (swagger): **278**
- Endpoints consumidos por frontend (detectados): **115**
- Endpoints backend sin consumo detectado: **163**
- Endpoints frontend no encontrados en swagger: **0**
- Vistas con consumo de API: **34**
- Vistas sin consumo de API (estaticas): **6**

## CRUD por recurso (frontend vs backend)

| Recurso | Frontend (metodos detectados) | Backend (swagger) | Estado |
| --- | --- | --- | --- |
| `species` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `breeds` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `animals` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `fields` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `food_types` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `diseases` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `controls` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `animal-fields` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `animal-diseases` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `medications` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `treatments` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `treatment-medications` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `treatment-vaccines` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `vaccines` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `vaccinations` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `genetic-improvements` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `route-administrations` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |
| `users` | DELETE, GET, PATCH, POST, PUT | DELETE, GET, PATCH, POST, PUT | OK |

## Endpoints backend sin vista (resumen por modulo)

| Modulo | Cantidad | Ejemplos |
| --- | --- | --- |
| `animals` | 13 | DELETE /animals/{id}/delete-with-check; GET /animals/metadata; GET /animals/stats; GET /animals/tree/ancestors; GET /animals/tree/descendants; GET /animals/{id}/dependencies |
| `analytics` | 9 | GET /analytics/alerts; GET /analytics/animals/statistics; GET /analytics/animals/{id}/medical-history; GET /analytics/dashboard; GET /analytics/dashboard/complete; GET /analytics/health/statistics |
| `users` | 9 | GET /users/metadata; GET /users/statistics; GET /users/stats; GET /users/{id}/activity; HEAD /users; HEAD /users/{id} |
| `breeds` | 8 | GET /breeds/by-species/{id}; GET /breeds/metadata; GET /breeds/stats; HEAD /breeds; HEAD /breeds/{id}; PARAMETERS /breeds/by-species/{id} |
| `fields` | 8 | GET /fields/metadata; GET /fields/stats; GET /fields/{id}/animals; HEAD /fields; HEAD /fields/{id}; PARAMETERS /fields/{id} |
| `route-administrations` | 8 | GET /route-administrations/active; GET /route-administrations/metadata; GET /route-administrations/search; GET /route-administrations/stats; HEAD /route-administrations; HEAD /route-administrations/{id} |
| `vaccines` | 8 | GET /vaccines/by-route/{id}; GET /vaccines/metadata; GET /vaccines/stats; GET /vaccines/with-route-administration; HEAD /vaccines; HEAD /vaccines/{id} |
| `animal-images` | 7 | DELETE /animal-images/image/{id}; GET /animal-images/{id}; PARAMETERS /animal-images/image/{id}; PARAMETERS /animal-images/image/{id}/set-primary; PARAMETERS /animal-images/{id}; POST /animal-images/upload |
| `preferences` | 7 | DELETE /preferences/favorites; DELETE /preferences/favorites/{id}; GET /preferences/favorites; GET /preferences/history; PARAMETERS /preferences/favorites/{id}; POST /preferences/favorites |
| `activity` | 6 | GET /activity; GET /activity/filters; GET /activity/me; GET /activity/me/stats; GET /activity/me/summary; GET /activity/stats |
| `animal-diseases` | 6 | GET /animal-diseases/metadata; GET /animal-diseases/stats; HEAD /animal-diseases; HEAD /animal-diseases/{id}; PARAMETERS /animal-diseases/{id}; POST /animal-diseases/bulk |
| `controls` | 6 | GET /controls/metadata; GET /controls/stats; HEAD /controls; HEAD /controls/{id}; PARAMETERS /controls/{id}; POST /controls/bulk |
| `diseases` | 6 | GET /diseases/metadata; GET /diseases/stats; HEAD /diseases; HEAD /diseases/{id}; PARAMETERS /diseases/{id}; POST /diseases/bulk |
| `food_types` | 6 | GET /food_types/metadata; GET /food_types/stats; HEAD /food_types; HEAD /food_types/{id}; PARAMETERS /food_types/{id}; POST /food_types/bulk |
| `genetic-improvements` | 6 | GET /genetic-improvements/metadata; GET /genetic-improvements/stats; HEAD /genetic-improvements; HEAD /genetic-improvements/{id}; PARAMETERS /genetic-improvements/{id}; POST /genetic-improvements/bulk |
| `medications` | 6 | GET /medications/metadata; GET /medications/stats; HEAD /medications; HEAD /medications/{id}; PARAMETERS /medications/{id}; POST /medications/bulk |
| `species` | 6 | GET /species/metadata; GET /species/stats; HEAD /species; HEAD /species/{id}; PARAMETERS /species/{id}; POST /species/bulk |
| `treatment-medications` | 6 | GET /treatment-medications/metadata; GET /treatment-medications/stats; HEAD /treatment-medications; HEAD /treatment-medications/{id}; PARAMETERS /treatment-medications/{id}; POST /treatment-medications/bulk |
| `treatment-vaccines` | 6 | GET /treatment-vaccines/metadata; GET /treatment-vaccines/stats; HEAD /treatment-vaccines; HEAD /treatment-vaccines/{id}; PARAMETERS /treatment-vaccines/{id}; POST /treatment-vaccines/bulk |
| `treatments` | 6 | GET /treatments/metadata; GET /treatments/stats; HEAD /treatments; HEAD /treatments/{id}; PARAMETERS /treatments/{id}; POST /treatments/bulk |
| `vaccinations` | 6 | GET /vaccinations/metadata; GET /vaccinations/stats; HEAD /vaccinations; HEAD /vaccinations/{id}; PARAMETERS /vaccinations/{id}; POST /vaccinations/bulk |
| `auth` | 5 | GET /auth/refresh; POST /auth/change-password; POST /auth/login; POST /auth/recover; POST /auth/reset-password |
| `animal-fields` | 4 | GET /animal-fields/metadata; GET /animal-fields/stats; PARAMETERS /animal-fields/{id}; POST /animal-fields/bulk |
| `security` | 3 | GET /security/alerts; GET /security/metrics; POST /security/scan |
| `navigation` | 2 | GET /navigation/quick-access; GET /navigation/structure |

## Vistas sin consumo de API (staticas o solo UI)

- `pages\app\App.tsx`
- `pages\dashboard\all\QRCodeGenerator.tsx`
- `pages\dashboard\all\QRCodeScanner.tsx`
- `pages\landing\index.tsx`
- `pages\notFound\index.tsx`
- `pages\unauthorized\index.tsx`

## Vistas con consumo de API (mapeo rapido)

- Nota: el mapeo es heuristico. Si una vista importa un servicio/hook, se listan todos los endpoints de ese servicio aunque la vista use solo un subconjunto.

- `pages\dashboard\admin\home.tsx`
  - `DELETE /animal-diseases/{id}`
  - `DELETE /animals/{id}`
  - `DELETE /users/{id}`
  - `GET /animal-diseases`
  - `GET /animal-diseases/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `GET /users`
  - `GET /users/roles`
  - `GET /users/status`
  - `GET /users/{id}`
  - `PATCH /animal-diseases/{id}`
  - `PATCH /animals/{id}`
  - `PATCH /users/{id}`
  - `POST /animal-diseases`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /users`
  - `POST /users/public`
  - `PUT /animal-diseases/{id}`
  - `PUT /animals/{id}`
  - `PUT /users/{id}`
- `pages\dashboard\admin\user.tsx`
  - `DELETE /users/{id}`
  - `GET /users`
  - `GET /users/roles`
  - `GET /users/status`
  - `GET /users/{id}`
  - `PATCH /users/{id}`
  - `POST /users`
  - `POST /users/public`
  - `PUT /users/{id}`
- `pages\dashboard\admin\userForm.tsx`
  - `DELETE /users/{id}`
  - `GET /users`
  - `GET /users/roles`
  - `GET /users/status`
  - `GET /users/{id}`
  - `PATCH /users/{id}`
  - `POST /users`
  - `POST /users/public`
  - `PUT /users/{id}`
- `pages\dashboard\all\animalFields.tsx`
  - `DELETE /animal-fields/{id}`
  - `GET /animal-fields`
  - `GET /animal-fields/{id}`
  - `GET /auth/me`
  - `PATCH /animal-fields/{id}`
  - `POST /animal-fields`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `PUT /animal-fields/{id}`
- `pages\dashboard\all\animals.tsx`
  - `DELETE /animals/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `PATCH /animals/{id}`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `PUT /animals/{id}`
- `pages\dashboard\all\controls.tsx`
  - `DELETE /controls/{id}`
  - `GET /auth/me`
  - `GET /controls`
  - `GET /controls/{id}`
  - `PATCH /controls/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /controls`
  - `PUT /controls/{id}`
- `pages\dashboard\all\diseaseAnimal.tsx`
  - `DELETE /animal-diseases/{id}`
  - `GET /animal-diseases`
  - `GET /animal-diseases/{id}`
  - `GET /auth/me`
  - `PATCH /animal-diseases/{id}`
  - `POST /animal-diseases`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `PUT /animal-diseases/{id}`
- `pages\dashboard\all\diseases.tsx`
  - `DELETE /diseases/{id}`
  - `GET /auth/me`
  - `GET /diseases`
  - `GET /diseases/{id}`
  - `PATCH /diseases/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /diseases`
  - `PUT /diseases/{id}`
- `pages\dashboard\all\fields.tsx`
  - `DELETE /fields/{id}`
  - `GET /auth/me`
  - `GET /fields`
  - `GET /fields/{id}`
  - `PATCH /fields/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /fields`
  - `PUT /fields/{id}`
- `pages\dashboard\all\foodTypes.tsx`
  - `DELETE /food_types/{id}`
  - `GET /auth/me`
  - `GET /food_types`
  - `GET /food_types/{id}`
  - `PATCH /food_types/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /food_types`
  - `PUT /food_types/{id}`
- `pages\dashboard\all\forms\animalFieldForm.tsx`
  - `DELETE /animal-fields/{id}`
  - `DELETE /animals/{id}`
  - `DELETE /fields/{id}`
  - `GET /animal-fields`
  - `GET /animal-fields/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `GET /fields`
  - `GET /fields/{id}`
  - `PATCH /animal-fields/{id}`
  - `PATCH /animals/{id}`
  - `PATCH /fields/{id}`
  - `POST /animal-fields`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /fields`
  - `PUT /animal-fields/{id}`
  - `PUT /animals/{id}`
  - `PUT /fields/{id}`
- `pages\dashboard\all\forms\animalForm.tsx`
  - `DELETE /animals/{id}`
  - `DELETE /breeds/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `GET /breeds`
  - `GET /breeds/{id}`
  - `PATCH /animals/{id}`
  - `PATCH /breeds/{id}`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /breeds`
  - `PUT /animals/{id}`
  - `PUT /breeds/{id}`
- `pages\dashboard\all\forms\breedForm.tsx`
  - `DELETE /breeds/{id}`
  - `DELETE /species/{id}`
  - `GET /auth/me`
  - `GET /breeds`
  - `GET /breeds/{id}`
  - `GET /species`
  - `GET /species/{id}`
  - `PATCH /breeds/{id}`
  - `PATCH /species/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /breeds`
  - `POST /species`
  - `PUT /breeds/{id}`
  - `PUT /species/{id}`
- `pages\dashboard\all\forms\controlForm.tsx`
  - `DELETE /animals/{id}`
  - `DELETE /controls/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `GET /controls`
  - `GET /controls/{id}`
  - `PATCH /animals/{id}`
  - `PATCH /controls/{id}`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /controls`
  - `PUT /animals/{id}`
  - `PUT /controls/{id}`
- `pages\dashboard\all\forms\diseaseAnimalForm.tsx`
  - `DELETE /animal-diseases/{id}`
  - `DELETE /animals/{id}`
  - `DELETE /diseases/{id}`
  - `DELETE /users/{id}`
  - `GET /animal-diseases`
  - `GET /animal-diseases/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `GET /diseases`
  - `GET /diseases/{id}`
  - `GET /users`
  - `GET /users/roles`
  - `GET /users/status`
  - `GET /users/{id}`
  - `PATCH /animal-diseases/{id}`
  - `PATCH /animals/{id}`
  - `PATCH /diseases/{id}`
  - `PATCH /users/{id}`
  - `POST /animal-diseases`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /diseases`
  - `POST /users`
  - `POST /users/public`
  - `PUT /animal-diseases/{id}`
  - `PUT /animals/{id}`
  - `PUT /diseases/{id}`
  - `PUT /users/{id}`
- `pages\dashboard\all\forms\diseaseForm.tsx`
  - `DELETE /diseases/{id}`
  - `GET /auth/me`
  - `GET /diseases`
  - `GET /diseases/{id}`
  - `PATCH /diseases/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /diseases`
  - `PUT /diseases/{id}`
- `pages\dashboard\all\forms\fieldForm.tsx`
  - `DELETE /fields/{id}`
  - `DELETE /food_types/{id}`
  - `GET /auth/me`
  - `GET /fields`
  - `GET /fields/{id}`
  - `GET /food_types`
  - `GET /food_types/{id}`
  - `PATCH /fields/{id}`
  - `PATCH /food_types/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /fields`
  - `POST /food_types`
  - `PUT /fields/{id}`
  - `PUT /food_types/{id}`
- `pages\dashboard\all\forms\foodTypeForm.tsx`
  - `DELETE /food_types/{id}`
  - `GET /auth/me`
  - `GET /food_types`
  - `GET /food_types/{id}`
  - `PATCH /food_types/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /food_types`
  - `PUT /food_types/{id}`
- `pages\dashboard\all\forms\improvedAnimalForm.tsx`
  - `DELETE /animals/{id}`
  - `DELETE /genetic-improvements/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `GET /genetic-improvements`
  - `GET /genetic-improvements/{id}`
  - `PATCH /animals/{id}`
  - `PATCH /genetic-improvements/{id}`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /genetic-improvements`
  - `PUT /animals/{id}`
  - `PUT /genetic-improvements/{id}`
- `pages\dashboard\all\forms\medicineForm.tsx`
  - `DELETE /medications/{id}`
  - `DELETE /route-administrations/{id}`
  - `GET /auth/me`
  - `GET /medications`
  - `GET /medications/{id}`
  - `GET /route-administrations`
  - `GET /route-administrations/{id}`
  - `PATCH /medications/{id}`
  - `PATCH /route-administrations/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /medications`
  - `POST /route-administrations`
  - `PUT /medications/{id}`
  - `PUT /route-administrations/{id}`
- `pages\dashboard\all\forms\specieForm.tsx`
  - `DELETE /species/{id}`
  - `GET /auth/me`
  - `GET /species`
  - `GET /species/{id}`
  - `PATCH /species/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /species`
  - `PUT /species/{id}`
- `pages\dashboard\all\forms\treatmentForm.tsx`
  - `DELETE /animals/{id}`
  - `DELETE /treatments/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `GET /treatments`
  - `GET /treatments/{id}`
  - `PATCH /animals/{id}`
  - `PATCH /treatments/{id}`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /treatments`
  - `PUT /animals/{id}`
  - `PUT /treatments/{id}`
- `pages\dashboard\all\forms\vaccinationForm.tsx`
  - `DELETE /animals/{id}`
  - `DELETE /users/{id}`
  - `DELETE /vaccinations/{id}`
  - `DELETE /vaccines/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `GET /users`
  - `GET /users/roles`
  - `GET /users/status`
  - `GET /users/{id}`
  - `GET /vaccinations`
  - `GET /vaccinations/{id}`
  - `GET /vaccines`
  - `GET /vaccines/{id}`
  - `PATCH /animals/{id}`
  - `PATCH /users/{id}`
  - `PATCH /vaccinations/{id}`
  - `PATCH /vaccines/{id}`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /users`
  - `POST /users/public`
  - `POST /vaccinations`
  - `POST /vaccines`
  - `PUT /animals/{id}`
  - `PUT /users/{id}`
  - `PUT /vaccinations/{id}`
  - `PUT /vaccines/{id}`
- `pages\dashboard\all\forms\vaccineForm.tsx`
  - `DELETE /diseases/{id}`
  - `DELETE /route-administrations/{id}`
  - `DELETE /vaccines/{id}`
  - `GET /auth/me`
  - `GET /diseases`
  - `GET /diseases/{id}`
  - `GET /route-administrations`
  - `GET /route-administrations/{id}`
  - `GET /vaccines`
  - `GET /vaccines/{id}`
  - `PATCH /diseases/{id}`
  - `PATCH /route-administrations/{id}`
  - `PATCH /vaccines/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /diseases`
  - `POST /route-administrations`
  - `POST /vaccines`
  - `PUT /diseases/{id}`
  - `PUT /route-administrations/{id}`
  - `PUT /vaccines/{id}`
- `pages\dashboard\all\geneticImprovements.tsx`
  - `DELETE /genetic-improvements/{id}`
  - `GET /auth/me`
  - `GET /genetic-improvements`
  - `GET /genetic-improvements/{id}`
  - `PATCH /genetic-improvements/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /genetic-improvements`
  - `PUT /genetic-improvements/{id}`
- `pages\dashboard\all\medications.tsx`
  - `DELETE /medications/{id}`
  - `GET /auth/me`
  - `GET /medications`
  - `GET /medications/{id}`
  - `PATCH /medications/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /medications`
  - `PUT /medications/{id}`
- `pages\dashboard\all\speciesAndBreeds.tsx`
  - `DELETE /breeds/{id}`
  - `DELETE /species/{id}`
  - `GET /auth/me`
  - `GET /breeds`
  - `GET /breeds/{id}`
  - `GET /species`
  - `GET /species/{id}`
  - `PATCH /breeds/{id}`
  - `PATCH /species/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /breeds`
  - `POST /species`
  - `PUT /breeds/{id}`
  - `PUT /species/{id}`
- `pages\dashboard\all\treatments.tsx`
  - `DELETE /animals/{id}`
  - `DELETE /medications/{id}`
  - `DELETE /treatment-medications/{id}`
  - `DELETE /treatment-vaccines/{id}`
  - `DELETE /treatments/{id}`
  - `DELETE /vaccines/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `GET /medications`
  - `GET /medications/{id}`
  - `GET /treatment-medications`
  - `GET /treatment-medications/{id}`
  - `GET /treatment-vaccines`
  - `GET /treatment-vaccines/{id}`
  - `GET /treatments`
  - `GET /treatments/{id}`
  - `GET /vaccines`
  - `GET /vaccines/{id}`
  - `PATCH /animals/{id}`
  - `PATCH /medications/{id}`
  - `PATCH /treatment-medications/{id}`
  - `PATCH /treatment-vaccines/{id}`
  - `PATCH /treatments/{id}`
  - `PATCH /vaccines/{id}`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /medications`
  - `POST /treatment-medications`
  - `POST /treatment-vaccines`
  - `POST /treatments`
  - `POST /vaccines`
  - `PUT /animals/{id}`
  - `PUT /medications/{id}`
  - `PUT /treatment-medications/{id}`
  - `PUT /treatment-vaccines/{id}`
  - `PUT /treatments/{id}`
  - `PUT /vaccines/{id}`
- `pages\dashboard\all\vaccinations.tsx`
  - `DELETE /vaccinations/{id}`
  - `GET /auth/me`
  - `GET /vaccinations`
  - `GET /vaccinations/{id}`
  - `PATCH /vaccinations/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /vaccinations`
  - `PUT /vaccinations/{id}`
- `pages\dashboard\all\vaccines.tsx`
  - `DELETE /vaccines/{id}`
  - `GET /auth/me`
  - `GET /vaccines`
  - `GET /vaccines/{id}`
  - `PATCH /vaccines/{id}`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `POST /vaccines`
  - `PUT /vaccines/{id}`
- `pages\dashboard\apprentice\home.tsx`
  - `DELETE /animal-diseases/{id}`
  - `DELETE /animals/{id}`
  - `GET /animal-diseases`
  - `GET /animal-diseases/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `PATCH /animal-diseases/{id}`
  - `PATCH /animals/{id}`
  - `POST /animal-diseases`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `PUT /animal-diseases/{id}`
  - `PUT /animals/{id}`
- `pages\dashboard\instructor\home.tsx`
  - `DELETE /animal-diseases/{id}`
  - `DELETE /animals/{id}`
  - `GET /animal-diseases`
  - `GET /animal-diseases/{id}`
  - `GET /animals`
  - `GET /animals/status`
  - `GET /animals/{id}`
  - `GET /auth/me`
  - `PATCH /animal-diseases/{id}`
  - `PATCH /animals/{id}`
  - `POST /animal-diseases`
  - `POST /animals`
  - `POST /auth/logout`
  - `POST /auth/refresh`
  - `PUT /animal-diseases/{id}`
  - `PUT /animals/{id}`
- `pages\login\index.tsx`
  - `GET /auth/me`
  - `POST /auth/logout`
  - `POST /auth/refresh`
- `pages\signUp\index.tsx`
  - `DELETE /users/{id}`
  - `GET /users`
  - `GET /users/roles`
  - `GET /users/status`
  - `GET /users/{id}`
  - `PATCH /users/{id}`
  - `POST /users`
  - `POST /users/public`
  - `PUT /users/{id}`