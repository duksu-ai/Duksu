# Duksu


## Setup
1. Install uv (if not already installed):
```bash
curl -sSf https://install.ultraviolet.rs | sh
```

2. Create virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate
uv sync
```

3. Set up environment variables (edit the `.env` file with your API keys):
```bash
cp .env.example .env
```

4. Install PostgreSQL:  
Download and install local PostgreSQL from [https://www.postgresql.org/download/](https://www.postgresql.org/download/)  

5. Configure database connection:
Edit the `DATABASE_URL` in your `.env` file. The default value is for user `postgres` with password `1234`:
```
DATABASE_URL=postgresql+psycopg2://<username>:<password>@localhost:<port>/duksu
e.g.
DATABASE_URL=postgresql+psycopg2://postgres:1234@localhost:5432/duksu
```

6. Run initial database migrations:
```bash
alembic upgrade head
```

## Migration

Apply migrations when new migration files are added:
```bash
alembic upgrade head
```

If you have modified existing migration files and want to reapply them:
1. Rollback migrations (where `i` is the number of migration files from latest to revert):
```bash
alembic downgrade -i
```
2. Then apply migrations again:
```bash
alembic upgrade head
```


## Usage

```bash
python -m duksu_exec.cli --help
```

### Create a new user
```bash
python -m duksu_exec.cli add-user --user_id=<user id>
```

### Create a feed associated with a user
```bash
python -m duksu_exec.cli create-news-feed --user_id=<user id> --query_prompt="<query prompt>"
```

### Populate feed with curated news articles that match the user's query prompt
```bash
python -m duksu_exec.cli populate-feed --feed_id=<feed_id>
```


## LangSmith
```bash
langgraph dev
```