#!/usr/bin/env python3
"""
Comprehensive API testing script for Student Marketplace
Run this after starting the Django server to test all endpoints
"""

import requests
import json
from datetime import datetime

BASE_URL = 'http://127.0.0.1:8000/api'

class APITester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.user_id = None
        
    def print_response(self, response, description=""):
        """Helper to print API responses"""
        print(f"\n{'='*50}")
        print(f"TEST: {description}")
        print(f"URL: {response.url}")
        print(f"Status: {response.status_code}")
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response: {response.text}")
        print('='*50)
        
    def test_user_registration(self):
        """Test user registration"""
        data = {
            "email": "test@wits.ac.za",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "first_name": "Test",
            "last_name": "User",
            "phone_number": "+27123456789",
            "campus_location": "Wits University"
        }
        
        response = self.session.post(f"{BASE_URL}/auth/register/", json=data)
        self.print_response(response, "User Registration")
        
        if response.status_code == 201:
            self.user_id = response.json().get('user', {}).get('id')
            return True
        return False
    
    def test_user_login(self):
        """Test user login"""
        data = {
            "email": "test@wits.ac.za",
            "password": "testpass123"
        }
        
        response = self.session.post(f"{BASE_URL}/auth/login/", json=data)
        self.print_response(response, "User Login")
        
        if response.status_code == 200:
            self.access_token = response.json().get('access')
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}'
            })
            return True
        return False
    
    def test_user_profile(self):
        """Test getting user profile"""
        response = self.session.get(f"{BASE_URL}/auth/profile/")
        self.print_response(response, "User Profile")
        return response.status_code == 200
    
    def test_categories(self):
        """Test product categories"""
        # Create category
        data = {
            "name": "Electronics",
            "description": "Electronic devices and gadgets"
        }
        
        response = self.session.post(f"{BASE_URL}/categories/", json=data)
        self.print_response(response, "Create Category")
        
        if response.status_code == 201:
            category_id = response.json().get('id')
            
            # List categories
            response = self.session.get(f"{BASE_URL}/categories/")
            self.print_response(response, "List Categories")
            
            return category_id
        return None
    
    def test_products(self, category_id):
        """Test product operations"""
        # Create product
        data = {
            "title": "Test Laptop",
            "description": "A great laptop for students",
            "price": "15000.00",
            "category": category_id,
            "condition": "excellent",
            "location": "Wits Campus",
            "is_available": True
        }
        
        response = self.session.post(f"{BASE_URL}/products/", json=data)
        self.print_response(response, "Create Product")
        
        if response.status_code == 201:
            product_id = response.json().get('id')
            
            # List products
            response = self.session.get(f"{BASE_URL}/products/")
            self.print_response(response, "List Products")
            
            # Get specific product
            response = self.session.get(f"{BASE_URL}/products/{product_id}/")
            self.print_response(response, "Get Product Detail")
            
            # Search products
            response = self.session.get(f"{BASE_URL}/product-search/?q=laptop")
            self.print_response(response, "Search Products")
            
            # Add to favorites
            response = self.session.post(f"{BASE_URL}/products/{product_id}/add_favorite/")
            self.print_response(response, "Add to Favorites")
            
            return product_id
        return None
    
    def test_conversations(self):
        """Test chat functionality"""
        # Create conversation
        data = {
            "title": "Laptop Inquiry",
            "conversation_type": "direct"
        }
        
        response = self.session.post(f"{BASE_URL}/conversations/", json=data)
        self.print_response(response, "Create Conversation")
        
        if response.status_code == 201:
            conversation_id = response.json().get('id')
            
            # Send message
            message_data = {
                "content": "Hi, is the laptop still available?",
                "message_type": "text"
            }
            
            response = self.session.post(
                f"{BASE_URL}/conversations/{conversation_id}/send_message/", 
                json=message_data
            )
            self.print_response(response, "Send Message")
            
            # Get conversation messages
            response = self.session.get(f"{BASE_URL}/conversations/{conversation_id}/messages/")
            self.print_response(response, "Get Messages")
            
            # List conversations
            response = self.session.get(f"{BASE_URL}/conversations/")
            self.print_response(response, "List Conversations")
            
            return conversation_id
        return None
    
    def test_token_refresh(self):
        """Test JWT token refresh"""
        # This would require having a refresh token from login
        response = self.session.post(f"{BASE_URL}/auth/refresh/", json={})
        self.print_response(response, "Token Refresh (might fail without refresh token)")
    
    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting API Tests...")
        print(f"Base URL: {BASE_URL}")
        
        # Test registration and login
        if not self.test_user_registration():
            print("❌ Registration failed, trying login...")
            
        if not self.test_user_login():
            print("❌ Login failed, stopping tests")
            return
            
        print("✅ Authentication successful")
        
        # Test authenticated endpoints
        self.test_user_profile()
        
        # Test products
        category_id = self.test_categories()
        if category_id:
            product_id = self.test_products(category_id)
        
        # Test chat
        self.test_conversations()
        
        # Test misc
        self.test_token_refresh()
        
        print("\n🎉 API Testing Complete!")
        print("\n📊 Summary:")
        print("- Check the responses above for any errors")
        print("- 200/201 status codes indicate success")
        print("- 400/401/403/404/500 indicate issues to fix")


def main():
    """Main function to run tests"""
    print("Student Marketplace API Tester")
    print("Make sure Django server is running on http://127.0.0.1:8000")
    
    input("\nPress Enter to start tests...")
    
    tester = APITester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()