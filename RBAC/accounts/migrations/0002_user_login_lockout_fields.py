from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [
        migrations.AddField(model_name="user", name="failed_login_attempts", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name="user", name="locked_until", field=models.DateTimeField(blank=True, null=True)),
    ]
