## Overview

[![Linting](https://github.com/akshar-raaj/ramayanquiz/actions/workflows/linting.yml/badge.svg)](https://github.com/akshar-raaj/ramayanquiz/actions/workflows/linting.yml)  [![Unit Tests](https://github.com/akshar-raaj/ramayanquiz/actions/workflows/unit_tests.yml/badge.svg)](https://github.com/akshar-raaj/ramayanquiz/actions/workflows/unit_tests.yml) [![Test Coverage](https://github.com/akshar-raaj/ramayanquiz/blob/master/coverage.svg)](https://github.com/akshar-raaj/ramayanquiz/actions/workflows/code_coverage.yml)

An application at the intersection of my 3 interests:
- Software Engineering
- Quizzing
- Ramacharitamanas(रामचरितमानस)

This application drives ramayanquiz.com backend.

## Tech Stack

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-%234ea94b.svg?style=for-the-badge&logo=mongodb&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)

| Category | Option |
|----|-----|
| Programming Language | Python, a mature language enabling Rapid Application Development. Let's talk about Duck Typing! |
| API Framework | FastAPI, a modern and performant API framework |
| Transactional Database | PostgreSQL |
| Standby Database | MongoDB |
| Message Broker | RabbitMQ |
| Workflow Management | Airflow |
| SQL Toolkit | SQLAlchemy |
| Unit Testing | Pytest |
| CI/CD | Github Action |

## Feature List
- Database tables for entities - Done
- API to create questions - Done
- Add questions through csv upload - Done
- Secure the API - Done
- Persist user answers to localstorage - Done
- User answer report:
  - Pie chart: Unattempted, attempted
  - Pie chart: Correct, Incorrect - Done
  - Bar chart: Correct, incorrect for difficulty levels - Done
  - Bar chart: Correct, incorrect for tags
  - Stacked Bar chart: Total, correct, incorrect for difficulty levels
- Share report on Linkedin, Twitter and Facebook
- Hindi translation
- Allow users to upvote or downvote a question
- Allow users to contribute a question
- Before contributing, search if a similar question exists
- Give an information icon in front of each question. This gives context about this question.

## More
Along with PostgreSQL, we will also use MongoDB. This is only for demonstration purpose to understand which things are easy/difficult in PostgreSQL vs MongoDB.

Compare Elasticsearch with Postgres full text search.

Compare Redis with memcache and see if Redis in-built data structures provide an advantage compared to storing everything as JSON dump.

Introduce an Analytical database to perform analytical queries which can generate reports.

Implement websocket so that any new question added starts showing up immediately.

Add ML to predict the kanda and difficulty for a question

Implement suggestions and question recommendations based on earlier questions attempted.

Add badges:
- pylint

Mobile Application
