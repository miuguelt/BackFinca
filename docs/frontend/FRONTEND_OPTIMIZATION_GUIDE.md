# 🎨 Frontend Optimization Guide - BackFinca

## 📋 Table of Contents

1. [Overview](#overview)
2. [API Query Optimization](#api-query-optimization)
3. [Caching Strategies](#caching-strategies)
4. [Component Performance](#component-performance)
5. [Network Optimization](#network-optimization)
6. [Code Examples](#code-examples)
7. [Best Practices Checklist](#best-practices-checklist)

---

## 🎯 Overview

This guide provides frontend-specific optimization recommendations to work optimally with the recently optimized backend API.

### Key Principles

1. **Request only what you need** - Use field selection
2. **Cache aggressively** - Reduce API calls
3. **Paginate everything** - Never load all records
4. **Batch operations** - Combine multiple requests
5. **Monitor performance** - Track metrics

---

## 🚀 API Query Optimization

### 1. Always Use Pagination

```javascript
// ❌ BAD - Will timeout with 10,000+ animals
const getAllAnimals = async () => {
  const response = await api.get('/animals/');
  return response.data.data; // Could be massive
};

// ✅ GOOD - Paginated approach
const getAnimalsPaginated = async (page = 1, limit = 25) => {
  const response = await api.get('/animals/', {
    params: { page, limit }
  });
  return response.data;
};

// ✅ BETTER - With React Query infinite scroll
const useAnimalsInfinite = () => {
  return useInfiniteQuery(
    'animals',
    ({ pageParam = 1 }) => getAnimalsPaginated(pageParam, 25),
    {
      getNextPageParam: (lastPage) => {
        const { current_page, total_pages } = lastPage.pagination;
        return current_page < total_pages ? current_page + 1 : undefined;
      }
    }
  );
};
```

### 2. Field Selection to Reduce Payload

```javascript
// ❌ BAD - Returns all fields + relationships (50KB per animal)
const response = await api.get('/animals/123');

// ✅ GOOD - Returns only needed fields (5KB per animal)
const response = await api.get('/animals/123', {
  params: {
    fields: 'id,record,status,weight,birth_date'
  }
});

// ✅ BEST - With nested relationships
const response = await api.get('/animals/123', {
  params: {
    fields: 'id,record,status,weight,breed.name,breed.species.name'
  }
});

// React Hook Example
const useAnimal = (id, fields) => {
  return useQuery(
    ['animal', id, fields],
    () => api.get(`/animals/${id}`, {
      params: { fields: fields.join(',') }
    }),
    {
      enabled: !!id,
      staleTime: 5 * 60 * 1000 // 5 minutes
    }
  );
};

// Usage
const { data: animal } = useAnimal(123, [
  'id', 'record', 'status', 'weight', 'breed.name'
]);
```

### 3. Filtering at the API Level

```javascript
// ❌ BAD - Fetch all, filter on client
const response = await api.get('/animals/');
const alive = response.data.data.filter(a => a.status === 'Vivo');

// ✅ GOOD - Filter on server
const response = await api.get('/animals/', {
  params: {
    status: 'Vivo',
    page: 1,
    limit: 25
  }
});

// ✅ BEST - Multiple filters
const response = await api.get('/animals/', {
  params: {
    status: 'Vivo',
    sex: 'Hembra',
    breeds_id: 5,
    birth_date_gte: '2024-01-01',
    page: 1,
    limit: 25
  }
});
```

### 4. Searching Efficiently

```javascript
// ❌ BAD - Client-side search
const allAnimals = await getAllAnimals(); // Huge payload
const filtered = allAnimals.filter(a => a.record.includes(query));

// ✅ GOOD - Server-side search
const searchAnimals = async (query) => {
  const response = await api.get('/animals/', {
    params: {
      search: query, // Searches in 'record' field
      page: 1,
      limit: 10
    }
  });
  return response.data;
};

// React Hook with Debouncing
import { useDebounce } from 'use-debounce';

const useAnimalSearch = (query) => {
  const [debouncedQuery] = useDebounce(query, 500);

  return useQuery(
    ['animals', 'search', debouncedQuery],
    () => searchAnimals(debouncedQuery),
    {
      enabled: debouncedQuery.length >= 3,
      staleTime: 2 * 60 * 1000
    }
  );
};

// Usage
const SearchComponent = () => {
  const [query, setQuery] = useState('');
  const { data, isLoading } = useAnimalSearch(query);

  return (
    <input
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      placeholder="Buscar animal..."
    />
  );
};
```

### 5. Sorting on Server

```javascript
// ❌ BAD - Sort client-side
const animals = await getAnimals();
animals.sort((a, b) => new Date(b.birth_date) - new Date(a.birth_date));

// ✅ GOOD - Sort server-side
const response = await api.get('/animals/', {
  params: {
    sort: '-birth_date', // - prefix for DESC
    page: 1,
    limit: 25
  }
});

// Multiple sort fields
const response = await api.get('/animals/', {
  params: {
    sort: '-birth_date,record', // DESC birth_date, ASC record
    page: 1,
    limit: 25
  }
});
```

---

## 💾 Caching Strategies

### 1. React Query Configuration

```javascript
// src/config/reactQuery.js
import { QueryClient } from 'react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Refetch on window focus (can be disabled)
      refetchOnWindowFocus: false,

      // Retry failed requests 3 times
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),

      // Cache for 5 minutes
      cacheTime: 5 * 60 * 1000,

      // Consider data fresh for 2 minutes
      staleTime: 2 * 60 * 1000,

      // Error boundary
      useErrorBoundary: false
    }
  }
});

// src/index.js
import { QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';
import { queryClient } from './config/reactQuery';

ReactDOM.render(
  <QueryClientProvider client={queryClient}>
    <App />
    <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>,
  document.getElementById('root')
);
```

### 2. Cache Time by Endpoint Type

```javascript
// Master data (rarely changes) - Long cache
const useSpecies = () => {
  return useQuery(
    'species',
    () => api.get('/species/'),
    {
      staleTime: 30 * 60 * 1000, // 30 minutes
      cacheTime: 60 * 60 * 1000  // 1 hour
    }
  );
};

const useBreeds = () => {
  return useQuery(
    'breeds',
    () => api.get('/breeds/'),
    {
      staleTime: 30 * 60 * 1000,
      cacheTime: 60 * 60 * 1000
    }
  );
};

// Transactional data (changes frequently) - Short cache
const useAnimals = (filters) => {
  return useQuery(
    ['animals', filters],
    () => api.get('/animals/', { params: filters }),
    {
      staleTime: 1 * 60 * 1000, // 1 minute
      cacheTime: 3 * 60 * 1000  // 3 minutes
    }
  );
};

// Analytics (expensive to compute) - Match backend cache
const useDashboard = () => {
  return useQuery(
    'dashboard',
    () => api.get('/analytics/dashboard/complete'),
    {
      staleTime: 2 * 60 * 1000, // 2 minutes (match backend)
      cacheTime: 5 * 60 * 1000,
      refetchInterval: 2 * 60 * 1000 // Auto-refresh every 2 min
    }
  );
};
```

### 3. Optimistic Updates

```javascript
// Update animal with optimistic UI
const useUpdateAnimal = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (data) => api.put(`/animals/${data.id}`, data),
    {
      // Optimistic update
      onMutate: async (newAnimal) => {
        // Cancel outgoing refetches
        await queryClient.cancelQueries(['animal', newAnimal.id]);

        // Snapshot previous value
        const previousAnimal = queryClient.getQueryData(['animal', newAnimal.id]);

        // Optimistically update cache
        queryClient.setQueryData(['animal', newAnimal.id], newAnimal);

        // Return context with snapshot
        return { previousAnimal };
      },

      // Rollback on error
      onError: (err, newAnimal, context) => {
        queryClient.setQueryData(
          ['animal', newAnimal.id],
          context.previousAnimal
        );
      },

      // Refetch after success
      onSettled: (data) => {
        queryClient.invalidateQueries(['animal', data.id]);
        queryClient.invalidateQueries(['animals']); // Invalidate list too
      }
    }
  );
};
```

### 4. Cache Invalidation Strategies

```javascript
// Invalidate related queries after mutation
const useCreateAnimal = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (data) => api.post('/animals/', data),
    {
      onSuccess: (newAnimal) => {
        // Invalidate lists
        queryClient.invalidateQueries(['animals']);

        // Invalidate dashboard stats
        queryClient.invalidateQueries(['dashboard']);

        // Invalidate breed animal count if breed changed
        if (newAnimal.breeds_id) {
          queryClient.invalidateQueries(['breed', newAnimal.breeds_id]);
        }

        // Optionally add to cache
        queryClient.setQueryData(['animal', newAnimal.id], newAnimal);
      }
    }
  );
};

const useDeleteAnimal = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (id) => api.delete(`/animals/${id}`),
    {
      onSuccess: (_, deletedId) => {
        // Remove from cache
        queryClient.removeQueries(['animal', deletedId]);

        // Invalidate lists
        queryClient.invalidateQueries(['animals']);
        queryClient.invalidateQueries(['dashboard']);
      }
    }
  );
};
```

### 5. Prefetching for Better UX

```javascript
// Prefetch animal details when hovering over link
const AnimalListItem = ({ animal }) => {
  const queryClient = useQueryClient();

  const prefetchAnimal = () => {
    queryClient.prefetchQuery(
      ['animal', animal.id],
      () => api.get(`/animals/${animal.id}`)
    );
  };

  return (
    <Link
      to={`/animals/${animal.id}`}
      onMouseEnter={prefetchAnimal}
    >
      {animal.record}
    </Link>
  );
};

// Prefetch next page
const AnimalsPaginatedList = ({ currentPage }) => {
  const queryClient = useQueryClient();
  const { data } = useAnimals(currentPage);

  useEffect(() => {
    // Prefetch next page
    if (currentPage < data.pagination.total_pages) {
      queryClient.prefetchQuery(
        ['animals', currentPage + 1],
        () => getAnimalsPaginated(currentPage + 1)
      );
    }
  }, [currentPage, data, queryClient]);

  return <div>{/* Render animals */}</div>;
};
```

---

## ⚡ Component Performance

### 1. Virtualized Lists for Large Datasets

```javascript
import { FixedSizeList } from 'react-window';

const AnimalVirtualList = ({ animals }) => {
  const Row = ({ index, style }) => (
    <div style={style}>
      <AnimalCard animal={animals[index]} />
    </div>
  );

  return (
    <FixedSizeList
      height={600}
      itemCount={animals.length}
      itemSize={100}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
};
```

### 2. Memoization

```javascript
import { memo, useMemo, useCallback } from 'react';

// Memoize expensive components
const AnimalCard = memo(({ animal }) => {
  return (
    <div>
      <h3>{animal.record}</h3>
      <p>Status: {animal.status}</p>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison
  return prevProps.animal.id === nextProps.animal.id &&
         prevProps.animal.updated_at === nextProps.animal.updated_at;
});

// Memoize expensive calculations
const AnimalStatistics = ({ animals }) => {
  const stats = useMemo(() => {
    return {
      total: animals.length,
      alive: animals.filter(a => a.status === 'Vivo').length,
      avgWeight: animals.reduce((sum, a) => sum + a.weight, 0) / animals.length
    };
  }, [animals]);

  return <div>{/* Render stats */}</div>;
};

// Memoize callbacks
const AnimalList = ({ animals }) => {
  const handleDelete = useCallback((id) => {
    // Delete logic
  }, []);

  return animals.map(animal => (
    <AnimalCard
      key={animal.id}
      animal={animal}
      onDelete={handleDelete}
    />
  ));
};
```

### 3. Code Splitting

```javascript
import { lazy, Suspense } from 'react';

// Lazy load heavy components
const AnalyticsDashboard = lazy(() => import('./pages/AnalyticsDashboard'));
const ReportsPage = lazy(() => import('./pages/ReportsPage'));
const AnimalDetailsPage = lazy(() => import('./pages/AnimalDetailsPage'));

// App.js
const App = () => {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/dashboard" element={<AnalyticsDashboard />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/animals/:id" element={<AnimalDetailsPage />} />
      </Routes>
    </Suspense>
  );
};
```

---

## 🌐 Network Optimization

### 1. Request Batching

```javascript
// ❌ BAD - Multiple separate requests
const fetchAllData = async () => {
  const animals = await api.get('/animals/');
  const breeds = await api.get('/breeds/');
  const species = await api.get('/species/');
  return { animals, breeds, species };
};

// ✅ GOOD - Parallel requests
const fetchAllData = async () => {
  const [animals, breeds, species] = await Promise.all([
    api.get('/animals/'),
    api.get('/breeds/'),
    api.get('/species/')
  ]);
  return { animals, breeds, species };
};

// ✅ BEST - React Query parallel queries
const useDashboardData = () => {
  const animals = useQuery('animals', () => api.get('/animals/'));
  const breeds = useQuery('breeds', () => api.get('/breeds/'));
  const species = useQuery('species', () => api.get('/species/'));

  return {
    isLoading: animals.isLoading || breeds.isLoading || species.isLoading,
    data: {
      animals: animals.data,
      breeds: breeds.data,
      species: species.data
    }
  };
};
```

### 2. Request Deduplication

React Query automatically deduplicates identical requests:

```javascript
// These three components all request the same data
const ComponentA = () => {
  const { data } = useQuery('species', fetchSpecies);
  return <div>...</div>;
};

const ComponentB = () => {
  const { data } = useQuery('species', fetchSpecies);
  return <div>...</div>;
};

const ComponentC = () => {
  const { data } = useQuery('species', fetchSpecies);
  return <div>...</div>;
};

// React Query makes only ONE network request
// All three components share the same cached data
```

### 3. Request Cancellation

```javascript
import axios from 'axios';

const useAnimalSearch = (query) => {
  return useQuery(
    ['animals', 'search', query],
    async ({ signal }) => {
      const response = await api.get('/animals/', {
        params: { search: query },
        signal // Pass AbortSignal from React Query
      });
      return response.data;
    },
    {
      enabled: query.length >= 3
    }
  );
};

// If query changes before request completes,
// React Query automatically cancels the previous request
```

### 4. Compression

```javascript
// Configure axios to accept gzip/brotli compression
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
  headers: {
    'Accept-Encoding': 'gzip, deflate, br',
    'Content-Type': 'application/json'
  }
});

// The backend already sends compressed responses
// Just make sure your client accepts them
```

---

## 📝 Code Examples

### Complete Service Layer

```javascript
// src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'https://your-api.com/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'Accept-Encoding': 'gzip, deflate, br'
  }
});

// Request interceptor - Add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - Handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

```javascript
// src/services/animalsService.js
import api from './api';

class AnimalsService {
  async getAll(params = {}) {
    const { page = 1, limit = 25, ...filters } = params;
    const response = await api.get('/animals/', {
      params: { page, limit, ...filters }
    });
    return response.data;
  }

  async getById(id, fields = null) {
    const params = fields ? { fields: fields.join(',') } : {};
    const response = await api.get(`/animals/${id}`, { params });
    return response.data.data;
  }

  async create(data) {
    const response = await api.post('/animals/', data);
    return response.data.data;
  }

  async update(id, data) {
    const response = await api.put(`/animals/${id}`, data);
    return response.data.data;
  }

  async delete(id) {
    const response = await api.delete(`/animals/${id}`);
    return response.data;
  }

  async search(query) {
    const response = await api.get('/animals/', {
      params: { search: query, limit: 10 }
    });
    return response.data;
  }

  async getGenealogy(id, maxDepth = 3) {
    const response = await api.get(`/animals/${id}/genealogy`, {
      params: { max_depth: maxDepth }
    });
    return response.data.data;
  }
}

export default new AnimalsService();
```

### Complete Hooks Layer

```javascript
// src/hooks/useAnimals.js
import { useQuery, useMutation, useQueryClient } from 'react-query';
import animalsService from '../services/animalsService';

export const useAnimals = (filters = {}) => {
  return useQuery(
    ['animals', filters],
    () => animalsService.getAll(filters),
    {
      staleTime: 2 * 60 * 1000,
      keepPreviousData: true // Keep previous page while fetching next
    }
  );
};

export const useAnimal = (id, fields = null) => {
  return useQuery(
    ['animal', id, fields],
    () => animalsService.getById(id, fields),
    {
      enabled: !!id,
      staleTime: 5 * 60 * 1000
    }
  );
};

export const useCreateAnimal = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (data) => animalsService.create(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['animals']);
        queryClient.invalidateQueries(['dashboard']);
      }
    }
  );
};

export const useUpdateAnimal = () => {
  const queryClient = useQueryClient();

  return useMutation(
    ({ id, data }) => animalsService.update(id, data),
    {
      onSuccess: (updatedAnimal) => {
        queryClient.setQueryData(['animal', updatedAnimal.id], updatedAnimal);
        queryClient.invalidateQueries(['animals']);
      }
    }
  );
};

export const useDeleteAnimal = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (id) => animalsService.delete(id),
    {
      onSuccess: (_, deletedId) => {
        queryClient.removeQueries(['animal', deletedId]);
        queryClient.invalidateQueries(['animals']);
        queryClient.invalidateQueries(['dashboard']);
      }
    }
  );
};

export const useAnimalSearch = (query) => {
  const [debouncedQuery] = useDebounce(query, 500);

  return useQuery(
    ['animals', 'search', debouncedQuery],
    () => animalsService.search(debouncedQuery),
    {
      enabled: debouncedQuery.length >= 3,
      staleTime: 2 * 60 * 1000
    }
  );
};
```

### Complete Component Example

```javascript
// src/pages/AnimalsPage.jsx
import React, { useState } from 'react';
import { useAnimals, useDeleteAnimal } from '../hooks/useAnimals';
import { AnimalCard } from '../components/AnimalCard';
import { Pagination } from '../components/Pagination';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

export const AnimalsPage = () => {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    status: 'Vivo',
    sort: '-birth_date'
  });

  const { data, isLoading, error } = useAnimals({ page, limit: 25, ...filters });
  const deleteMutation = useDeleteAnimal();

  const handleDelete = async (id) => {
    if (window.confirm('¿Está seguro de eliminar este animal?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    setPage(1); // Reset to first page
  };

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  const { data: animals, pagination } = data;

  return (
    <div className="animals-page">
      <h1>Animales</h1>

      <FilterBar filters={filters} onChange={handleFilterChange} />

      <div className="animals-grid">
        {animals.map(animal => (
          <AnimalCard
            key={animal.id}
            animal={animal}
            onDelete={() => handleDelete(animal.id)}
          />
        ))}
      </div>

      <Pagination
        currentPage={pagination.current_page}
        totalPages={pagination.total_pages}
        onPageChange={setPage}
      />
    </div>
  );
};
```

---

## ✅ Best Practices Checklist

### API Requests

- [ ] Always use pagination (`?page=1&limit=25`)
- [ ] Use field selection when possible (`?fields=id,record,status`)
- [ ] Filter on server, not client (`?status=Vivo`)
- [ ] Sort on server (`?sort=-birth_date`)
- [ ] Search on server (`?search=query`)
- [ ] Debounce search inputs (500ms)
- [ ] Cancel requests when component unmounts

### Caching

- [ ] Use React Query for API state management
- [ ] Configure appropriate `staleTime` per endpoint type
  - Master data: 30 minutes
  - Transactional data: 1-2 minutes
  - Analytics: 2 minutes (match backend)
- [ ] Invalidate related queries after mutations
- [ ] Use optimistic updates for better UX
- [ ] Prefetch data on hover/route change

### Performance

- [ ] Virtualize long lists (react-window)
- [ ] Memoize expensive components (React.memo)
- [ ] Memoize expensive calculations (useMemo)
- [ ] Memoize callbacks (useCallback)
- [ ] Code split routes (React.lazy)
- [ ] Lazy load images
- [ ] Use CSS instead of JS animations

### Network

- [ ] Batch independent requests (Promise.all)
- [ ] Enable compression (Accept-Encoding header)
- [ ] Set reasonable timeouts (30 seconds)
- [ ] Implement retry logic (3 attempts)
- [ ] Handle errors gracefully
- [ ] Show loading states

### Monitoring

- [ ] Track response times
- [ ] Log slow requests (> 3 seconds)
- [ ] Monitor cache hit rates
- [ ] Track API error rates
- [ ] Monitor bundle size
- [ ] Use React Query Devtools in development

---

## 📊 Performance Targets

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **First Contentful Paint (FCP)** | < 1.5s | Lighthouse |
| **Time to Interactive (TTI)** | < 3s | Lighthouse |
| **API Response Time (p95)** | < 2s | Network tab |
| **Cache Hit Rate** | > 70% | React Query Devtools |
| **Bundle Size** | < 500KB | webpack-bundle-analyzer |
| **Number of Requests** | < 20 per page | Network tab |

---

## 🔗 Additional Resources

- [React Query Docs](https://react-query.tanstack.com/)
- [React Performance Optimization](https://react.dev/learn/render-and-commit)
- [Web Vitals](https://web.dev/vitals/)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)

---

**Happy optimizing! 🚀**
