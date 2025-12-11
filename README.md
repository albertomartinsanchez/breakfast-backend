# FastAPI sample application
Sample python web api using FastAPI

# Project Structure

```
backend/
├── main.py              # FastAPI app initialization and configuration
├── config.py            # Application settings and configuration
├── database.py          # Database connection and session management
├── models.py            # SQLAlchemy ORM models
├── schemas.py           # Pydantic schemas for request/response validation
├── crud.py              # Database operations (Create, Read, Update, Delete)
├── auth.py              # Authentication logic and dependencies
├── routers/
│   ├── __init__.py
│   ├── auth.py          # Authentication endpoints
│   └── products.py      # Product CRUD endpoints
├── requirements.txt     # Python dependencies
├── start.sh             # Startup script for deployment
└── .env                 # Environment variables (not committed to git)
```

## File Responsibilities

- **main.py**: Entry point, router registration, middleware setup
- **config.py**: Centralized configuration using pydantic-settings
- **database.py**: Database engine, session management, connection
- **models.py**: SQLAlchemy models (database schema)
- **schemas.py**: Pydantic models for validation and serialization
- **crud.py**: Pure database operations, reusable across endpoints
- **auth.py**: Authentication logic, token management, user verification
- **routers/**: API endpoints organized by feature

## Best Practices Applied

1. ✅ **Separation of Concerns**: Each file has a single responsibility
2. ✅ **Dependency Injection**: Using FastAPI's Depends for db sessions and auth
3. ✅ **Async/Await**: All database operations are async
4. ✅ **Pydantic Validation**: Input validation with Field constraints
5. ✅ **Router Organization**: Endpoints grouped by feature with prefixes and tags
6. ✅ **Proper Status Codes**: Using correct HTTP status codes (201, 204, 404, etc.)
7. ✅ **Type Hints**: Fully typed code for better IDE support
8. ✅ **Configuration Management**: Settings in config.py, not hardcoded
9. ✅ **Lifespan Events**: Database initialization on startup
10. ✅ **CRUD Pattern**: Reusable database operations

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload

# Run with custom host/port
uvicorn main:app --host 0.0.0.0 --port 8000
```
