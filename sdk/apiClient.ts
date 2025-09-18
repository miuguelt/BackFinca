/*
  Minimal Frontend SDK for FincaBack
  - Axios instance with cookies (withCredentials)
  - CSRF header handling (X-CSRF-Token) for mutating requests
  - Automatic refresh on 401 with retry
  - Auth helpers: login, me, refresh, logout

  Usage:
    import { createApiClient } from './sdk/apiClient';
    const api = createApiClient({ baseURL: 'https://finca.isladigital.xyz/api/v1' });

    // Login
    await api.login({ identifier: 'user@example.com', password: 'password' });

    // Then authenticated requests automatically include cookies
    const me = await api.me();
*/

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

export type ApiSuccess<T, M = any> = { success: true; data: T; meta?: M };
export type ApiError = { success: false; error: { code: string; message: string; details?: any; trace_id: string } };
export type ApiResponse<T, M = any> = ApiSuccess<T, M> | ApiError;
export type LoginRequest = {
  identifier?: string | number;
  identification?: string | number;
  email?: string;
  password: string;
};

export type UserInfo = {
  id: number;
  identification?: string | null;
  fullname: string;
  email: string;
  role: string;
  status: boolean;
};

export type LoginData = {
  user: UserInfo;
  access_token?: string;
  token_type?: string;
  expires_in?: number;
};

export type RefreshData = {
  access_token: string;
  token_type: string;
  expires_in?: number;
};
export type ApiClient = ReturnType<typeof createApiClient>;

// Analytics types based on swagger definitions
export type Dashboard = {
  total_animals: number;
  active_animals: number;
  health_alerts: number;
  productivity_score: number;
  recent_activities: any[];
  generated_at: string; // date-time
};

export type ProductionStats = {
  weight_trends: any[];
  growth_rates: any[];
  productivity_metrics: any;
  best_performers: any[];
  group_statistics: any;
  summary: any;
};

export type AnimalStats = {
  by_status: any;
  by_sex: any;
  by_breed: any[];
  by_age_group: any;
  weight_distribution: any;
  total_animals: number;
  average_weight: number;
};

export type HealthStats = {
  treatments_by_month: any[];
  vaccinations_by_month: any[];
  health_status_distribution: any;
  common_diseases: any[];
  medication_usage: any[];
};

// --- Domain model types (from swagger) ---
export type RouteAdminRef = { id: number; name: string };

export type RouteAdministrationInput = {
  name: string;
  description?: string;
  status?: boolean; // default true
};
export type RouteAdministration = {
  id: number;
  name: string;
  description?: string;
  status: boolean;
  created_at: string; // date-time
  updated_at: string; // date-time
};

export type MedicationsInput = {
  name: string;
  description: string;
  indications?: string;
  dosis?: string;
  contraindications?: string;
  route_administration_id: number;
  availability?: boolean;
};
export type Medication = {
  id: number;
  name: string;
  description: string;
  indications: string;
  contraindications?: string;
  route_administration_id: number;
  availability: boolean; // default true
  created_at: string; // date-time
  updated_at: string; // date-time
  route_administration_rel?: RouteAdminRef;
};

export type VaccinesInput = {
  name: string;
  dosis: string;
  route_administration_id: number;
  vaccination_interval: string;
  type: string; // Atenuada, Inactivada, ...
  national_plan: string;
  target_disease_id: number;
};
export type Vaccine = {
  id: number;
  name: string;
  dosis: string;
  route_administration_id: number;
  vaccination_interval: string;
  type: string;
  national_plan: string;
  target_disease_id: number;
  route_administration_rel?: RouteAdminRef;
};

export type AnimalDiseasesInput = {
  animal_id: number;
  disease_id: number;
  instructor_id: number;
  diagnosis_date: string; // YYYY-MM-DD
  status?: string;
  notes?: string | null;
};
export type AnimalDisease = {
  id: number;
  animal_id: number;
  disease_id: number;
  instructor_id: number;
  diagnosis_date: string; // YYYY-MM-DD
  status: string;
  notes?: string | null;
  created_at: string; // date-time
  updated_at: string; // date-time
  animal?: { id: number; record: string; sex: string; status: string };
  disease?: { id: number; name: string };
  instructor?: { id: number; fullname: string; role: string };
};

export type AnimalFieldsInput = {
  animal_id: number;
  field_id: number;
  assignment_date: string; // YYYY-MM-DD
  removal_date?: string | null; // YYYY-MM-DD
  notes?: string | null;
};
export type AnimalField = {
  id: number;
  animal_id: number;
  field_id: number;
  assignment_date: string; // YYYY-MM-DD
  removal_date?: string | null; // YYYY-MM-DD
  notes?: string | null;
  created_at: string; // date-time
  updated_at: string; // date-time
  animal?: { id: number; record: string; sex: string; status: string };
  field?: { id: number; name: string; ubication?: string; capacity?: number };
};

// Add domain types for Diseases and Fields
export type FieldState = 'Disponible' | 'Ocupado' | 'Mantenimiento' | 'Restringido' | 'Dañado' | 'Activo';

export type FieldsInput = {
  name: string;
  ubication: string;
  capacity: string;
  state: FieldState; // enum per swagger
  handlings: string;
  gauges: string;
  area: string;
  food_type_id?: number;
};

export type Field = {
  id: number;
  name: string;
  ubication?: string | null;
  capacity?: string | null;
  state: FieldState;
  handlings?: string | null;
  gauges?: string | null;
  area: string;
  food_type_id?: number | null;
  created_at: string; // date-time
  updated_at: string; // date-time
};

export type DiseasesInput = {
  name: string;
  symptoms: string;
  details: string;
};

export type Disease = {
  id: number;
  name: string;
  symptoms: string;
  details: string;
  created_at: string; // date-time
  updated_at: string; // date-time
};

// --- Error & pagination types ---
export class ApiClientError extends Error {
  code?: string;
  traceId?: string;
  details?: any;
  constructor(message: string, code?: string, traceId?: string, details?: any) {
    super(message);
    this.name = 'ApiClientError';
    this.code = code;
    this.traceId = traceId;
    this.details = details;
  }
}

export type Pagination = {
  page: number;
  limit: number;
  total_items: number;
  total_pages: number;
  has_next_page: boolean;
  has_previous_page: boolean;
};
export type PaginationMeta = { pagination: Pagination };
export type PaginatedResult<T, M extends PaginationMeta = PaginationMeta> = { items: T[]; meta?: M };

// Provide a reusable CRUD resource type for stronger typings
export type CrudResource<TModel, TCreate = Partial<TModel>, TUpdate = Partial<TModel>> = {
  list: (params?: any, config?: AxiosRequestConfig) => Promise<TModel[]>;
  listWithMeta: <M extends PaginationMeta = PaginationMeta>(params?: any, config?: AxiosRequestConfig) => Promise<PaginatedResult<TModel, M>>;
  get: (id: string | number, config?: AxiosRequestConfig) => Promise<TModel>;
  create: (payload: TCreate, config?: AxiosRequestConfig) => Promise<TModel>;
  update: (id: string | number, payload: TUpdate, config?: AxiosRequestConfig) => Promise<TModel>;
  patch: (id: string | number, payload: Partial<TUpdate>, config?: AxiosRequestConfig) => Promise<TModel>;
  remove: (id: string | number, config?: AxiosRequestConfig) => Promise<any>;
};

// --- Cookie helpers ---
function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()!.split(';').shift() || null;
  return null;
}

export function getCsrfAccess(): string | null {
  return getCookie('csrf_access_token');
}

export function getCsrfRefresh(): string | null {
  return getCookie('csrf_refresh_token');
}

function isMutating(method?: string): boolean {
  const m = (method || 'GET').toUpperCase();
  return m === 'POST' || m === 'PUT' || m === 'PATCH' || m === 'DELETE';
}

function isRefreshUrl(url?: string): boolean {
  if (!url) return false;
  // Works for both absolute and relative URLs
  return url.endsWith('/auth/refresh') || url.includes('/auth/refresh?') || url.includes('/auth/refresh#');
}

function extractData<T>(payload: any): T {
  if (payload && typeof payload.success === 'boolean') {
    if (payload.success) return payload.data as T;
    const err = payload.error || {};
    throw new ApiClientError(err.message || 'API error', err.code, err.trace_id, err.details);
  }
  return payload as T;
}

export function createApiClient(options?: { baseURL?: string }): {
  http: AxiosInstance;
  login: (payload: LoginRequest, config?: AxiosRequestConfig) => Promise<LoginData>;
  me: (config?: AxiosRequestConfig) => Promise<UserInfo>;
  refresh: (config?: AxiosRequestConfig) => Promise<RefreshData>;
  logout: (config?: AxiosRequestConfig) => Promise<null>;
  createCrud: <TModel, TCreate = Partial<TModel>, TUpdate = Partial<TModel>>(basePath: string) => CrudResource<TModel, TCreate, TUpdate>;
  animals: {
    list: (params?: any, config?: AxiosRequestConfig) => Promise<any[]>;
    listWithMeta: <M extends PaginationMeta = PaginationMeta>(params?: any, config?: AxiosRequestConfig) => Promise<PaginatedResult<any, M>>;
    get: (id: string | number, config?: AxiosRequestConfig) => Promise<any>;
    create: (payload: any, config?: AxiosRequestConfig) => Promise<any>;
    update: (id: string | number, payload: any, config?: AxiosRequestConfig) => Promise<any>;
    patch: (id: string | number, payload: any, config?: AxiosRequestConfig) => Promise<any>;
    remove: (id: string | number, config?: AxiosRequestConfig) => Promise<any>;
    stats: (config?: AxiosRequestConfig) => Promise<any>;
    status: (config?: AxiosRequestConfig) => Promise<any>;
  };
  medications: CrudResource<Medication, MedicationsInput, MedicationsInput>;
  vaccines: CrudResource<Vaccine, VaccinesInput, VaccinesInput>;
  routeAdministrations: CrudResource<RouteAdministration, RouteAdministrationInput, RouteAdministrationInput>;
  animalDiseases: CrudResource<AnimalDisease, AnimalDiseasesInput, AnimalDiseasesInput> & { stats: (config?: AxiosRequestConfig) => Promise<any> };
  animalFields: CrudResource<AnimalField, AnimalFieldsInput, AnimalFieldsInput> & { stats: (config?: AxiosRequestConfig) => Promise<any> };
  diseases: CrudResource<Disease, DiseasesInput, DiseasesInput> & { stats: (config?: AxiosRequestConfig) => Promise<any>; bulkCreate: (payload: DiseasesInput[], config?: AxiosRequestConfig) => Promise<Disease[]> };
  fields: CrudResource<Field, FieldsInput, FieldsInput> & { stats: (config?: AxiosRequestConfig) => Promise<any>; bulkCreate: (payload: FieldsInput[], config?: AxiosRequestConfig) => Promise<Field[]> };
  analytics: {
    alerts: (params?: AlertsParams, config?: AxiosRequestConfig) => Promise<any[]>;
    animals: {
      statistics: (config?: AxiosRequestConfig) => Promise<AnimalStats>;
      medicalHistory: (animalId: string | number, params?: AnimalMedicalHistoryParams, config?: AxiosRequestConfig) => Promise<any>;
    };
    dashboard: (config?: AxiosRequestConfig) => Promise<Dashboard>;
    health: { statistics: (params?: HealthStatsParams, config?: AxiosRequestConfig) => Promise<HealthStats> };
    production: { statistics: (params?: ProductionStatsParams, config?: AxiosRequestConfig) => Promise<ProductionStats> };
    reports: { custom: (params: CustomReportParams, config?: AxiosRequestConfig) => Promise<any> };
  };
} {
  const baseURL = options?.baseURL || '/api/v1';

  const http = axios.create({
    baseURL,
    withCredentials: true,
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    }
  });

  // REQUEST: attach CSRF for mutating requests
  http.interceptors.request.use((config) => {
    // Ensure credentials are always included
    config.withCredentials = true;

    // Add CSRF header for mutating requests
    if (isMutating(config.method)) {
      const isRefresh = isRefreshUrl(config.url || '');
      const csrfName = isRefresh ? 'csrf_refresh_token' : 'csrf_access_token';
      const csrfToken = getCookie(csrfName);
      if (csrfToken) {
        config.headers = config.headers || {};
        (config.headers as any)['X-CSRF-Token'] = csrfToken;
      }
    }

    return config;
  });

  // RESPONSE: reject domain errors (success=false) before normal flow
  http.interceptors.response.use(
    (response) => {
      const data = (response as AxiosResponse<any>).data;
      if (data && typeof data.success === 'boolean' && data.success === false) {
        const err = data.error || {};
        return Promise.reject(new ApiClientError(err.message || 'API error', err.code, err.trace_id, err.details));
      }
      return response;
    },
    async (error: AxiosError) => {
      const original = error.config as (AxiosRequestConfig & { _retry?: boolean });

      // If unauthorized and we haven't retried yet, try refresh
      if (
        error.response?.status === 401 &&
        original &&
        !original._retry &&
        !isRefreshUrl(original.url || '') &&
        !(original.url || '').endsWith('/auth/login')
      ) {
        original._retry = true;
        try {
          const csrfRefresh = getCookie('csrf_refresh_token') || '';
          await http.post('/auth/refresh', {}, {
            withCredentials: true,
            headers: { 'X-CSRF-Token': csrfRefresh }
          });
          // Retry original request
          return http(original);
        } catch (refreshErr) {
          // If refresh also fails, propagate the original error
          return Promise.reject(refreshErr);
        }
      }

      return Promise.reject(error);
    }
  );

  async function login(payload: LoginRequest, config?: AxiosRequestConfig): Promise<LoginData> {
    const res: AxiosResponse<ApiResponse<LoginData>> = await http.post('/auth/login', payload, config);
    return extractData<LoginData>(res.data);
  }

  async function me(config?: AxiosRequestConfig): Promise<UserInfo> {
    const res: AxiosResponse<ApiResponse<UserInfo>> = await http.get('/auth/me', config);
    return extractData<UserInfo>(res.data);
  }

  async function refresh(config?: AxiosRequestConfig): Promise<RefreshData> {
    const csrfRefresh = getCookie('csrf_refresh_token') || '';
    const res: AxiosResponse<ApiResponse<RefreshData>> = await http.post('/auth/refresh', {}, {
      ...(config || {}),
      headers: { ...(config?.headers || {}), 'X-CSRF-Token': csrfRefresh },
      withCredentials: true
    });
    return extractData<RefreshData>(res.data);
  }

  async function logout(config?: AxiosRequestConfig): Promise<null> {
    const res: AxiosResponse<ApiResponse<null>> = await http.post('/auth/logout', {}, config);
    return extractData<null>(res.data);
  }

  function normalizeBase(path: string): string {
    if (!path.startsWith('/')) return `/${path}`;
    return path;
  }

  function createCrud<TModel, TCreate = Partial<TModel>, TUpdate = Partial<TModel>>(basePath: string) {
    const base = normalizeBase(basePath).replace(/\/$/, '');
    return {
      async list(params?: any, config?: AxiosRequestConfig): Promise<TModel[]> {
        const res: AxiosResponse<ApiResponse<TModel[], PaginationMeta>> = await http.get(`${base}/`, { ...(config || {}), params });
        return extractData<TModel[]>(res.data);
      },
      async listWithMeta<M extends PaginationMeta = PaginationMeta>(params?: any, config?: AxiosRequestConfig): Promise<PaginatedResult<TModel, M>> {
        const res: AxiosResponse<ApiResponse<TModel[], M>> = await http.get(`${base}/`, { ...(config || {}), params });
        const data = res.data as ApiResponse<TModel[], M>;
        if ('success' in data) {
          if (data.success) {
            return { items: data.data, meta: data.meta } as PaginatedResult<TModel, M>;
          }
          const err = data.error || {} as any;
          throw new ApiClientError(err.message || 'API error', err.code, err.trace_id, err.details);
        }
        // Non-standard response
        return { items: (data as unknown as any[]), meta: undefined } as PaginatedResult<TModel, M>;
      },
      async get(id: string | number, config?: AxiosRequestConfig): Promise<TModel> {
        const res: AxiosResponse<ApiResponse<TModel>> = await http.get(`${base}/${id}`, config);
        return extractData<TModel>(res.data);
      },
      async create(payload: TCreate, config?: AxiosRequestConfig): Promise<TModel> {
        const res: AxiosResponse<ApiResponse<TModel>> = await http.post(`${base}/`, payload, config);
        return extractData<TModel>(res.data);
      },
      async update(id: string | number, payload: TUpdate, config?: AxiosRequestConfig): Promise<TModel> {
        const res: AxiosResponse<ApiResponse<TModel>> = await http.put(`${base}/${id}`, payload, config);
        return extractData<TModel>(res.data);
      },
      async patch(id: string | number, payload: Partial<TUpdate>, config?: AxiosRequestConfig): Promise<TModel> {
        const res: AxiosResponse<ApiResponse<TModel>> = await http.patch(`${base}/${id}`, payload, config);
        return extractData<TModel>(res.data);
      },
      async remove(id: string | number, config?: AxiosRequestConfig): Promise<any> {
        const res: AxiosResponse<ApiResponse<any>> = await http.delete(`${base}/${id}`, config);
        return extractData<any>(res.data);
      }
    } as CrudResource<TModel, TCreate, TUpdate>;
  }

  // Preconfig for animals resource with a couple of specials
  const animalsCrud = createCrud<any>('/animals');
  const animals = {
    ...animalsCrud,
    async listWithMeta<M extends PaginationMeta = PaginationMeta>(params?: any, config?: AxiosRequestConfig): Promise<PaginatedResult<any, M>> {
      const res: AxiosResponse<ApiResponse<any[], M>> = await http.get('/animals/', { ...(config || {}), params });
      const data = res.data as ApiResponse<any[], M>;
      if ('success' in data) {
        if (data.success) {
          return { items: data.data, meta: data.meta } as PaginatedResult<any, M>;
        }
        const err = (data as ApiError).error || {} as any;
        throw new ApiClientError(err.message || 'API error', err.code, err.trace_id, err.details);
      }
      return { items: (data as unknown as any[]), meta: undefined } as PaginatedResult<any, M>;
    },
    async stats(config?: AxiosRequestConfig): Promise<any> {
      const res: AxiosResponse<ApiResponse<any>> = await http.get('/animals/stats', config);
      return extractData<any>(res.data);
    },
    async status(config?: AxiosRequestConfig): Promise<any> {
      const res: AxiosResponse<ApiResponse<any>> = await http.get('/animals/status', config);
      return extractData<any>(res.data);
    }
  };

  const analytics = {
    async alerts(params?: AlertsParams, config?: AxiosRequestConfig): Promise<any[]> {
      const res: AxiosResponse<ApiResponse<any[]>> = await http.get('/analytics/alerts', { ...(config || {}), params });
      return extractData<any[]>(res.data);
    },
    animals: {
      async statistics(config?: AxiosRequestConfig): Promise<AnimalStats> {
        const res: AxiosResponse<ApiResponse<AnimalStats>> = await http.get('/analytics/animals/statistics', config);
        return extractData<AnimalStats>(res.data);
      },
      async medicalHistory(animalId: string | number, params?: AnimalMedicalHistoryParams, config?: AxiosRequestConfig): Promise<any> {
        const res: AxiosResponse<ApiResponse<any>> = await http.get(`/analytics/animals/${animalId}/medical-history`, { ...(config || {}), params });
        return extractData<any>(res.data);
      }
    },
    async dashboard(config?: AxiosRequestConfig): Promise<Dashboard> {
      const res: AxiosResponse<ApiResponse<Dashboard>> = await http.get('/analytics/dashboard', config);
      return extractData<Dashboard>(res.data);
    },
    health: {
      async statistics(params?: HealthStatsParams, config?: AxiosRequestConfig): Promise<HealthStats> {
        const res: AxiosResponse<ApiResponse<HealthStats>> = await http.get('/analytics/health/statistics', { ...(config || {}), params });
        return extractData<HealthStats>(res.data);
      }
    },
    production: {
      async statistics(params?: ProductionStatsParams, config?: AxiosRequestConfig): Promise<ProductionStats> {
        const res: AxiosResponse<ApiResponse<ProductionStats>> = await http.get('/analytics/production/statistics', { ...(config || {}), params });
        return extractData<ProductionStats>(res.data);
      }
    },
    reports: {
      async custom(params: CustomReportParams, config?: AxiosRequestConfig): Promise<any> {
        const res: AxiosResponse<ApiResponse<any>> = await http.post('/analytics/reports/custom', null, { ...(config || {}), params });
        return extractData<any>(res.data);
      }
    }
  };

  const medications = createCrud<Medication, MedicationsInput, MedicationsInput>('/medications');
  const vaccines = createCrud<Vaccine, VaccinesInput, VaccinesInput>('/vaccines');
  const routeAdministrations = createCrud<RouteAdministration, RouteAdministrationInput, RouteAdministrationInput>('/route-administrations');

  // Preconfigured and typed resources with extra endpoints
  const animalDiseasesCrud = createCrud<AnimalDisease, AnimalDiseasesInput, AnimalDiseasesInput>('/animal-diseases');
  const animalDiseases = {
    ...animalDiseasesCrud,
    async stats(config?: AxiosRequestConfig): Promise<any> {
      const res: AxiosResponse<ApiResponse<any>> = await http.get('/animal-diseases/stats', config);
      return extractData<any>(res.data);
    }
  };

  const animalFieldsCrud = createCrud<AnimalField, AnimalFieldsInput, AnimalFieldsInput>('/animal-fields');
  const animalFields = {
    ...animalFieldsCrud,
    async stats(config?: AxiosRequestConfig): Promise<any> {
      const res: AxiosResponse<ApiResponse<any>> = await http.get('/animal-fields/stats', config);
      return extractData<any>(res.data);
    }
  };

  // Diseases resource with stats and bulkCreate helpers
  const diseasesCrud = createCrud<Disease, DiseasesInput, DiseasesInput>('/diseases');
  const diseases = {
    ...diseasesCrud,
    async stats(config?: AxiosRequestConfig): Promise<any> {
      const res: AxiosResponse<ApiResponse<any>> = await http.get('/diseases/stats', config);
      return extractData<any>(res.data);
    },
    async bulkCreate(payload: DiseasesInput[], config?: AxiosRequestConfig): Promise<Disease[]> {
      const res: AxiosResponse<ApiResponse<Disease[]>> = await http.post('/diseases/bulk', payload, config);
      return extractData<Disease[]>(res.data);
    }
  };

  // Fields resource with stats and bulkCreate helpers
  const fieldsCrud = createCrud<Field, FieldsInput, FieldsInput>('/fields');
  const fields = {
    ...fieldsCrud,
    async stats(config?: AxiosRequestConfig): Promise<any> {
      const res: AxiosResponse<ApiResponse<any>> = await http.get('/fields/stats', config);
      return extractData<any>(res.data);
    },
    async bulkCreate(payload: FieldsInput[], config?: AxiosRequestConfig): Promise<Field[]> {
      const res: AxiosResponse<ApiResponse<Field[]>> = await http.post('/fields/bulk', payload, config);
      return extractData<Field[]>(res.data);
    }
  };

  return { http, login, me, refresh, logout, createCrud, animals, medications, vaccines, routeAdministrations, animalDiseases, animalFields, diseases, fields, analytics };
}