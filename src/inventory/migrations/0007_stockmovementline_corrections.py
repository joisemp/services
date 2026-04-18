from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_productimage_variantimage'),
        ('core', '0018_rename_warehouse_user_warehouses'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockmovementline',
            name='correction_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='stockmovementline',
            name='correction_type',
            field=models.CharField(choices=[('ORIGINAL', 'Original'), ('CORRECTION', 'Correction')], default='ORIGINAL', max_length=16),
        ),
        migrations.AddField(
            model_name='stockmovementline',
            name='corrected_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='stockmovementline',
            name='corrected_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inventory_corrections_made', to='core.user'),
        ),
        migrations.AddField(
            model_name='stockmovementline',
            name='corrects_movement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='corrections', to='inventory.stockmovementline'),
        ),
        migrations.AddIndex(
            model_name='stockmovementline',
            index=models.Index(fields=['correction_type', '-created_at'], name='inventory_s_correct_9f1c14_idx'),
        ),
        migrations.AddIndex(
            model_name='stockmovementline',
            index=models.Index(fields=['corrects_movement'], name='inventory_s_correct_797573_idx'),
        ),
    ]
