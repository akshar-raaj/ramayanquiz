## Overview

An application at the intersection of my 3 interests:
- Software Engineering
- Quizzing
- Religion

This application drives ramayanquiz.com backend.

It has the following features:
- Create a question
- Associate choices with a question
- Mark one of the choices as correct answer for the question

## Tech Stack

Programming Language: Python, a mature language enabling Rapid Application Development. Let's talk about Duck Typing!
API Framework: FastAPI, a modern and performant API framework.
Transactional Database: PostgreSQL
SQL Toolkit: SQLAlchemy
Unit Testing: Pytest
CI/CD: Github Action
Search backend: Elasticsearch
Cache: Redis
Message Queue: RabbitMQ
Background Task Processing: Celery

## Feature List
- Database tables for entities
- API to create questions
- Add questions through csv upload
- User authentication
- Associate user and answer
- Track user's answers
- User answer report:
  - Pie chart: Unattempted, attempted
  - Pie chart: Correct, Incorrect
  - Bar chart: Correct, incorrect for difficulty levels
  - Bar chart: Correct, incorrect for tags
  - Stacked Bar chart: Total, correct, incorrect for difficulty levels
- Share report on Linkedin, Twitter and Facebook

## More
Along with PostgreSQL, we will also use MongoDB. This is only for demonstration purpose to understand which things are easy/difficult in PostgreSQL vs MongoDB.

Compare Elasticsearch with Postgres full text search.

Compare Redis with memcache and see if Redis in-built data structures provide an advantage compared to storing everything as JSON dump.

Introduce an Analytical database to perform analytical queries which can generate reports.

Implement websocket so that any new question added starts showing up immediately.

Add ML to predict the kanda and difficulty for a question

Implement suggestions and question recommendations based on earlier questions attempted.