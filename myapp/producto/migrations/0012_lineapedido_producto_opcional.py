import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('producto', '0011_lineapedido_posicion')]

    operations = [
        migrations.AlterField(
            model_name='lineapedido',
            name='producto',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                to='producto.producto',
            ),
        ),
    ]
