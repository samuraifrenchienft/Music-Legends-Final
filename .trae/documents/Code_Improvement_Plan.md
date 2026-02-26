
# Code Improvement Plan

This plan outlines several areas where the codebase can be improved for better maintainability, stability, and security.

## 1. Complete the Migration to Alembic for Database Schema Management

**Problem:** The `database.py` file contains a large number of `CREATE TABLE` statements, and there are also some `ALTER TABLE` statements. This indicates that the database schema is being managed manually, which is error-prone and not scalable. Although there are comments indicating that Alembic is being used, the presence of these `CREATE TABLE` statements suggests the migration is not complete.

**Proposed Solution:**

*   **Remove all `CREATE TABLE` and `ALTER TABLE` statements from `database.py`.**
*   **Ensure that all tables are defined as SQLAlchemy models in the `models/` directory.**
*   **Use Alembic to generate a migration script that creates all the tables.** This will involve:
    *   Ensuring that the Alembic environment is correctly configured to use the `Base` from the models.
    *   Running `alembic revision --autogenerate` to create the migration script.
    *   Reviewing the generated migration script to ensure it is correct.
*   **Apply the migration to the database.**

## 2. Refactor the Database Layer to Use the SQLAlchemy ORM

**Problem:** The database layer uses a mix of raw SQL queries and a custom wrapper to provide compatibility between SQLite and PostgreSQL. This adds unnecessary complexity and can lead to security vulnerabilities like SQL injection.

**Proposed Solution:**

*   **Replace all raw SQL queries with SQLAlchemy ORM queries.** This will make the code more readable, maintainable, and secure.
*   **Remove the `_PgCursorWrapper` and `_PgConnectionWrapper` classes.** These wrappers are no longer needed once all queries are using the ORM.
*   **Use the SQLAlchemy `Session` object to interact with the database.** This will provide a consistent and high-level API for all database operations.
*   **Choose one database for production and development.** Using the same database (PostgreSQL) for both environments will eliminate the need for the compatibility layer and simplify the code.

## 3. Separate the Web Server and the Discord Bot

**Problem:** The `app.py` file runs both the Flask web server and the Discord bot in the same process. This is not a robust architecture for a production application.

**Proposed Solution:**

*   **Run the Flask/FastAPI application and the Discord bot as separate processes.**
*   **Use a process manager like Gunicorn for the web application and a supervisor like `systemd` for the bot.** This will make the application more stable and easier to manage.
*   **Consider replacing Flask with FastAPI for the webhooks.** Since the project already uses FastAPI for the TMA, using it for the webhooks as well would unify the web framework and allow for the use of async-native code.

## 4. Improve Configuration and Secrets Management

**Problem:** While the `config.py` file is a good start, there are still some areas for improvement in configuration and secrets management.

**Proposed Solution:**

*   **Add comments to the `config.py` file to explain the purpose of each setting.**
*   **Add a reminder to the `README.md` or a new `CONTRIBUTING.md` file about not committing the `.env` file to version control.**
*   **Disable the debug endpoints in production.** The `tma/api/main.py` file has a `/api/debug` endpoint that should be disabled or protected in a production environment.

## 5. Refactor the Startup Logic

**Problem:** The `setup_hook` in `main.py` is very large and complex.

**Proposed Solution:**

*   **Break down the `setup_hook` into smaller, more focused functions.** For example, have separate functions for setting up the database, loading cogs, and setting up backups.
*   **Use the `logging` module more consistently for structured logging.**
*   **Move the list of cogs to be loaded to the `config.py` file.** This will make it easier to enable or disable cogs without changing the code.

## 6. Address Potential SQL Injection Vulnerabilities

**Problem:** There are several places in the code where f-strings are used to build SQL queries. This is a serious security vulnerability.

**Proposed Solution:**

*   **Replace all f-string-based queries with parameterized queries.** All parameters should be passed to the `execute` method as a tuple to be properly sanitized. This is a high-priority task. The refactoring to the SQLAlchemy ORM will also solve this problem.
