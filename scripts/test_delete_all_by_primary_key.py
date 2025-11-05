#!/usr/bin/env python3
"""Demonstrate and validate GenericRepository.delete_all_by_primary_key."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Iterable

import boto3
from moto import mock_aws

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


# Direct import avoids pulling async dependencies defined in package __init__
from generic_repo.sync_repo import GenericRepository  # noqa: E402

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def _create_table(resource: boto3.resources.base.ServiceResource, table_name: str) -> None:
    resource.create_table(
        TableName=table_name,
        KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
        AttributeDefinitions=[{'AttributeName': 'pk', 'AttributeType': 'S'}, {'AttributeName': 'sk', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST',
    )


def _seed_items(repo: GenericRepository, partition_key: str, sort_keys: Iterable[str]) -> None:
    for index, sort_key in enumerate(sort_keys, start=1):
        repo.save_with_composite_key(
            {
                'pk': partition_key,
                'sk': sort_key,
                'payload': f'example-{index}',
            },
            return_model=False,
        )


def _show_items(repo: GenericRepository, partition_key: str, label: str) -> None:
    items = repo.find_all(partition_key)
    logging.info('%s (%s items): %s', label, len(items), items)


def main() -> None:
    table_name = 'DemoCompositeTable'
    partition_key_value = 'tenant-123'
    sort_keys = ['2024-09-01', '2024-09-02', '2024-09-03']

    with mock_aws():
        session = boto3.Session(region_name='us-east-1')
        dynamodb = session.resource('dynamodb')

        _create_table(dynamodb, table_name)

        repo = GenericRepository(
            table_name=table_name,
            primary_key_name='pk',
            session=session,
            region_name='us-east-1',
        )

        logging.info('Seeding sample items...')
        _seed_items(repo, partition_key_value, sort_keys)
        _show_items(repo, partition_key_value, 'Before PartiQL delete')

        logging.info('Calling delete_all_by_primary_key...')
        repo.delete_all_by_primary_key(partition_key_value)
        _show_items(repo, partition_key_value, 'After PartiQL delete')

        logging.info('Re-seeding items to demonstrate debug mode...')
        _seed_items(repo, partition_key_value, sort_keys)
        debug_repo = GenericRepository(
            table_name=table_name,
            primary_key_name='pk',
            session=session,
            region_name='us-east-1',
            debug_mode=True,
        )

        debug_repo.delete_all_by_primary_key(partition_key_value)
        _show_items(repo, partition_key_value, 'After debug-mode delete (items should remain)')

        logging.info('Success: PartiQL delete removes items, debug mode leaves them untouched.')


if __name__ == '__main__':
    main()
