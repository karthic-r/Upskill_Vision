import unittest
import sqlite3
import os
import pandas as pd
from flask import session
from app import app, get_db_connection

class TestInstructorDashboard(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.test_database = "test_upskill_vision.db"
        app.config['DATABASE'] = cls.test_database
        app.config['TESTING'] = True
        cls.client = app.test_client()

        with app.app_context():
            if os.path.exists(cls.test_database):
                os.remove(cls.test_database)
            cls._init_test_db()
    
    @classmethod
    def _init_test_db(cls):
        conn = sqlite3.connect(cls.test_database)
        cursor = conn.cursor()
        
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS courses")
        cursor.execute("DROP TABLE IF EXISTS enrollment")
        cursor.execute("DROP TABLE IF EXISTS quiz_attempt")
        
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE enrollment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                course_id INTEGER,
                progress INTEGER,
                enrollment_date TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(course_id) REFERENCES courses(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE quiz_attempt (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                course_id INTEGER,
                quiz_score INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(course_id) REFERENCES courses(id)
            )
        ''')
        
        cursor.executemany("INSERT INTO users (email, role) VALUES (?, ?)", [
            ("student1@example.com", "student"),
            ("student2@example.com", "student"),
            ("instructor@example.com", "instructor")
        ])
        
        cursor.executemany("INSERT INTO courses (title) VALUES (?)", [
            ("Python Basics",),
            ("Data Science",)
        ])
        
        cursor.executemany("INSERT INTO enrollment (user_id, course_id, progress, enrollment_date) VALUES (?, ?, ?, ?)", [
            (1, 1, 80, "2024-01-10"),
            (2, 2, 100, "2024-02-15")
        ])
        
        cursor.executemany("INSERT INTO quiz_attempt (user_id, course_id, quiz_score) VALUES (?, ?, ?)", [
            (1, 1, 85),
            (2, 2, 90)
        ])
        
        conn.commit()
        conn.close()
    
    @classmethod
    def tearDownClass(cls):
        conn = sqlite3.connect(cls.test_database)
        conn.close()
        if os.path.exists(cls.test_database):
            os.remove(cls.test_database)

    def test_progress_tracking(self):
        """Verify progress updates correctly."""
        with app.app_context():
            conn = get_db_connection()
            df = pd.read_sql_query("SELECT progress FROM enrollment", conn)
            conn.close()
        
        self.assertFalse(df.empty)
        self.assertTrue(all(df["progress"] >= 0))  # Progress should be non-negative
        
    def test_performance_graph(self):
        """Check if graphs generate accurately."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user'] = 'instructor@example.com'
                sess['role'] = 'instructor'
            
            response = client.get('/instructor_dashboard')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Course Completion Percentage', response.data)
            self.assertIn(b'Course Status', response.data)
    
    def test_course_completion(self):
        """Verify course completion calculation."""
        with app.app_context():
            conn = get_db_connection()
            df = pd.read_sql_query("SELECT progress FROM enrollment", conn)
            conn.close()
        
        completed_courses = df[df["progress"] >= 100].shape[0]
        self.assertGreaterEqual(completed_courses, 1)
        
if __name__ == "__main__":
    unittest.main()
