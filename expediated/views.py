from django.shortcuts import render

import datetime

import json
import requests
from requests.auth import HTTPBasicAuth

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST

from .models import Customer, Product

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def CustomerView(request):

    data = request.data

    if data is None:
        return Response({
			'ok': False,
			'error': 'Invalid Request'
		}, HTTP_400_BAD_REQUEST)

    products = data["products"]

    if products is None or len(products) == 0:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)

    prod_count = len(products)

    contact = data["contact"]

    order_type = contact["order_type"]

    co_enabled = contact["co_enabled"]
    co_complete = contact["co_complete"]
    co_separate = contact["co_separate"]
    
    customer = Customer(
        name = contact["name"],
        street = contact["street"],
        city = contact["city"],
        state = contact["state"],
        zip = contact["zip"],
        phone = contact["phone"],
        email = contact["email"],

        co_name = contact["co_name"],
        same_address = contact["same_address"],
        co_street = contact["co_street"],
        co_city = contact["co_city"],
        co_state = contact["co_state"],
        co_zip = contact["co_zip"],
        co_phone = contact["co_phone"],
        co_email = contact["co_email"],

        co_enabled = co_enabled,
        co_complete = co_complete,
        co_separate = co_separate,
    )

    customer.save()

    scenario = 0
    template_id = ""

    if order_type == 1:
        if co_enabled == False:
            scenario = 4
            if prod_count == 1:
                template_id = "71deb1e2dad0d0a0f7dda94187274a70b0c42859"
            else:
                template_id = "59f4b4f6beecdc1adf69b3f514254537e7df03e2"
        else:
            if co_complete == False:
                scenario = 2
                if prod_count == 1:
                    template_id = "c50646d726f8892cee46ec2b2695b68efe2a6d70"
                else:
                    template_id = "2eed73d46c691102b93a6592486a05af25715113"
            else:
                if co_separate == False:
                    scenario = 1
                    if prod_count == 1:
                        template_id = "ad4ccc1e4c23d1e92811a1dc1a0667151b0f247d"
                    else:
                        template_id = "d085baae4ac46ffd7359782cedf0b46bc03204a8"
                else:
                    scenario = 3
                    if prod_count == 1:
                        template_id = "79597c3abf1aed2f90d778807fdd714041ba3714"
                    else:
                        template_id = "cba1acd7f1724f792decc49e49b32d445cb29a5b"
    elif order_type == 2:
        if co_enabled == False:
            scenario = 4
            if prod_count == 1:
                template_id = "1a3254cae49432e7f1eedb93c2cf00009dd14422"
            else:
                template_id = "b1069d5dac0001f2b94cbf5c20c39b2274f114ea"
        else:
            if co_complete == False:
                scenario = 2
                if prod_count == 1:
                    template_id = "a0b37dfc5d3909a0d42f9c7a11553bd9adf5b672"
                else:
                    template_id = "98642bf455ad62d7984ef8899a4389e8405d1f66"
            else:
                if co_separate == False:
                    scenario = 1
                    if prod_count == 1:
                        template_id = "df05890933839a3d9879b4167b38ae907d135c57"
                    else:
                        template_id = "5a7bd4c90d262d667205f5151085014a9621210d"
                else:
                    scenario = 3
                    if prod_count == 1:
                        template_id = "9529f3555e6ac8224e296f7a99c01267cbcb870e"
                    else:
                        template_id = "cfe9d26bdf7d1613530b9a23508d950189d1cb42"
    else:
        return Response()
       
    custom_fields = [
        { "name": "buyer_name", "value": contact["name"] },
        { "name": "buyer_address", "value": contact["street"] },
        { "name": "buyer_city", "value": contact["city"] },
        { "name": "buyer_state", "value": contact["state"] },
        { "name": "buyer_zip", "value": contact["zip"] },
        { "name": "buyer_phone", "value": contact["phone"] },
        { "name": "buyer_full_address", "value": contact["street"] + ", " + contact["city"] + ", " + contact["state"] + ", " + contact["zip"] }
    ]

    if order_type == 1:
        custom_fields.append({ "name": "buyer_email", "value": contact["email"] })

    today = datetime.date.today()
    third_date = today + datetime.timedelta(days=3)

    if contact["state"] == "Maine":
        third_date = today + datetime.timedelta(days=10)

    custom_fields.append({ "name": "third_date", "value": third_date.strftime("%m/%d/%Y") })

    if scenario != 4:
        co_name = contact["co_name"]
        co_street = contact["co_street"]
        co_city = contact["co_city"]
        co_state = contact["co_state"]
        co_zip = contact["co_zip"]
        co_phone = contact["co_phone"]
        co_email = contact["co_email"]

        if order_type == 1:
            custom_fields.append({ "name": "co_name", "value": co_name })
            custom_fields.append({ "name": "co_address", "value": co_street })
            custom_fields.append({ "name": "co_city", "value": co_city })
            custom_fields.append({ "name": "co_state", "value": co_state })
            custom_fields.append({ "name": "co_zip", "value": co_zip })
            custom_fields.append({ "name": "co_phone", "value": co_phone })
            custom_fields.append({ "name": "co_email", "value": co_email })

        if co_state == "Maine":
            third_date = today + datetime.timedelta(days=10)
        else:
            third_date = today + datetime.timedelta(days=3)

        custom_fields.append({ "name": "co_third_date", "value": third_date.strftime("%m/%d/%Y") })

    i = 0
    
    for product in data["products"]:
        product_type = product["product_type"]
        product = Product(
            customer = customer,
            product_type = product_type,
            price = float(product["price"]),
            total_discount = float(product["total_discount"]),
            coupon = float(product["coupon"]),
            add_discount = float(product["add_discount"]),
            tax = float(product["tax"]),
            cash_credit = float(product["cash_credit"]),
            check = float(product["check"]),
            finance_period = product["finance_period"],
            makemodel = product["makemodel"]
        )

        product.save()

        if i == 0:
            custom_fields.append({ "name": "makemodel", "value": product.makemodel })
            custom_fields.append({ "name": "s_price", "value": "${:.2f}".format(product.net_price()) })
            custom_fields.append({ "name": "s_tax", "value": "${:.2f}".format(product.tax) })
            custom_fields.append({ "name": "s_balance", "value": "${:.2f}".format(product.balance()) })
            custom_fields.append({ "name": "s_down", "value": "${:.2f}".format(product.down_payment()) })
            custom_fields.append({ "name": "s_cc", "value": "${:.2f} / ${:.2f}".format(product.cash_credit, product.check) })
            custom_fields.append({ "name": "s_unpaid", "value": "${:.2f}".format(product.unpaid_balance()) })
            custom_fields.append({ "name": "s_monthly", "value": "${:.2f}".format(product.monthly_minimum()) })

            if product.product_type == "FOOD":
                custom_fields.append({ "name": "special", "value": '0% interest food order' })

            if product.cash_credit != 0 or product.check != 0:
                custom_fields.append({ "name": "check_cc", "value": True })
            else:
                custom_fields.append({ "name": "check_ach", "value": True })

            # if order_type == 1:
            #     custom_fields.append({ "name": "s_neworder", "value": True })
            # elif order_type == 2:
            #     custom_fields.append({ "name": "s_reorder", "value": True })
        if i == 1:
            custom_fields.append({ "name": "makemodel_2", "value": product.makemodel })
            custom_fields.append({ "name": "s_price_2", "value": "${:.2f}".format(product.net_price()) })
            custom_fields.append({ "name": "s_tax_2", "value": "${:.2f}".format(product.tax) })
            custom_fields.append({ "name": "s_balance_2", "value": "${:.2f}".format(product.balance()) })
            custom_fields.append({ "name": "s_down_2", "value": "${:.2f}".format(product.down_payment()) })
            custom_fields.append({ "name": "s_cc_2", "value": "${:.2f} / ${:.2f}".format(product.cash_credit, product.check) })
            custom_fields.append({ "name": "s_unpaid_2", "value": "${:.2f}".format(product.unpaid_balance()) })
            custom_fields.append({ "name": "s_monthly_2", "value": "${:.2f}".format(product.monthly_minimum()) })

            if product.product_type == "FOOD":
                custom_fields.append({ "name": "special_2", "value": '0% interest food order' })

            if product.cash_credit != 0 or product.check != 0:
                custom_fields.append({ "name": "check_cc_2", "value": True })
            else:
                custom_fields.append({ "name": "check_ach_2", "value": True })

        i = i + 1


    url = 'https://api.hellosign.com/v3/signature_request/send_with_template'

    message = "Dear " + contact["name"]
    if scenario == 1 or scenario == 2:
        message = message + " and " + contact["co_name"] + "\n"
    message += "\n\n"
    message += "Thank you for your interest in American Frozen Foods!\n\n"
    message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
    message += "Thank you for the opportunity to be of service!"

    payload = {
        # "test_mode": 1,
        "title": "American Frozen Foods Documentation",
        "subject": "American Frozen Foods Documentation",
        "message": message,
        "template_id": template_id,
        "signers[buyer][name]": contact["name"],
        "signers[buyer][email_address]": contact["email"],
        "custom_fields": json.dumps(custom_fields),
        "ccs[cc1][email_address]": "Billyrapp@yahoo.com",
        "ccs[cc2][email_address]": "susan.treglia@yahoo.com",
        "ccs[cc3][email_address]": "americanfoods5@gmail.com"
    }


    if scenario == 1 or scenario == 2:
        payload["signers[cobuyer][name]"] = "Co-Applicant"
        payload["signers[cobuyer][email_address]"] = contact["co_email"]

    r = requests.post(url, data=payload, auth=HTTPBasicAuth(settings.HELLOSIGN_CLIENT_ID, ''))

    print (r.text)

    return Response({
        'ok': True
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SendPrequalifyView(request):
    data = request.data

    if data is None:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)

    emails = [
        'vlad@dcg.dev',
        'matt@traviscapitalpartners.com',
        'ryan@dcg.dev',
        'kat@dcg.dev'
    ]
    ctxt = data

    send_email('Prequalify', 'prequalify', ctxt, emails, '')

    return Response({
        'ok': True
    })


def send_email(subject, template_prefix, template_ctxt, emails, attach_path):
    if len(emails) == 0:
        return

    txt_file = '%s.txt' % template_prefix
    html_file = '%s.html' % template_prefix

    from_email = settings.DEFAULT_EMAIL_FROM
    bcc_email = settings.DEFAULT_EMAIL_BCC
    text_content = render_to_string(txt_file, template_ctxt)
    html_content = render_to_string(html_file, template_ctxt)
    msg = EmailMultiAlternatives(subject, text_content, from_email, emails, bcc=[bcc_email])
    msg.attach_alternative(html_content, 'text/html')
    if attach_path != '':
        msg.attach_file(attach_path)
    msg.send()