import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0004_userprofile_failed_login_attempts_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name="event",
            index=models.Index(fields=["status", "date"], name="event_status_date_idx"),
        ),
        migrations.AddIndex(
            model_name="registration",
            index=models.Index(fields=["event", "status"], name="reg_event_status_idx"),
        ),
        migrations.AddIndex(
            model_name="registration",
            index=models.Index(fields=["user", "created_at"], name="reg_user_created_idx"),
        ),
        migrations.AddIndex(
            model_name="securityalert",
            index=models.Index(fields=["is_resolved", "created_at"], name="alert_resolved_created_idx"),
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=64)),
                ("target_type", models.CharField(blank=True, max_length=64)),
                ("target_id", models.CharField(blank=True, max_length=64)),
                ("outcome", models.CharField(default="success", max_length=16)),
                ("request_id", models.CharField(blank=True, max_length=64)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ems_audit_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-pk"]},
        ),
    ]
