# Authenticated Chat Example

This example demonstrates how to create a chat interface with user authentication using Ragbits Chat.

## Features

- 🔐 **User Authentication**: Login/logout with username/password
- 👤 **Role-based Access**: Different user roles (admin, moderator, user) with specific capabilities  
- 🛡️ **Secure Sessions**: Session-based authentication with Bearer tokens
- 📊 **Personalized Responses**: User-specific chat responses based on profile and roles
- 🔄 **Live Updates**: Role-specific live updates during processing
- 📚 **User Context**: Reference documents with user profile information

## Files

- `authenticated_chat.py` - Main authenticated chat implementation
- `test_authenticated_chat.py` - Test script for the authentication workflow
- `README_authenticated.md` - This documentation

## Quick Start

### 1. Start the Server

#### Full Authentication Support (Recommended)
```bash
# From the examples/chat directory - includes login/logout endpoints
uv run python authenticated_chat.py
```

#### Alternative Methods
```bash  
# From project root
python examples/chat/authenticated_chat.py

# Via CLI (limited auth support)
uv run ragbits api run examples.chat.authenticated_chat:MyAuthenticatedChat
```

The server will start at `http://127.0.0.1:8000` with a web interface.

**Note**: The CLI version has limited authentication support because it doesn't create the authentication endpoints (`/api/auth/login`, `/api/auth/logout`). For full authentication features, use the direct Python execution.

### 2. Test Users

The example includes these test users:

| Username  | Password  | Roles                    | Description         |
|-----------|-----------|--------------------------|---------------------|
| `admin`   | `admin123` | admin, moderator, user  | System administrator |
| `moderator` | `mod123` | moderator, user        | Community moderator |
| `alice`   | `alice123` | user                   | Regular user        |
| `bob`     | `bob123`   | user                   | Regular user        |

### 3. Authentication Workflow

#### Web Interface
1. Open `http://127.0.0.1:8000` in your browser
2. Use the login form with any test user credentials
3. Start chatting after successful authentication

#### API Endpoints
1. **Login**: `POST /api/auth/login`
   ```json
   {
     "username": "admin",
     "password": "admin123"
   }
   ```

2. **Chat**: `POST /api/chat` (with Bearer token)
   ```bash
   Authorization: Bearer <session_id>
   ```

3. **Logout**: `POST /api/auth/logout`
   ```json
   {
     "session_id": "<session_id>"
   }
   ```

## Testing

### Automated Test
```bash
python examples/chat/test_authenticated_chat.py
```

### Interactive Test
```bash
python examples/chat/test_authenticated_chat.py --interactive
```

Interactive commands:
- `login <username> <password>` - Login
- `chat <message>` - Send message
- `logout` - Logout
- `config` - Show API configuration
- `users` - Show available test users
- `quit` - Exit

## Example Chat Interactions

### As Admin User
```
💬 You: What admin features are available?
🤖 Bot: As an administrator, you have full system access including:
- User management and permissions
- System configuration and monitoring
- Content moderation capabilities
- Administrative dashboards and reports
```

### As Regular User
```
💬 You: Tell me about my profile
🤖 Bot: Hello Alice Johnson! You're logged in as 'alice' with user role. 
Your profile shows you're part of the Marketing department.
```

## Architecture

### AuthenticatedChatInterface
- Extends the base `ChatInterface` with authentication
- Validates sessions before processing chat requests
- Provides user context in `authenticated_chat()` method
- Supports role-based response customization

### ListAuthBackend
- In-memory user storage with hashed passwords
- Session management with expiration
- User roles and metadata support
- Suitable for development and small deployments

### Role-based Features
- **Admin**: Full system access, admin-specific live updates
- **Moderator**: Content moderation features, policy checks
- **User**: Standard chat features, personalized responses

## Customization

### Adding New Users
Edit the `create_auth_backend()` function in `authenticated_chat.py`:

```python
users = [
    {
        "username": "newuser",
        "password": "newpass123",
        "email": "newuser@example.com",
        "full_name": "New User",
        "roles": ["user"],
        "metadata": {"department": "Engineering"}
    }
]
```

### Custom Authentication Backend
Replace `ListAuthBackend` with `DatabaseAuthBackend` or `OAuth2Backend`:

```python
from ragbits.chat.auth.backends import DatabaseAuthBackend, OAuth2Backend

# Database authentication
auth_backend = DatabaseAuthBackend("sqlite:///users.db")

# OAuth2 authentication  
auth_backend = OAuth2Backend("google", client_id, client_secret, redirect_uri)
```

### Role-specific Responses
Modify the `authenticated_chat()` method to customize responses based on user roles:

```python
if "admin" in user_roles:
    yield self.create_text_response("🔧 Admin-specific content...")
elif "moderator" in user_roles:
    yield self.create_text_response("🛡️ Moderator-specific content...")
```

## Security Notes

- Passwords are hashed using SHA-256 in `ListAuthBackend`
- Sessions have configurable expiration times
- Bearer tokens are used for API authentication
- CORS is configured for web interface access
- State signatures prevent tampering with conversation state

## Production Considerations

- Use `DatabaseAuthBackend` or `OAuth2Backend` for production
- Configure proper CORS origins for your domain
- Set up HTTPS for secure authentication
- Implement proper session timeout and cleanup
- Add rate limiting and abuse protection
- Use environment variables for sensitive configuration