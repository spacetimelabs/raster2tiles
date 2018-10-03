# -*- coding: utf-8 -*-

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


metadata = sa.MetaData()

# TODO: compound index with zoom, column and row
tiles = sa.Table(
    'tiles',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('zoom_level', sa.Integer),
    sa.Column('tile_column', sa.Integer),
    sa.Column('tile_row', sa.Integer),
    sa.Column('tileset', sa.String, nullable=False, index=True),
    sa.Column('date', sa.Date, nullable=True, index=True),
    sa.Column('metadata', JSONB, nullable=True),
    sa.Column('tile_data', sa.Binary),
    sa.UniqueConstraint('tileset', 'zoom_level', 'tile_column', 'tile_row', 'date', name='uniq_tile')
)


def create_connection(uri):
    """Create a database connection."""
    return sa.create_engine(uri)


def create_tables(db):
    """Create database tables."""
    return metadata.create_all(db)
