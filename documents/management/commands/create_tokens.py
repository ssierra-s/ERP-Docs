from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

class Command(BaseCommand):
    help = "Crear tokens para usuarios. Uso: python manage.py create_tokens [--username <username>] [--all]"

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, help="Nombre de usuario para crear token.")
        parser.add_argument("--all", action="store_true", help="Crear token para todos los usuarios existentes.")

    def handle(self, *args, **options):
        username = options.get("username")
        do_all = options.get("all", False)

        if not username and not do_all:
            raise CommandError("Debes pasar --username o --all")

        if do_all:
            users = User.objects.all()
            for u in users:
                token, created = Token.objects.get_or_create(user=u)
                self.stdout.write(f"{u.username} -> {token.key} {'(created)' if created else '(exists)'}")
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"Usuario {username} no encontrado")

        token, created = Token.objects.get_or_create(user=user)
        self.stdout.write(f"{user.username} -> {token.key} {'(created)' if created else '(exists)'}")
