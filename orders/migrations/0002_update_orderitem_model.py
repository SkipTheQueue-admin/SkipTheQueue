# Generated manually to handle model updates

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        # Add database indexes for better performance - only for fields that definitely exist
        migrations.AddIndex(
            model_name='userprofile',
            index=models.Index(fields=['phone_number'], name='orders_user_phone_nu_12345_idx'),
        ),
        migrations.AddIndex(
            model_name='college',
            index=models.Index(fields=['name'], name='orders_college_name_abc12_idx'),
        ),
        migrations.AddIndex(
            model_name='college',
            index=models.Index(fields=['slug'], name='orders_college_slug_def34_idx'),
        ),
        migrations.AddIndex(
            model_name='college',
            index=models.Index(fields=['is_active'], name='orders_college_is_act_ghi56_idx'),
        ),
        migrations.AddIndex(
            model_name='menuitem',
            index=models.Index(fields=['name'], name='orders_menuitem_name_mno90_idx'),
        ),
        migrations.AddIndex(
            model_name='menuitem',
            index=models.Index(fields=['price'], name='orders_menuitem_price_pqr12_idx'),
        ),
        migrations.AddIndex(
            model_name='menuitem',
            index=models.Index(fields=['is_available'], name='orders_menuitem_is_ava_stu34_idx'),
        ),
        migrations.AddIndex(
            model_name='menuitem',
            index=models.Index(fields=['college'], name='orders_menuitem_colleg_vwx56_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user'], name='orders_order_user_id_jkl56_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user_name'], name='orders_order_user_nam_mno78_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user_phone'], name='orders_order_user_pho_pqr90_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['college'], name='orders_order_college_id_stu12_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status'], name='orders_order_status_vwx34_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['created_at'], name='orders_order_created_a_yz56_idx'),
        ),
        migrations.AddIndex(
            model_name='orderitem',
            index=models.Index(fields=['order'], name='orders_orderitem_order_stu90_idx'),
        ),
    ]
