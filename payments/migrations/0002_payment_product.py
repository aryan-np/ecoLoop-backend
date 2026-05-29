import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0005_product_sold_to"),
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="payments",
                to="products.product",
            ),
        ),
    ]
