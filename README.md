# Student Marketplace API Documentation

## Base URL
```
http://127.0.0.1:8000/api
```

## Authentication
The API uses JWT (JSON Web Tokens) for authentication. Include the access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## 🔐 Authentication Endpoints

### Register User
```http
POST /api/auth/register/
```
**Body:**
```json
{
  "email": "student@wits.ac.za",
  "password": "securepassword",
  "password_confirm": "securepassword",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+27123456789",
  "campus_location": "Wits University"
}
```

### Login
```http
POST /api/auth/login/
```
**Body:**
```json
{
  "email": "student@wits.ac.za",
  "password": "securepassword"
}
```
**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Refresh Token
```http
POST /api/auth/refresh/
```
**Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Get/Update Profile
```http
GET /api/auth/profile/
PUT /api/auth/profile/
```
**PUT Body:**
```json
{
  "first_name": "Updated Name",
  "phone_number": "+27987654321",
  "campus_location": "UCT"
}
```

### Verify Email
```http
POST /api/auth/verify-email/
```
**Body:**
```json
{
  "verification_code": "123456"
}
```

---

## 📦 Product Endpoints

### List/Create Products
```http
GET /api/products/
POST /api/products/
```
**POST Body:**
```json
{
  "title": "MacBook Pro 2020",
  "description": "Excellent condition laptop, perfect for students",
  "price": "25000.00",
  "category": 1,
  "condition": "excellent",
  "location": "Wits Campus",
  "is_available": true
}
```

### Product Detail
```http
GET /api/products/{id}/
PUT /api/products/{id}/
DELETE /api/products/{id}/
```

### Product Categories
```http
GET /api/categories/
POST /api/categories/
```
**POST Body:**
```json
{
  "name": "Electronics",
  "description": "Electronic devices and gadgets"
}
```

### Search Products
```http
GET /api/product-search/?q=laptop&category=1&min_price=1000&max_price=30000
```
**Query Parameters:**
- `q`: Search term
- `category`: Category ID
- `min_price`: Minimum price
- `max_price`: Maximum price
- `condition`: Product condition
- `location`: Location filter

### Favorites
```http
GET /api/favorites/
POST /api/products/{id}/add_favorite/
DELETE /api/products/{id}/remove_favorite/
```

### Product Images
```http
POST /api/product-images/
```
**Body (multipart/form-data):**
```
image: [file]
product: [product_id]
alt_text: "Product main image"
```

---

## 💬 Chat Endpoints

### List/Create Conversations
```http
GET /api/conversations/
POST /api/conversations/
```
**POST Body:**
```json
{
  "title": "Laptop Inquiry",
  "conversation_type": "direct",
  "participant_ids": [2, 3]
}
```

### Conversation Detail
```http
GET /api/conversations/{id}/
PUT /api/conversations/{id}/
DELETE /api/conversations/{id}/
```

### Get Messages
```http
GET /api/conversations/{id}/messages/
```

### Send Message
```http
POST /api/conversations/{id}/send_message/
```
**Body:**
```json
{
  "content": "Is the laptop still available?",
  "message_type": "text"
}
```

### Message Operations
```http
GET /api/messages/
PUT /api/messages/{id}/
DELETE /api/messages/{id}/
POST /api/messages/{id}/mark_read/
```

### Unread Count
```http
GET /api/messages/unread_count/
```

### Conversation Management
```http
POST /api/conversations/{id}/add_participant/
POST /api/conversations/{id}/leave_conversation/
```

### Search Conversations
```http
GET /api/conversation-search/?q=laptop
```

---

## 📁 Response Formats

### Success Response
```json
{
  "id": 1,
  "field1": "value1",
  "field2": "value2",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Error Response
```json
{
  "error": "Error message",
  "details": {
    "field": ["This field is required."]
  }
}
```

### Paginated Response
```json
{
  "count": 25,
  "next": "http://127.0.0.1:8000/api/products/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## 🔒 Permissions

### Public Endpoints
- POST /api/auth/register/
- POST /api/auth/login/
- POST /api/auth/refresh/

### Authenticated Endpoints
All other endpoints require authentication

### Owner-Only Operations
- Update/Delete own products
- Update/Delete own messages
- Update own profile

---

## 📊 Status Codes

- **200 OK**: Successful GET/PUT request
- **201 Created**: Successful POST request
- **204 No Content**: Successful DELETE request
- **400 Bad Request**: Invalid data provided
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Permission denied
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

---

## 🚀 Quick Start

1. **Start the server:**
   ```bash
   cd my_project/backend
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   python manage.py runserver
   ```

2. **Register a user:**
   ```bash
   curl -X POST http://127.0.0.1:8000/api/auth/register/ \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@wits.ac.za",
       "password": "testpass123",
       "password_confirm": "testpass123",
       "first_name": "Test",
       "last_name": "User"
     }'
   ```

3. **Login to get token:**
   ```bash
   curl -X POST http://127.0.0.1:8000/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@wits.ac.za",
       "password": "testpass123"
     }'
   ```

4. **Use the token for authenticated requests:**
   ```bash
   curl -X GET http://127.0.0.1:8000/api/products/ \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

---

## 🧪 Testing

### Automated Testing
Run the provided test script:
```bash
python test_api.py
```

### Manual Testing with Postman
1. Import the API endpoints into Postman
2. Set up environment variables:
   - `base_url`: http://127.0.0.1:8000/api
   - `access_token`: (obtain from login)
3. Test each endpoint systematically

### Frontend Integration
For React/Vue.js frontend integration:
```javascript
// Example API call
const response = await fetch('http://127.0.0.1:8000/api/products/', {
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  }
});
const products = await response.json();
```

---

## 🛠️ Development Notes

### CORS Configuration
The backend is configured to accept requests from:
- `http://localhost:3000` (React default)
- `http://127.0.0.1:3000`
- Add your frontend URLs to `CORS_ALLOWED_ORIGINS` in settings.py

### File Uploads
For file uploads (product images, message attachments):
- Use `multipart/form-data` content type
- Files are stored in `media/` directory
- Maximum file size: 10MB (configurable)

### Pagination
Most list endpoints support pagination:
- Default page size: 20 items
- Use `?page=2` for subsequent pages
- Use `?page_size=50` to override page size

### Rate Limiting
- Authentication endpoints: 5 requests/minute
- Other endpoints: 100 requests/minute
- Adjust in Django settings if needed

---

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the backend directory:
```env
SECRET_KEY=your_secret_key_here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=sqlite:///db.sqlite3
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

### Student Email Domains
Configured domains for student verification:
- `.edu` (US universities)
- `.ac.za` (South African universities)
- `wits.ac.za`
- `uct.ac.za`
- `up.ac.za`
- `tuks.co.za`

Add more domains in `settings.py`:
```python
STUDENT_EMAIL_DOMAINS = [
    '.edu', '.ac.za', 'wits.ac.za', 'uct.ac.za', 
    'up.ac.za', 'tuks.co.za', 'your-university.edu'
]
```

---

## 🚨 Error Handling

### Common Errors

**401 Unauthorized**
```json
{
  "detail": "Authentication credentials were not provided."
}
```
*Solution: Include valid JWT token in Authorization header*

**403 Forbidden**
```json
{
  "detail": "You do not have permission to perform this action."
}
```
*Solution: Ensure user owns the resource or has required permissions*

**400 Bad Request**
```json
{
  "email": ["This field is required."],
  "password": ["This field may not be blank."]
}
```
*Solution: Fix the data according to validation errors*

### Debugging Tips
1. Check Django server logs for detailed error messages
2. Verify JWT token hasn't expired (default: 5 minutes)
3. Ensure Content-Type headers are correct
4. Check that user is verified for restricted actions

---

## 📱 Mobile App Integration

### React Native Example
```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

class StudentMarketplaceAPI {
  constructor() {
    this.baseURL = 'http://127.0.0.1:8000/api';
  }

  async makeRequest(endpoint, options = {}) {
    const token = await AsyncStorage.getItem('access_token');
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, config);
    return response.json();
  }

  async login(email, password) {
    const response = await this.makeRequest('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    
    if (response.access) {
      await AsyncStorage.setItem('access_token', response.access);
      await AsyncStorage.setItem('refresh_token', response.refresh);
    }
    
    return response;
  }

  async getProducts() {
    return this.makeRequest('/products/');
  }
}
```

---

## 🎯 Next Steps

### Phase 1: Core Functionality ✅
- [x] User authentication & registration
- [x] Product CRUD operations
- [x] Basic chat system
- [x] Admin interface

### Phase 2: Enhanced Features
- [ ] Real-time messaging with WebSockets
- [ ] Push notifications
- [ ] Advanced search & filtering
- [ ] User ratings & reviews
- [ ] Payment integration

### Phase 3: Production Ready
- [ ] Deploy to cloud (AWS/Heroku)
- [ ] Add Redis for caching
- [ ] Implement rate limiting
- [ ] Add monitoring & logging
- [ ] SSL certificate setup

### Phase 4: Advanced Features
- [ ] AI-powered product recommendations
- [ ] Geolocation services
- [ ] Social media integration
- [ ] Advanced analytics
- [ ] Multi-language support

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 📞 Support

For questions or issues:
- Check the Django server logs
- Review this documentation
- Test endpoints with the provided test script
- Ensure all dependencies are installed correctly

**Happy coding! 🚀**