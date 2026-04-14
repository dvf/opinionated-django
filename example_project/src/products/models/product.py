from typing import ClassVar

from django.db import models

from project.ids import generate_prd_id


class Product(models.Model):
    class Meta:
        verbose_name = "product"
        verbose_name_plural = "products"
        indexes = [
            models.Index(fields=["name"], name="idx_%(class)s_name"),
        ]

    __prefix__: ClassVar[str] = "prd"

    id = models.CharField(
        max_length=64, primary_key=True, default=generate_prd_id, editable=False
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()

    def __str__(self):
        return self.name
