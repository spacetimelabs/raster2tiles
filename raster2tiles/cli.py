# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import json
from os import path
from datetime import datetime
from cStringIO import StringIO
import psycopg2
import numpy as np
import scipy.misc
from sqlalchemy.dialects.postgresql import insert
from raster2tiles import database
from raster2tiles.tile import open_raster, raster2tiles


def _create_tile_dict(tileset, zoom, ty, tx, scene_date, data, metadata=None):
    return {
        'tileset': tileset,
        'zoom_level': zoom,
        'tile_column': tx,
        'tile_row': ty,
        'date': scene_date,
        'metadata': metadata,
        'tile_data': data
    }


def _insert_batch(db, batch):
    stmt = insert(database.tiles).values(batch)
    stmt = stmt.on_conflict_do_update(
        index_elements=('tileset', 'zoom_level', 'tile_column', 'tile_row', 'date'),
        set_=dict(metadata=stmt.excluded.metadata, tile_data=stmt.excluded.tile_data)
    )
    return db.execute(stmt)


def main(args):
    input_filepath = args[1]
    database_uri = args[2]
    tileset = args[3]
    image_format = args[4] if len(args) == 5 else 'png'

    scene_id = path.basename(input_filepath).split('_')[0]
    satellite = scene_id[:3]
    scene_path, scene_row = int(scene_id[3:6]), int(scene_id[5:9])
    year_yday = scene_id[9:16]
    scene_date = datetime.strptime(year_yday, '%Y%j')

    db_conn = database.create_connection(database_uri)
    database.create_tables(db_conn)

    batch, max_batch_size = [], 100

    input_raster = open_raster(input_filepath)
    for (zoom, ty, tx), data in raster2tiles(input_raster):
        if data.shape[2] == 1:
            data = np.squeeze(data)

        im = scipy.misc.toimage(data, 255, 0, mode='RGBA')
        buffer = StringIO()
        im.save(buffer, image_format)
        buffer.seek(0)

        print('{}/{}/{}'.format(zoom, tx, ty))
        metadata = {
            'satellite': satellite,
            'cloud_cover': 0.0,
            'scene_id': scene_id,
            'scene_path': scene_path,
            'scene_row': scene_row
        }
        new_tile = _create_tile_dict(tileset, zoom, ty, tx, scene_date, buffer.read(), metadata)
        batch.append(new_tile)

        if len(batch) > max_batch_size:
            _insert_batch(db_conn, batch)
            batch = []
    if batch:
        _insert_batch(db_conn, batch)


def go():
    main(sys.argv)


if __name__ == '__main__':
    go()
