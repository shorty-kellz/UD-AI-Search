#!/usr/bin/env python3
"""
Test Questions Ingestor

This script reads test questions from a text file and stores them in the database.
Each line in the file is treated as a separate test question.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add the backend directory to the path to import database modules
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

from database import get_connection


def create_test_questions_table(conn):
    """Create the test_questions table if it doesn't exist"""
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL UNIQUE
        )
    ''')
    
    conn.commit()
    print("✅ Test questions table created/verified")


def read_test_questions_file(file_path):
    """Read test questions from the text file"""
    questions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    questions.append({
                        'line_number': line_num,
                        'question_text': line
                    })
        
        print(f"✅ Read {len(questions)} questions from {file_path}")
        return questions
        
    except FileNotFoundError:
        print(f"❌ Error: Test questions file not found at {file_path}")
        return []
    except Exception as e:
        print(f"❌ Error reading test questions file: {e}")
        return []


def insert_test_questions(conn, questions):
    """Insert test questions into the database"""
    cursor = conn.cursor()
    inserted_count = 0
    skipped_count = 0
    
    for question_data in questions:
        try:
            cursor.execute('''
                INSERT INTO test_questions (question_text)
                VALUES (?)
            ''', (question_data['question_text'],))
            inserted_count += 1
            
        except sqlite3.IntegrityError:
            # Question already exists (UNIQUE constraint)
            skipped_count += 1
            print(f"⚠️ Skipped duplicate question (line {question_data['line_number']}): {question_data['question_text'][:50]}...")
            
        except Exception as e:
            print(f"❌ Error inserting question (line {question_data['line_number']}): {e}")
    
    conn.commit()
    print(f"✅ Inserted {inserted_count} new questions")
    print(f"⚠️ Skipped {skipped_count} duplicate questions")


def main():
    """Main function to ingest test questions"""
    print("🚀 Starting test questions ingestion...")
    
    # Get the path to the test questions file
    data_dir = Path(__file__).parent.parent / "data"
    test_questions_file = data_dir / "test_questions.txt"
    
    if not test_questions_file.exists():
        print(f"❌ Test questions file not found at: {test_questions_file}")
        print("Please create a test_questions.txt file in the data folder with one question per line.")
        return
    
    # Get database connection
    try:
        with get_connection() as conn:
            print("✅ Connected to database")
            
            # Create the table
            create_test_questions_table(conn)
            
            # Read questions from file
            questions = read_test_questions_file(test_questions_file)
            
            if not questions:
                print("❌ No questions found to insert")
                return
            
            # Insert questions into database
            insert_test_questions(conn, questions)
            
            # Display summary
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test_questions")
            total_count = cursor.fetchone()[0]
            print(f"📊 Total test questions in database: {total_count}")
            
            print("✅ Test questions ingestion completed successfully!")
            
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        return


if __name__ == "__main__":
    main() 