from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Producto',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('desc', models.TextField()),
                ('precio', models.FloatField()),
                ('precio_costo', models.FloatField()),
                ('id_proveedor', models.IntegerField()),
            ],
            options={
                'db_table': 'producto',
            },
        ),
    ]
