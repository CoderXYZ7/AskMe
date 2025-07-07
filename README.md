# AskMe - Project Request Management System

A simple web application for managing project requests and feedback.

## Features

### Admin Features
- **Simple Login System**: Hardcoded admin credentials (username: admin, password: admin123)
- **Project Management**: Create, lock/unlock, and delete projects
- **Request Management**: View, approve/reject, respond to, tag, block, and delete requests
- **Status Tracking**: Mark requests as pending, approved, rejected, or completed
- **User Blocking**: Block specific requests from being visible to users

### User Features
- **Anonymous Access**: No registration required
- **IP-based Usernames**: Automatic username generation based on IP address
- **Request Submission**: Submit requests to available (unlocked) projects
- **Request Tracking**: View your own requests and their status
- **Admin Responses**: See admin responses to your requests

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Access the Application**:
   - User Interface: http://localhost:5000
   - Admin Interface: http://localhost:5000/admin/login

## Default Admin Credentials

- **Username**: admin
- **Password**: admin123

> **Important**: Change these credentials in production by modifying the `ADMIN_USERNAME` and `ADMIN_PASSWORD` variables in `app.py`.

## Database

The application uses SQLite and automatically creates the database file (`askme.db`) on first run. The database includes:

- **Projects Table**: Stores project information and lock status
- **Requests Table**: Stores user requests with status, tags, and admin responses

## Project Structure

```
AskMe/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── askme.db              # SQLite database (created automatically)
└── templates/            # HTML templates
    ├── base.html         # Base template with common layout
    ├── index.html        # Home page showing projects
    ├── admin_login.html  # Admin login page
    ├── admin_dashboard.html # Admin management interface
    └── project_detail.html  # Project page for users
```

## Usage

### For Administrators

1. Login at `/admin/login` with the default credentials
2. Create projects using the form in the admin dashboard
3. Manage requests by clicking the edit button on any request
4. Lock projects to prevent new requests
5. Delete projects and requests as needed

### For Users

1. Visit the home page to see available projects
2. Click on a project to view details and submit requests
3. Fill out the request form with a title and description
4. View your previous requests and admin responses on the project page

## Security Notes

- This is a simple application with basic security measures
- Admin credentials are hardcoded and should be changed for production use
- User identification is based on IP addresses only
- No input sanitization beyond basic Flask protections
- Suitable for internal/development use, not production environments

## Customization

You can easily customize the application by:

- Modifying the admin credentials in `app.py`
- Updating the CSS styles in `templates/base.html`
- Adding new request statuses or fields
- Implementing additional user authentication methods
