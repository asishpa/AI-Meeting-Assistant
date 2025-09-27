from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.config import settings

from app.db.base import Base
import app.models  # import your models here

# --- Alembic setup ---
config = context.config

# Load logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Replace async driver with psycopg2 for migrations
sync_url = settings.DATABASE_URL.replace("asyncpg", "psycopg2")
config.set_main_option("sqlalchemy.url", sync_url)

target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,          # <--- add this
        compare_type=True,             # <--- detect type changes
        compare_server_default=True,   # <--- detect default changes
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,          # <--- add this
            compare_type=True,             # <--- detect type changes
            compare_server_default=True,   # <--- detect default changes
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
