"""Utility script to inspect generated swagger.json. Not a pytest test."""

def main():
    from app import create_app
    app = create_app('testing')
    with app.test_client() as c:
        rv = c.get('/api/v1/swagger.json')
        print('STATUS', rv.status_code)
        data = rv.get_data(as_text=True)
        print('LENGTH', len(data))
        print(data[:2000])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
