import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connection

from users.models import User


class Command(BaseCommand):
    help = "Seed users database with mock data."

    def handle(self, *args, **options):
        confirmation = input("This will delete all users. Continue? (Y/n): ")

        if confirmation.lower() not in ("y", ""):
            print("Seed cancelled.")
            return

        file_path = (
            Path(__file__).resolve().parents[2] / "management" / "seeds" / "users.json"
        )

        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        users = [User(**user) for user in data]

        User.objects.all().delete()

        sequence_sql = connection.ops.sequence_reset_sql(
            no_style(),
            [User],
        )


        with connection.cursor() as cursor:
            for sql in sequence_sql:
                cursor.execute(sql)

        User.objects.bulk_create(users)
        print("Successfull inserted: ", users)
