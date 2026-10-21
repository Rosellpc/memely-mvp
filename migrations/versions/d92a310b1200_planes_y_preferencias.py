"""Add preferences, weekly plans, meals and shared auth throttling.

Revision ID: d92a310b1200
Revises: c4b08eaaf62f
"""
from alembic import op
import sqlalchemy as sa

revision = 'd92a310b1200'
down_revision = 'c4b08eaaf62f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('perfiles', sa.Column('preferencia', sa.String(20), server_default='balanced', nullable=False))
    op.create_check_constraint('ck_perfiles_preferencia', 'perfiles', "preferencia IN ('balanced', 'vegetarian')")
    op.create_table('planes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('preferencia', sa.String(20), nullable=False),
        sa.Column('fecha_inicio', sa.Date(), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("preferencia IN ('balanced', 'vegetarian')", name='ck_planes_preferencia'),
    )
    op.create_index('ix_planes_usuario_id', 'planes', ['usuario_id'])
    op.create_table('comidas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('planes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dia', sa.Integer(), nullable=False),
        sa.Column('momento', sa.String(20), nullable=False),
        sa.Column('titulo', sa.String(200), nullable=False),
        sa.Column('completada', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.CheckConstraint('dia BETWEEN 0 AND 6', name='ck_comidas_dia'),
        sa.CheckConstraint("momento IN ('desayuno', 'almuerzo', 'cena')", name='ck_comidas_momento'),
        sa.UniqueConstraint('plan_id', 'dia', 'momento', name='uq_comidas_plan_dia_momento'),
    )
    op.create_index('ix_comidas_plan_id', 'comidas', ['plan_id'])
    op.create_table('login_limits',
        sa.Column('clave', sa.String(64), primary_key=True),
        sa.Column('intentos', sa.Integer(), nullable=False),
        sa.Column('expira_en', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_login_limits_expira_en', 'login_limits', ['expira_en'])


def downgrade():
    op.drop_table('login_limits')
    op.drop_table('comidas')
    op.drop_table('planes')
    op.drop_constraint('ck_perfiles_preferencia', 'perfiles', type_='check')
    op.drop_column('perfiles', 'preferencia')
