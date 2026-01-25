Based on the analysis of the codebase and the symptoms ("backend falls after a certain time", 404 errors, and the presence of SSE/Event functionality), the root cause is **worker starvation** due to Server-Sent Events (SSE).

### The Problem
1.  **SSE Connections:** The application uses SSE (`/api/v1/events`) for real-time updates. SSE connections are persistent and keep a connection open indefinitely.
2.  **Limited Concurrency:** The current configuration uses `gunicorn` with `--workers 2 --threads 2`, allowing only **4 concurrent connections**.
3.  **Starvation:** As soon as 4 users (or tabs) connect to the dashboard, all worker threads are occupied by the SSE loop. Any subsequent request (API calls, navigation) will be queued and eventually timeout or fail, leading to the "server is down" behavior and 404/502 errors from the proxy.

### The Solution
Switch the Gunicorn worker class to **`gevent`**.
`gevent` is an asynchronous worker class that can handle thousands of concurrent connections on a single worker, making it ideal for applications with long-lived connections like SSE or WebSockets.

### Implementation Plan
1.  **Update `requirements.txt`**: Add `gevent` as a dependency.
2.  **Update `Dockerfile`**: Modify the `CMD` to use `gunicorn -k gevent` instead of threads.
3.  **Update `Procfile`**: Update the command for production deployments.

This change will allow the backend to handle many simultaneous users and SSE connections without "falling" or becoming unresponsive.