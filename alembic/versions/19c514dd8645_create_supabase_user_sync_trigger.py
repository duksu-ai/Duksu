"""create_supabase_user_sync_trigger

Revision ID: 19c514dd8645
Revises: acf7562b405f
Create Date: 2025-07-05 09:47:08.239652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19c514dd8645'
down_revision: Union[str, Sequence[str], None] = 'acf7562b405f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create a function to handle user creation
    op.execute("""
        CREATE OR REPLACE FUNCTION handle_new_user()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Insert into public.users table when a new user is created in auth.users
            -- Use the auth user's id as auth_id and email as user_id (or id as fallback)
            INSERT INTO public.users (user_id, auth_id, created_at, updated_at)
            VALUES (
                COALESCE(NEW.email, NEW.id::text), 
                NEW.id, 
                NEW.created_at, 
                NEW.updated_at
            )
            ON CONFLICT (user_id) DO UPDATE SET
                auth_id = EXCLUDED.auth_id,
                updated_at = EXCLUDED.updated_at;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Create a function to handle user deletion
    op.execute("""
        CREATE OR REPLACE FUNCTION handle_user_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Delete the corresponding record in public.users when auth.users is deleted
            DELETE FROM public.users
            WHERE auth_id = OLD.id;
            
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Create the trigger on auth.users table for INSERT
    op.execute("""
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW
            EXECUTE FUNCTION handle_new_user();
    """)
    
    # Create the trigger on auth.users table for DELETE
    op.execute("""
        CREATE TRIGGER on_auth_user_deleted
            BEFORE DELETE ON auth.users
            FOR EACH ROW
            EXECUTE FUNCTION handle_user_delete();
    """)
    
    # Grant necessary permissions for the trigger functions
    op.execute("""
        GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
        GRANT INSERT, UPDATE, DELETE ON public.users TO supabase_auth_admin;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the triggers
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_deleted ON auth.users;")
    
    # Drop the functions
    op.execute("DROP FUNCTION IF EXISTS handle_new_user();")
    op.execute("DROP FUNCTION IF EXISTS handle_user_delete();")
    
    # Revoke permissions
    op.execute("REVOKE INSERT, UPDATE, DELETE ON public.users FROM supabase_auth_admin;")
    op.execute("REVOKE USAGE ON SCHEMA public FROM supabase_auth_admin;")
