#!/usr/bin/env python3

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db

def test_app():
    """Simple test to verify the application works"""
    
    # Initialize the database
    init_db()
    
    # Create a test client
    app.config['TESTING'] = True
    with app.test_client() as client:
        
        print("Testing AskMe application...")
        
        # Test home page
        print("1. Testing home page...")
        response = client.get('/')
        assert response.status_code == 200
        assert b'Welcome to AskMe' in response.data
        print("   ✓ Home page loads correctly")
        
        # Test admin login page
        print("2. Testing admin login page...")
        response = client.get('/admin/login')
        assert response.status_code == 200
        assert b'Admin Login' in response.data
        print("   ✓ Admin login page loads correctly")
        
        # Test admin login
        print("3. Testing admin authentication...")
        response = client.post('/admin/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Admin Dashboard' in response.data
        print("   ✓ Admin login works correctly")
        
        # Test project creation
        print("4. Testing project creation...")
        response = client.post('/admin/project/create', data={
            'name': 'Test Project',
            'description': 'A test project for verification'
        }, follow_redirects=True)
        assert response.status_code == 200
        print("   ✓ Project creation works correctly")
        
        # Test project visibility on home page
        print("5. Testing project visibility...")
        response = client.get('/')
        assert response.status_code == 200
        assert b'Test Project' in response.data
        print("   ✓ Projects display correctly on home page")
        
        # Test project detail page
        print("6. Testing project detail page...")
        # Get the first available project ID
        from app import get_db
        conn = get_db()
        project = conn.execute('SELECT id FROM projects WHERE is_locked = 0 LIMIT 1').fetchone()
        project_id = project['id'] if project else 1
        conn.close()
        
        response = client.get(f'/project/{project_id}')
        assert response.status_code == 200
        assert b'Submit New Request' in response.data
        print("   ✓ Project detail page works correctly")
        
        # Test request submission
        print("7. Testing request submission...")
        response = client.post(f'/project/{project_id}/request', data={
            'title': 'Test Request',
            'description': 'This is a test request'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Request submitted successfully' in response.data
        print("   ✓ Request submission works correctly")
        
        print("\n🎉 All tests passed! The AskMe application is working correctly.")
        print("\nTo run the application:")
        print("1. Activate virtual environment: source venv/bin/activate")
        print("2. Run the app: python app.py")
        print("3. Visit http://localhost:5000")
        print("4. Admin login: http://localhost:5000/admin/login (admin/admin123)")

if __name__ == '__main__':
    test_app()
