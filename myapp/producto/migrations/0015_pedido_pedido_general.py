from django.db import migrations, models
import django.db.models.deletion


def vincular_pedidos_actuales(apps, schema_editor):
    alias = schema_editor.connection.alias
    PedidoGeneral = apps.get_model('producto', 'PedidoGeneral')
    Pedido = apps.get_model('producto', 'Pedido')
    abierto = PedidoGeneral.objects.using(alias).filter(estado='abierto').first()
    if abierto:
        Pedido.objects.using(alias).filter(pedido_general__isnull=True).update(pedido_general=abierto)
    # Sin un período abierto, los pedidos anteriores se conservan sin asignar
    # y no se mezclan con las cargas de períodos futuros.


class Migration(migrations.Migration):
    dependencies = [('producto', '0014_pedido_general')]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='pedido_general',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='pedidos_clientes', to='producto.pedidogeneral',
            ),
        ),
        migrations.RunPython(vincular_pedidos_actuales, migrations.RunPython.noop),
    ]
