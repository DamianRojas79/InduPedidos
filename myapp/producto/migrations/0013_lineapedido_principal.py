from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('producto', '0012_lineapedido_producto_opcional')]

    operations = [
        migrations.AddField(
            model_name='lineapedido',
            name='principal',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='opciones', to='producto.lineapedido',
            ),
        ),
    ]
