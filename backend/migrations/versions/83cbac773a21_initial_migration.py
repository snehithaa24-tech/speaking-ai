"""initial migration

Revision ID: 83cbac773a21
Revises: 
Create Date: 2026-11-16 12:40:16.302851

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83cbac773a21'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('picture', sa.String(length=500), nullable=True),
        sa.Column('preferred_language', sa.String(length=10), nullable=False, server_default='en-IN'),
        sa.Column('role', sa.Enum('USER', 'ADMIN', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. sessions
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'ERROR', 'INTERRUPTED', name='sessionstatus'), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en-IN'),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.create_index('ix_sessions_user_started', 'sessions', ['user_id', 'started_at'], unique=False)

    # 3. conversation_messages
    op.create_table(
        'conversation_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('speaker', sa.Enum('USER', 'ASSISTANT', name='speakertype'), nullable=False),
        sa.Column('transcript', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en-IN'),
        sa.Column('is_final', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversation_messages_session_id'), 'conversation_messages', ['session_id'], unique=False)
    op.create_index('ix_messages_session_timestamp', 'conversation_messages', ['session_id', 'timestamp'], unique=False)

    # 4. feedback
    op.create_table(
        'feedback',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_session_id'), 'feedback', ['session_id'], unique=False)

    # 5. knowledge_documents
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('category', sa.Enum('AGRICULTURE', 'GOVERNMENT_SCHEMES', 'TRANSPORT', 'HOSPITAL_ASSISTANCE', 'GENERAL', name='knowledgecategory'), nullable=False),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en-IN'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_documents_category'), 'knowledge_documents', ['category'], unique=False)
    op.create_index('ix_knowledge_category_language', 'knowledge_documents', ['category', 'language'], unique=False)

    # 6. evaluation_records
    op.create_table(
        'evaluation_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('test_category', sa.String(length=100), nullable=False),
        sa.Column('result', sa.Enum('PASS', 'FAIL', 'PARTIAL', name='evaluationresult'), nullable=False),
        sa.Column('measured_latency', sa.Integer(), nullable=True),
        sa.Column('word_error_rate', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_records_language'), 'evaluation_records', ['language'], unique=False)
    op.create_index('ix_evaluation_language_category', 'evaluation_records', ['language', 'test_category'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_evaluation_language_category', table_name='evaluation_records')
    op.drop_index(op.f('ix_evaluation_records_language'), table_name='evaluation_records')
    op.drop_table('evaluation_records')

    op.drop_index('ix_knowledge_category_language', table_name='knowledge_documents')
    op.drop_index(op.f('ix_knowledge_documents_category'), table_name='knowledge_documents')
    op.drop_table('knowledge_documents')

    op.drop_index(op.f('ix_feedback_session_id'), table_name='feedback')
    op.drop_table('feedback')

    op.drop_index('ix_messages_session_timestamp', table_name='conversation_messages')
    op.drop_index(op.f('ix_conversation_messages_session_id'), table_name='conversation_messages')
    op.drop_table('conversation_messages')

    op.drop_index('ix_sessions_user_started', table_name='sessions')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_table('sessions')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
