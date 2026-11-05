"""strengthen account-household consistency constraints

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_accounts_id_household', ['id', 'household_id'])

    with op.batch_alter_table('imports', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_imports_id_household', ['id', 'household_id'])
        batch_op.create_unique_constraint('uq_imports_id_account', ['id', 'account_id'])
        batch_op.create_foreign_key(
            'fk_imports_account_household',
            'accounts',
            ['account_id', 'household_id'],
            ['id', 'household_id'],
            ondelete='CASCADE'
        )

    with op.batch_alter_table('staged_transactions', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_staged_account_household',
            'accounts',
            ['account_id', 'household_id'],
            ['id', 'household_id'],
            ondelete='CASCADE'
        )
        batch_op.create_foreign_key(
            'fk_staged_import_account',
            'imports',
            ['import_id', 'account_id'],
            ['id', 'account_id'],
            ondelete='CASCADE'
        )
        batch_op.create_foreign_key(
            'fk_staged_import_household',
            'imports',
            ['import_id', 'household_id'],
            ['id', 'household_id'],
            ondelete='CASCADE'
        )

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_transactions_account_household',
            'accounts',
            ['account_id', 'household_id'],
            ['id', 'household_id']
        )
        batch_op.create_foreign_key(
            'fk_transactions_import_account',
            'imports',
            ['import_id', 'account_id'],
            ['id', 'account_id']
        )
        batch_op.create_foreign_key(
            'fk_transactions_import_household',
            'imports',
            ['import_id', 'household_id'],
            ['id', 'household_id']
        )


def downgrade():
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_transactions_import_household', type_='foreignkey')
        batch_op.drop_constraint('fk_transactions_import_account', type_='foreignkey')
        batch_op.drop_constraint('fk_transactions_account_household', type_='foreignkey')

    with op.batch_alter_table('staged_transactions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_staged_import_household', type_='foreignkey')
        batch_op.drop_constraint('fk_staged_import_account', type_='foreignkey')
        batch_op.drop_constraint('fk_staged_account_household', type_='foreignkey')

    with op.batch_alter_table('imports', schema=None) as batch_op:
        batch_op.drop_constraint('fk_imports_account_household', type_='foreignkey')
        batch_op.drop_constraint('uq_imports_id_account', type_='unique')
        batch_op.drop_constraint('uq_imports_id_household', type_='unique')

    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.drop_constraint('uq_accounts_id_household', type_='unique')

