#!/usr/bin/env python3
"""Utility script to seed the configuration.PostalInfo table from a JSON dataset."""

import argparse
import json
import os
import sys
from itertools import islice

import django
from django.db import transaction


def chunked(iterable, size):
    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            break
        yield batch


def load_postal_info(json_path: str, chunk_size: int = 1000, limit: int | None = None, truncate: bool = False):
    from configuration.models import PostalInfo

    with open(json_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise ValueError("JSON payload must be a list of postal records")

    if limit is not None:
        data = data[:limit]

    records = []
    for entry in data:
        records.append(
            PostalInfo(
                pincode=int(entry.get("pincode")),
                officename=entry.get("officename"),
                officeType=entry.get("officeType"),
                Deliverystatus=entry.get("Deliverystatus"),
                divisionname=entry.get("divisionname"),
                regionname=entry.get("regionname"),
                circlename=entry.get("circlename"),
                Taluk=entry.get("Taluk"),
                Districtname=entry.get("Districtname"),
                statename=entry.get("statename"),
                Telephone=entry.get("Telephone"),
                relatedSuboffice=entry.get("relatedSuboffice"),
                relatedHeadoffice=entry.get("relatedHeadoffice"),
            )
        )

    with transaction.atomic():
        if truncate:
            PostalInfo.objects.all().delete()

        existing = set(PostalInfo.objects.filter(pincode__in=[r.pincode for r in records]).values_list("pincode", flat=True))
        to_create = [record for record in records if record.pincode not in existing]

        created = 0
        for batch in chunked(to_create, chunk_size):
            PostalInfo.objects.bulk_create(batch, ignore_conflicts=True)
            created += len(batch)

    return created, len(existing)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--settings",
        default="FleetManager.settings",
        help="Django settings module (default: %(default)s)",
    )
    parser.add_argument(
        "--file",
        default=os.path.join("utils", "data", "india_addresses.json"),
        help="Path to JSON file containing postal records",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Number of rows to insert per bulk_create call",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on records to load (useful for testing).",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete existing PostalInfo records before loading",
    )

    args = parser.parse_args(argv)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", args.settings)
    django.setup()

    created, skipped = load_postal_info(
        json_path=args.file,
        chunk_size=args.chunk_size,
        limit=args.limit,
        truncate=args.truncate,
    )

    print(f"PostalInfo load completed. Created: {created}, Skipped (existing): {skipped}")


if __name__ == "__main__":
    main()
