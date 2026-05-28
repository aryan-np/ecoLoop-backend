from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0002_saveddonationrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="ngooffer",
            name="photo_proof",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="donation_proofs/",
            ),
        ),
    ]
