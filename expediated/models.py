from django.db import models

# Create your models here.

class Customer(models.Model):
    name = models.CharField(max_length=101)
    street = models.CharField(max_length=101)
    city = models.CharField(max_length=101)
    state = models.CharField(max_length=101)
    zip  = models.CharField(max_length=101, blank=True, null=True)
    phone = models.CharField(max_length=18)
    email = models.CharField(max_length=101)

    co_name = models.CharField(max_length=101, blank=True, null=True)
    same_address = models.BooleanField(default=False)
    co_street = models.CharField(max_length=101, blank=True, null=True)
    co_city = models.CharField(max_length=101, blank=True, null=True)
    co_state = models.CharField(max_length=101, blank=True, null=True)
    co_zip = models.CharField(max_length=101, blank=True, null=True)
    co_phone = models.CharField(max_length=18, blank=True, null=True)
    co_email = models.CharField(max_length=101, blank=True, null=True)

    co_enabled = models.BooleanField(default=False)
    co_complete = models.BooleanField(default=False)
    co_separate = models.BooleanField(default=False)

class Product(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, blank=True, null=True)

    product_type = models.CharField(max_length=51)
    
    price = models.FloatField(default=0)
    total_discount = models.FloatField(default=0)
    coupon = models.FloatField(default=0)
    add_discount = models.FloatField(default=0)

    tax = models.FloatField(default=0)

    cash_credit = models.FloatField(default=0)
    check = models.FloatField(default=0)
    finance_period = models.IntegerField(default=0)

    makemodel = models.CharField(max_length=1001, blank=True, null=True)

    def net_price(self):
        return self.price * (100 - self.total_discount) / 100 - self.add_discount - self.coupon

    def balance(self):
        return self.net_price() + self.tax

    def down_payment(self):
        return self.cash_credit + self.check

    def unpaid_balance(self):
        return self.balance() - self.down_payment()

    def monthly_minimum(self):
        if self.product_type == "FOOD":
            if self.finance_period == 0:
                return 0
            return self.unpaid_balance() / self.finance_period
        elif self.product_type == "FSP" or self.product_type == "APP":
            multiple = 0
            if self.finance_period == 36:
                multiple = 0.035
            elif self.finance_period == 48:
                multiple = 0.03
            return self.unpaid_balance() * multiple
        return 0