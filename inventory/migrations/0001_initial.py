from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import decimal
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(name="Category", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("name", models.CharField(max_length=120, unique=True)), ("description", models.TextField(blank=True)), ("is_active", models.BooleanField(default=True)),
        ], options={"ordering":["name"]}),
        migrations.CreateModel(name="Supplier", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("name", models.CharField(max_length=180)), ("contact_person", models.CharField(blank=True,max_length=150)), ("phone", models.CharField(blank=True,max_length=50)), ("email", models.EmailField(blank=True,max_length=254)), ("address", models.TextField(blank=True)), ("kra_pin", models.CharField(blank=True,max_length=50)), ("notes", models.TextField(blank=True)), ("is_active", models.BooleanField(default=True)),
        ], options={"ordering":["name"]}),
        migrations.CreateModel(name="Item", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("sku", models.CharField(max_length=40, unique=True)), ("name", models.CharField(max_length=180)), ("description", models.TextField(blank=True)), ("unit", models.CharField(choices=[("piece","Piece"),("pack","Pack"),("box","Box"),("ream","Ream"),("set","Set"),("bottle","Bottle"),("kg","Kilogram"),("litre","Litre"),("other","Other")],default="piece",max_length=20)), ("location", models.CharField(blank=True,help_text="Store room, lab, office, etc.",max_length=120)), ("reorder_level", models.DecimalField(decimal_places=2,default=0,max_digits=12,validators=[django.core.validators.MinValueValidator(0)])), ("purchase_price", models.DecimalField(decimal_places=2,default=0,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])), ("current_stock", models.DecimalField(decimal_places=2,default=0,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])), ("is_active", models.BooleanField(default=True)),
            ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="items",to="inventory.category")),
        ], options={"ordering":["name"],"indexes":[models.Index(fields=["name"],name="inventory_i_name_9f7d2c_idx"),models.Index(fields=["sku"],name="inventory_i_sku_9c5d4f_idx"),models.Index(fields=["category"],name="inventory_i_categor_4b1d2a_idx")]}),
        migrations.CreateModel(name="Asset", fields=[
            ("id", models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")), ("created_at",models.DateTimeField(auto_now_add=True)), ("updated_at",models.DateTimeField(auto_now=True)),
            ("asset_tag",models.CharField(max_length=50,unique=True)), ("name",models.CharField(max_length=180)), ("serial_number",models.CharField(blank=True,max_length=120)), ("location",models.CharField(blank=True,max_length=150)), ("assigned_to",models.CharField(blank=True,max_length=150)), ("acquisition_date",models.DateField(blank=True,null=True)), ("acquisition_cost",models.DecimalField(decimal_places=2,default=0,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])), ("status",models.CharField(choices=[("ACTIVE","Active"),("MAINTENANCE","Under Maintenance"),("DISPOSED","Disposed"),("LOST","Lost")],default="ACTIVE",max_length=20)), ("notes",models.TextField(blank=True)),
            ("category",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="assets",to="inventory.category")),
        ],options={"ordering":["name"]}),
        migrations.CreateModel(name="Purchase", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")), ("created_at",models.DateTimeField(auto_now_add=True)), ("updated_at",models.DateTimeField(auto_now=True)),
            ("number",models.CharField(max_length=40,unique=True)), ("purchase_date",models.DateField(default=django.utils.timezone.localdate)), ("status",models.CharField(choices=[("DRAFT","Draft"),("RECEIVED","Received"),("CANCELLED","Cancelled")],default="DRAFT",max_length=20)), ("invoice_number",models.CharField(blank=True,max_length=100)), ("notes",models.TextField(blank=True)), ("received_at",models.DateTimeField(blank=True,null=True)),
            ("supplier",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="purchases",to="inventory.supplier")), ("received_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="received_purchases",to=settings.AUTH_USER_MODEL)),
        ],options={"ordering":["-purchase_date","-id"]}),
        migrations.CreateModel(name="PurchaseLine", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")), ("quantity",models.DecimalField(decimal_places=2,max_digits=14,validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])), ("unit_cost",models.DecimalField(decimal_places=2,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])),
            ("item",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="purchase_lines",to="inventory.item")), ("purchase",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="lines",to="inventory.purchase")),
        ]),
        migrations.CreateModel(name="StockMovement", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")), ("created_at",models.DateTimeField(auto_now_add=True)), ("updated_at",models.DateTimeField(auto_now=True)),
            ("movement_type",models.CharField(choices=[("IN","Stock In"),("OUT","Stock Out"),("ADJUSTMENT","Adjustment")],max_length=20)), ("quantity",models.DecimalField(decimal_places=2,max_digits=14,validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])), ("unit_cost",models.DecimalField(decimal_places=2,default=0,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])), ("reference",models.CharField(blank=True,max_length=120)), ("reason",models.CharField(blank=True,max_length=255)), ("balance_after",models.DecimalField(decimal_places=2,default=0,max_digits=14)), ("moved_at",models.DateTimeField()),
            ("created_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL)), ("item",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="movements",to="inventory.item")),
        ],options={"ordering":["-moved_at","-id"],"indexes":[models.Index(fields=["item","-moved_at"],name="inventory_s_item_id_1b3a52_idx"),models.Index(fields=["movement_type","-moved_at"],name="inventory_s_movement_7b5a3e_idx")]}),
        migrations.AddConstraint(model_name="supplier",constraint=models.UniqueConstraint(fields=("name","phone"),name="unique_supplier_name_phone")),
        migrations.AddConstraint(model_name="purchaseline",constraint=models.UniqueConstraint(fields=("purchase","item"),name="unique_purchase_item")),
    ]
