# Local HTTPS options for FincaBack

This document lists safe options to get HTTPS locally for development so you can test Secure cookies, SameSite and other behaviors that require TLS.

## 1. mkcert (recommended for local development)

- Install mkcert: [https://mkcert.dev/](https://mkcert.dev/) (or follow the project instructions).
- Create a local CA and install it in your OS/browser:

```powershell
mkcert -install
```

- Generate certificates for your development hosts (example: localhost and 127.0.0.1):

```powershell
mkcert localhost 127.0.0.1
```

- Point the app to the generated cert and key before running `run.py`:

```powershell
$env:SSL_CERT_FILE = "C:\path\to\localhost+1.pem"
$env:SSL_KEY_FILE  = "C:\path\to\localhost+1-key.pem"
$env:USE_HTTPS     = "true"
python run.py
```

## 2. Caddy (automatic Let's Encrypt for public dev domains)

Use Caddy to reverse-proxy to your local app and let it obtain certificates automatically via ACME. This is useful when you have a publicly resolvable dev domain.

Example `Caddyfile`:

```text
finca.dev.example.com {
  reverse_proxy 127.0.0.1:8081
}
```

Run Caddy with:

```powershell
caddy run --config Caddyfile
```

## 3. Self-signed certificate (not recommended for full testing)

Generate a self-signed certificate with OpenSSL and set `SSL_CERT_FILE` and `SSL_KEY_FILE` accordingly. Browsers will warn unless you install the CA in the trust store.

## Notes

- In production, TLS termination is handled by Coolify. Keep `USE_HTTPS=false` in `.env.production` and rely on Coolify's certificates.
- For testing cookie behavior (Secure, SameSite) you must use HTTPS in the browser.
- Do not commit private keys or certificates to version control.

## Troubleshooting

- If the browser rejects the certificate, ensure the mkcert CA (or your chosen CA) is installed in the system/browser trust store.
- For cross-device testing, either install the mkcert CA on the device or use a reverse proxy (Caddy) with a publicly resolvable dev domain.

