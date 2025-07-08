import unittest
import sqlite3
import os
from flask import Flask, session
from app import app  # Import your Flask app
import pandas as pd

class TestAdminDashboard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_database = "test_upskill_vision.db"
        app.config['DATABASE'] = cls.test_database
        app.config['TESTING'] = True
        cls.client = app.test_client()

        # Initialize test database
        with app.app_context():
            if os.path.exists(cls.test_database):
                os.remove(cls.test_database)
            cls._init_test_db()

    @classmethod
    def _init_test_db(cls):
        """Initialize the test database with required tables and data"""
        try:
            conn = sqlite3.connect(cls.test_database)
            cursor = conn.cursor()

            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    is_verified INTEGER DEFAULT 0,
                    approval_status TEXT NOT NULL DEFAULT 'pending'
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    duration INTEGER,
                    instructor_id INTEGER,
                    start_date TEXT,
                    end_date TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enrollment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Active',
                    progress INTEGER NOT NULL DEFAULT 0,
                    enrollment_date TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quiz_attempt (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quiz_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    attempt_date TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    feedback_date TEXT NOT NULL,
                    comment TEXT,
                    rate INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )
            ''')

            # Insert test data
            cursor.execute("INSERT INTO users (name, email, password, role, is_verified, approval_status) VALUES ('Admin', 'admin@admin.com', 'admin@123', 'admin', 1, 'approved')")
            cursor.execute("INSERT INTO users (name, email, password, role, is_verified, approval_status) VALUES ('User One', 'user1@test.com', 'user@123', 'user', 1, 'approved')")
            cursor.execute("INSERT INTO users (name, email, password, role, is_verified, approval_status) VALUES ('User Two', 'user2@test.com', 'user@123', 'user', 0, 'pending')")

            cursor.execute("INSERT INTO courses (title, description, duration, instructor_id, start_date, end_date) VALUES ('Python Basics', 'Learn Python from scratch', 30, 1, '2025-03-01', '2025-04-01')")
            cursor.execute("INSERT INTO courses (title, description, duration, instructor_id, start_date, end_date) VALUES ('Data Science', 'Intro to Data Science', 45, 1, '2025-03-10', '2025-04-25')")

            cursor.execute("INSERT INTO enrollment (user_id, course_id, status, progress, enrollment_date) VALUES (1, 1, 'Active', 100, '2025-03-01')")
            cursor.execute("INSERT INTO enrollment (user_id, course_id, status, progress, enrollment_date) VALUES (2, 2, 'Active', 50, '2025-03-02')")

            cursor.execute("INSERT INTO quiz_attempt (quiz_id, user_id, attempt_date, score, status) VALUES (1, 1, '2025-03-11', 85, 'Passed')")
            cursor.execute("INSERT INTO quiz_attempt (quiz_id, user_id, attempt_date, score, status) VALUES (2, 2, '2025-03-12', 60, 'Passed')")

            cursor.execute("INSERT INTO feedback (user_id, course_id, feedback_date, comment, rate) VALUES (1, 1, '2025-03-10', 'Great course!', 5)")
            cursor.execute("INSERT INTO feedback (user_id, course_id, feedback_date, comment, rate) VALUES (2, 2, '2025-03-12', 'Informative but needs more examples.', 4)")

            conn.commit()
        finally:
            conn.close()

    @classmethod
    def tearDownClass(cls):
        """Remove test database"""
        if os.path.exists(cls.test_database):
            os.remove(cls.test_database)

    def setUp(self):
        """Login as admin before each test"""
        with self.client as client:
            client.post('/admin_login', data={'email': 'admin@admin.com', 'password': 'admin@123'})

    def tearDown(self):
        """Logout admin after each test"""
        with self.client as client:
            client.get('/admin_logout')

    def test_progress_tracking(self):
        """Verify that progress updates are recorded correctly"""
        conn = sqlite3.connect(self.test_database)
        cursor = conn.cursor()
        cursor.execute("SELECT progress FROM enrollment WHERE user_id = 1")
        progress = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(progress, 100, "Progress tracking is incorrect")

    def test_performance_graph(self):
        """Check if performance graphs generate accurately"""
        response = self.client.get('/completion_plot')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'PNG', response.data, "Graph generation failed")

    def test_course_completion(self):
        """Verify course completion calculation is accurate"""
        conn = sqlite3.connect(self.test_database)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM enrollment WHERE progress = 100")
        completed_courses = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(completed_courses, 1, "Incorrect course completion calculation")

if __name__ == '__main__':
    unittest.main()
