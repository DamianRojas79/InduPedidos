from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('producto', '0010_pedido_lineapedido')]

    operations = [
        migrations.AddField(
            model_name='lineapedido',
            name='posicion',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
