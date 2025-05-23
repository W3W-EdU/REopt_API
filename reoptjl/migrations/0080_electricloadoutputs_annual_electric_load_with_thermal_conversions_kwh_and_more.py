# Generated by Django 4.0.7 on 2025-02-13 15:16

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reoptjl', '0079_alter_siteinputs_include_grid_renewable_fraction_in_re_constraints_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='electricloadoutputs',
            name='annual_electric_load_with_thermal_conversions_kwh',
            field=models.FloatField(blank=True, help_text='Total end-use electrical load, including electrified heating and cooling end-use load.', null=True),
        ),
        migrations.AlterField(
            model_name='electricloadoutputs',
            name='annual_calculated_kwh',
            field=models.FloatField(blank=True, help_text='Annual energy consumption calculated by summing up load_series_kw. Does not include electric load for any new heating or cooling techs.', null=True),
        ),
        migrations.AlterField(
            model_name='electricloadoutputs',
            name='load_series_kw',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(blank=True, null=True), default=list, help_text='Annual time series of BAU electric load. Does not include electric load for any new heating or cooling techs.', size=None),
        ),
    ]
