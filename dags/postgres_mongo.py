"""
A DAG that extracts from Postgres and upserts in MongoDB.
"""

import psycopg2
import pymongo
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


with DAG(
    "postgres_mongo",
    schedule_interval="@daily",
    start_date=datetime(2025, 5, 9)
    ):
    echo_start = BashOperator(task_id="echo_start", bash_command="echo 'Start check from PostgreSQL and upsert to MongoDB'")

    def _postgres_read():
        connection = psycopg2.connect("host=127.0.0.1 dbname=ramayanquiz user=postgres password=abc")
        cursor = connection.cursor()
        query = "select id, difficulty, question from questions;"
        print("Executing query")
        cursor.execute(query)
        print("Fetching result")
        db_rows = cursor.fetchall()
        columns = [col.name for col in cursor.description]
        rows = []
        for db_row in db_rows:
            rows.append({k: v for k, v in zip(columns, db_row)})
        connection.close()
        print(rows)
        return rows

    def _mongo_update(postgres_rows):
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client.ramayanquiz
        collection = db.questions
        print("Processing Postgres rows with Mongo")
        for row in postgres_rows:
            query = {'question': row['question']}
            update_clause = {'$set': {'difficulty': row['difficulty']}}
            collection.update_many(query, update_clause)

    def etl():
        rows = _postgres_read()
        _mongo_update(rows)

    etl = PythonOperator(task_id="etl", python_callable=etl)

    echo_start >> etl
