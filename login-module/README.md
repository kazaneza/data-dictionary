# Login Module

A standalone authentication module with both frontend and backend components that can be easily integrated into any project.

## Features

- JWT-based authentication
- Role-based access control (admin, manager, user)
- Beautiful, animated login UI
- Protected routes
- Token management with localStorage
- CORS-enabled backend API

## Project Structure

```
login-module/
├── backend/
│   ├── auth.py          # Authentication logic and JWT handling
│   ├── config.py        # Configuration (users, JWT settings)
│   ├── main.py          # FastAPI server with login endpoint
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── Login.tsx    # Login page component
│   │   ├── lib/
│   │   │   └── api.ts       # API client with auth interceptors
│   │   ├── App.tsx          # Main app with routing
│   │   ├── main.tsx         # Entry point
│   │   └── index.css        # Styles
│   ├── package.json
│   ├── vite.config.ts
│   └── ... (other config files)
└── README.md
```

## Backend Setup

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Navigate to the backend directory:
```bash
cd login-module/backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure users in `config.py`:
```python
ADMIN_USERS = ["admin1", "admin2"]
MANAGER_USERS = ["manager1", "manager2"]
JWT_SECRET = "your-secret-key-here"  # Change this!
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60
```

5. Run the server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### API Endpoints

- `POST /auth/login` - Login endpoint
  - Request body: `{ "username": "string", "password": "string" }`
  - Response: `{ "token": "jwt-token", "role": "admin|manager|user" }`

- `GET /health` - Health check endpoint

## Frontend Setup

### Prerequisites
- Node.js 16+
- npm or yarn

### Installation

1. Navigate to the frontend directory:
```bash
cd login-module/frontend
```

2. Install dependencies:
```bash
npm install
```

3. Configure API base URL:
   - Create a `.env` file in the frontend directory:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```
   - Or modify `src/lib/api.ts` directly

4. Run the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` (or the port Vite assigns)

### Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Integration Guide

### Backend Integration

1. Copy the `backend/auth.py` and `backend/config.py` files to your project
2. Install the required dependencies: `fastapi`, `uvicorn`, `pydantic`, `PyJWT`
3. Import and use the authentication functions:
```python
from auth import get_current_user, create_access_token, get_user_role

# Protect your endpoints
@app.get("/protected")
def protected_route(user = Depends(get_current_user)):
    return {"message": f"Hello {user['username']}"}
```

4. Add the login endpoint to your FastAPI app:
```python
from auth import LoginRequest, Token, get_user_role, create_access_token

@app.post("/auth/login", response_model=Token)
async def login(request: LoginRequest):
    # Your login logic here
    role = get_user_role(request.username)
    token = create_access_token(request.username, role)
    return {"token": token, "role": role}
```

### Frontend Integration

1. Copy the following files to your React project:
   - `src/pages/Login.tsx`
   - `src/lib/api.ts` (or merge with your existing API file)

2. Install required dependencies:
```bash
npm install axios react-router-dom react-hot-toast lucide-react
```

3. Add the login route to your router:
```tsx
import Login from './pages/Login';

<Route path="/login" element={<Login />} />
```

4. Use the authentication helpers:
```tsx
import { isAdmin, hasManageAccess, getCurrentUser, logout } from './lib/api';

// Check if user is admin
if (isAdmin()) {
  // Show admin features
}

// Check if user can manage
if (hasManageAccess()) {
  // Show management features
}

// Get current user
const user = getCurrentUser();

// Logout
logout();
```

5. Protect your routes:
```tsx
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = !!localStorage.getItem('authToken');
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  return <>{children}</>;
}

// Use it
<Route path="/dashboard" element={
  <PrivateRoute>
    <Dashboard />
  </PrivateRoute>
} />
```

## Customization

### Styling
The login page uses Tailwind CSS. You can customize colors and styles in:
- `src/pages/Login.tsx` - Login component styles
- `tailwind.config.js` - Tailwind configuration

### Logo
Replace the placeholder logo in `Login.tsx` (around line 47) with your own logo:
```tsx
<img
  src="/your-logo.png"
  alt="Your Logo"
  className="..."
/>
```

### Password Validation
Currently, the backend accepts any non-empty password. To add proper password validation:
1. Implement password hashing (bcrypt recommended)
2. Store user credentials in a database
3. Verify passwords in the login endpoint

## Security Notes

⚠️ **Important Security Considerations:**

1. **Change JWT_SECRET**: The default secret in `config.py` is for development only. Use a strong, random secret in production.

2. **Password Storage**: The current implementation doesn't verify passwords properly. Implement proper password hashing and storage for production use.

3. **HTTPS**: Always use HTTPS in production to protect tokens in transit.

4. **Token Expiration**: Adjust `JWT_EXPIRATION_MINUTES` based on your security requirements.

5. **CORS**: Update CORS settings in `backend/main.py` to only allow your frontend domain in production.

## License

This module is provided as-is for use in your projects.

