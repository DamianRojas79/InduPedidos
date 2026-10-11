from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('producto', '0015_pedido_pedido_general')]

    operations = [
        migrations.AddField(
            model_name='lineapedido',
            name='proveedor',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                to='producto.proveedor',
            ),
        ),
    ]
