from django.db import models
from jsonfield import JSONField

# Create your models here.


class Customer(models.Model):
    name = models.CharField(max_length=101)
    first_name = models.CharField(max_length=101, null=True, blank=True)
    last_name = models.CharField(max_length=101, null=True, blank=True)
    email = models.CharField(max_length=51, null=True, blank=True)
    dobY = models.CharField(max_length=11, null=True, blank=True)
    dobM = models.CharField(max_length=11, null=True, blank=True)
    dobD = models.CharField(max_length=11, null=True, blank=True)
    ssn = models.CharField(max_length=21, null=True, blank=True)
    driver_license = models.CharField(max_length=51, null=True, blank=True)
    no_of_dependents = models.CharField(max_length=21, null=True, blank=True)
    cell_phone = models.CharField(max_length=21, null=True, blank=True)
    home_phone = models.CharField(max_length=21, null=True, blank=True)
    street = models.CharField(max_length=101, null=True, blank=True)
    city = models.CharField(max_length=101, null=True, blank=True)
    state = models.CharField(max_length=101, null=True, blank=True)
    zip = models.CharField(max_length=101, null=True, blank=True)
    years_there_first = models.CharField(max_length=11, null=True, blank=True)
    own_or_rent = models.CharField(max_length=6, null=True, blank=True)
    employement_status = models.BooleanField(default=False)
    present_employer = models.CharField(max_length=31, null=True, blank=True)
    years_there_second = models.CharField(max_length=11, null=True, blank=True)
    job_title = models.CharField(max_length=101, null=True, blank=True)
    employer_phone = models.CharField(max_length=21, null=True, blank=True)
    monthly_income = models.CharField(max_length=21, null=True, blank=True)
    additional_income = models.CharField(max_length=21, null=True, blank=True)
    source = models.CharField(max_length=21, null=True, blank=True)
    landlord_mortgage_holder = models.CharField(max_length=51, null=True, blank=True)
    monthly_rent_mortgage_payment = models.CharField(max_length=51, null=True, blank=True)
    cif_number = models.CharField(max_length=101, null=True, blank=True)
    nortridge_cif_number = models.CharField(max_length=101, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Application(models.Model):
    applicant = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='mainapp')
    co_applicant = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='coapp', blank=True, null=True)
    co_enabled = models.BooleanField(default=False)
    co_complete = models.BooleanField(default=False)
    co_separate = models.BooleanField(default=False)
    status = models.CharField(max_length=101, null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)
    hello_sign_ref = models.CharField(max_length=101, null=True, blank=True)
    salesperson_email = models.CharField(max_length=51, default='developer@dcg.dev')
    rating = models.IntegerField(default=0)
    message = models.CharField(max_length=300, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
class CreditApplication(models.Model):
    credit_app = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='maincreditapp')
    credit_co_app = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='cocreditapp', blank=True, null=True)
    co_enabled = models.BooleanField(default=False)
    co_complete = models.BooleanField(default=False)
    co_separate = models.BooleanField(default=False)
    status = models.CharField(max_length=101, null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)
    salesperson_email = models.CharField(max_length=51, default='developer@dcg.dev')
    rating = models.IntegerField(default=0)
    message = models.CharField(max_length=300, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Product(models.Model):
    app = models.ForeignKey(Application, on_delete=models.CASCADE, null=True, blank=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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


class Preapproval(models.Model):
    app = models.ForeignKey(Application, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    status = models.IntegerField(default=0)   # 0 : not set, 1: approved, 2: declined, 3: OrderGenerated, 4: Deleted
    message = models.CharField(max_length=300, null=True, blank=True)
    product_type = models.CharField(max_length=51, null=True, blank=True)
    appliance = models.CharField(max_length=51, null=True, blank=True)
    earliest_delivery_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    #
    preapproval_request = models.IntegerField(default=0) # 0: new data, 1: requested, 2: admin denay, 0:amin aprove



class FundingRequest(models.Model):
    app = models.ForeignKey(Application, on_delete=models.CASCADE, null=True, blank=True)
    status = models.IntegerField(default=0)   # 0 : not set, 1: approved, 2: declined
    delivery_date = models.CharField(max_length=21)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class HelloSignResponse(models.Model):
    signature_request_id = models.CharField(max_length=200, null=True, blank=True)
    signature_id = models.CharField(max_length=200, null=True, blank=True)
    signer_email_address = models.CharField(max_length=200, null=True, blank=True)
    signer_name = models.CharField(max_length=101, null=True, blank=True)
    signer_role = models.CharField(max_length=101, null=True, blank=True)
    order = models.CharField(max_length=30, null=True, blank=True)
    status_code = models.CharField(max_length=50, null=True, blank=True)
    signed_at = models.CharField(max_length=50, null=True, blank=True)
    last_viewed_at = models.CharField(max_length=50, null=True, blank=True)
    last_reminded_at = models.CharField(max_length=50, null=True, blank=True)
    has_pin = models.BooleanField(default=False, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NortridgeToken(models.Model):
    token = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class HelloSignLog(models.Model):
    signature_request_id = models.CharField(max_length=200, null=True, blank=True)
    signature_id = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    response = JSONField()
    created_at = models.DateTimeField(auto_now=True, null=True, blank=True)
