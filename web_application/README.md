# FinComplaint AI Web Application

A modern web application for AI-powered complaint triage and remediation built with FastAPI and Next.js.

## Architecture

This application consists of two main components:

### Backend (FastAPI)
- **Location**: `web_application/backend/`
- **Technology**: FastAPI with async support
- **Features**:
  - REST API for complaint submission and management
  - WebSocket support for real-time pipeline updates
  - Rate limiting and budget management
  - Integration with fincomplaint-ai library

### Frontend (Next.js)
- **Location**: `web_application/frontend/`
- **Technology**: Next.js 14 with TypeScript and Tailwind CSS
- **Features**:
  - Modern React components with hooks
  - Real-time WebSocket updates
  - Responsive design with Tailwind CSS
  - Complaint submission and review interface

## API Endpoints

### Complaints
- `POST /api/v1/complaints` - Submit a new complaint
- `GET /api/v1/complaints/{thread_id}` - Get complaint status
- `POST /api/v1/complaints/{thread_id}/review` - Submit review action

### Budget Management
- `GET /api/v1/budget` - Get global budget status
- `PUT /api/v1/budget` - Update budget settings
- `GET /api/v1/complaints/{thread_id}/budget` - Get thread-specific budget

### Audit
- `GET /api/v1/complaints/{thread_id}/audit` - Get audit trail

### WebSocket
- `ws://localhost:8000/api/v1/complaints/{thread_id}/ws` - Real-time updates

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 18+
- fincomplaint-ai library (assumed available)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd web_application/backend
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the backend server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd web_application/frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Development

### Backend Development
- API documentation available at `http://localhost:8000/docs`
- Hot reload enabled with `--reload` flag
- Logs available in console

### Frontend Development
- TypeScript for type safety
- Tailwind CSS for styling
- Hot reload enabled in development mode
- Component-based architecture

## Key Components

### Backend Components
- `ComplaintOrchestrator`: Thread-safe wrapper for fincomplaint-ai
- `RateLimiter`: In-memory rate limiting
- `BudgetService`: Token budget management
- WebSocket handler for real-time updates

### Frontend Components
- `ComplaintForm`: Complaint submission form
- `PipelineView`: Real-time pipeline status visualization
- `ReviewPanel`: Human review interface
- `AuditTable`: Audit trail display
- `BudgetWidget`: Budget management interface

## Configuration

### Environment Variables
Create a `.env` file in the backend directory:

```env
# CORS settings
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=10

# Budget settings
DEFAULT_BUDGET_TOKENS=10000
BUDGET_RESET_HOURS=24
```

### Frontend Configuration
Update `web_application/frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Testing

### Backend Tests
```bash
cd web_application/backend
pytest
```

### Frontend Tests
```bash
cd web_application/frontend
npm test
```

## Deployment

### Docker (Recommended)
Build and run with Docker Compose:

```bash
docker-compose up --build
```

### Manual Deployment
1. Build frontend for production:
   ```bash
   cd web_application/frontend
   npm run build
   npm start
   ```

2. Deploy backend with a production ASGI server:
   ```bash
   cd web_application/backend
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

## Architecture Decisions

- **Decoupled Design**: Frontend and backend are completely separate applications
- **Real-time Updates**: WebSocket integration for live pipeline monitoring
- **Type Safety**: Full TypeScript coverage on frontend
- **Async Processing**: FastAPI with async/await for high performance
- **Component Architecture**: Reusable React components with clear separation of concerns

## Security Considerations

- CORS properly configured
- Rate limiting implemented
- Input validation with Pydantic
- Token budget management to prevent abuse
- Audit logging for compliance

## Future Enhancements

- Authentication and authorization
- Database persistence for production
- Advanced analytics dashboard
- Multi-tenant support
- API versioning
- Comprehensive testing suite