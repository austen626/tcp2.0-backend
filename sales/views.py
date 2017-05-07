import json

import holidays
import requests
import datetime
from requests.auth import HTTPBasicAuth
from django.conf import settings

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from accounts.models import User, Company
from .hellosignapi import get_signature_status, getpdfdoc, log_hellosign_data, send_reminder, delete_signature_request
from .permissions import IsHellosignCallback
from .models import Customer, Product, Application, Preapproval, FundingRequest, HelloSignResponse, CreditApplication
from .nortridge import getToken, revokeToken, createContact, searchContacts, getContact, getPaymentDue, getPaymentinfo
from rest_framework.parsers import MultiPartParser
from .nortridge import getToken, revokeToken, createContact, searchContacts, getContact, getContactloan, \
    getPaymentHistory
from .nortridge import getToken, revokeToken, createContact, searchContacts, getContact
from rest_framework.parsers import MultiPartParser
from .nortridge import getToken, revokeToken, createContact, searchContacts, getContact, getContactloan, \
    getPaymentHistory,searchContactsByPhoneEmail
from .utils import xstr
from .hellosignapi import get_all_signature_status
from .hellosignapi import sendEmailOkay, delete_signature_request
from django.forms.models import model_to_dict
from django.core.mail import EmailMultiAlternatives
import hashlib


# Public Holidays Check
def check_public_holiday(selected_date):
    final_date = selected_date
    us_holidays = holidays.UnitedStates()
    # Sunday Check
    if final_date.weekday() == 6:
        print("This Date %s Comes on Sunday, Selecting next day" % final_date)
        final_date = final_date + datetime.timedelta(days=1)
        return check_public_holiday(final_date)
    else:
        day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        print("This Date %s Comes on" % final_date, day_name[final_date.weekday()])

    # Public Holiday Check
    if final_date in us_holidays:
        print("This Date %s Comes on Public Holiday %s, Selecting next day" % (final_date, us_holidays.get(final_date)))
        final_date = final_date + datetime.timedelta(days=1)
        return check_public_holiday(final_date)
    else:
        print("Final Selected Date is", final_date)
        return final_date
#send Emails
def send_invite_email(email, user_type, dealer_company, user_name = 'User'):
    if email is None:
        return False
    emails = [email]
    subject = "TCP Credit application"
    message = "Dear "+user_type+",\n\n"
    if user_type =='User':
        message += "Your credit application for the "+ dealer_company+" has been submitted successfully.\n\n"
    elif user_type== 'Admin':
        message += "The credit application of "+user_name+" has been submitted successfully for the "+dealer_company+"."+"\n\n"
    message += "\n\nThanks!\nTravis Capital Partners"

    from_email = settings.DEFAULT_EMAIL_FROM
    html_message = ""
    msg = EmailMultiAlternatives(subject, message, from_email, emails)
    if html_message:
        msg.attach_alternative(html_message, 'text/html')
    msg.send()
    return True
def send_link_email(email, doc_id, phone, dealer_company, digest, sales_email):
    if email is None:
        return False
    token = hashlib.sha512(digest.encode())
    token = token.hexdigest()
    emails = [email]
    subject = "TCP Credit application"
    message = "Dear User,\n\n"
    message += "Credit application is on "+ dealer_company+"\n\n  Please fill details in the link-"
    message += settings.INVITE_CREDIT_APP_URL + str(doc_id) + "&phone=" + phone + "&email=" + email+ "&salesperson_email=" + sales_email+ "&token=" + token
    message += "\n\nThanks!\nTravis Capital Partners"

    from_email = settings.DEFAULT_EMAIL_FROM
    html_message = ""
    msg = EmailMultiAlternatives(subject, message, from_email, emails)
    if html_message:
        msg.attach_alternative(html_message, 'text/html')
    msg.send()
    return True

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SendSignatureView(request):
    data = request.data
    contact = data["contact"]
    products = data["products"]
    main_app = contact["main_app"]
    co_app = contact["co_app"]
    co_enabled = contact["co_enabled"]
    co_complete = contact["co_complete"]
    co_separate = contact["co_separate"]
    existing_id_cif = contact["existing_customer_id"]
    preapproval_id = contact["preapproval_id"]
    if existing_id_cif == 0:
        main_customer = Customer(
            name=main_app["name"],
            email=main_app["email"],
            dobY=main_app["dobY"],
            dobM=main_app["dobM"],
            dobD=main_app["dobD"],
            ssn=main_app["ssn"],
            driver_license=main_app["dl"],
            no_of_dependents=main_app["nod"],
            cell_phone=main_app["cell_phone"],
            home_phone=main_app["home_phone"],
            street=main_app["street"],
            city=main_app["city"],
            state=main_app["state"],
            zip=main_app["zip"],
            years_there_first=main_app["yt1"],
            own_or_rent=main_app["own_or_rent"],
            present_employer=main_app["present_employer"],
            years_there_second=main_app["yt2"],
            job_title=main_app["job_title"],
            employer_phone=main_app["employer_phone"],
            monthly_income=main_app["monthly_income"],
            additional_income=main_app["additional_income"],
            source=main_app["source"],
            landlord_mortgage_holder=main_app["landlord_holder"],
            monthly_rent_mortgage_payment=main_app["monthly_rent_payment"]
        )
        main_customer.save()
        #dealer company info
        user = User.objects.get(email=request.user.email)
        company = Company.objects.get(id=user.dealer_company_id)
        print(company.contact_type,company.contact_code)

        main_customer.cif_number = createContact(main_customer)
        main_customer.save()
        application = Application(applicant=main_customer)
        application.salesperson_email = request.user.email

        today = datetime.date.today()
        third_date = check_public_holiday(today + datetime.timedelta(days=3))
        if main_customer.state == "ME":
            third_date = check_public_holiday(today + datetime.timedelta(days=12))

        custom_fields = [
            {"name": "buyer_name", "value": main_customer.name},
            {"name": "buyer_address", "value": main_customer.street},
            {"name": "buyer_city", "value": main_customer.city},
            {"name": "buyer_state", "value": main_customer.state},
            {"name": "buyer_zip", "value": main_customer.zip},
            {"name": "buyer_phone", "value": main_customer.home_phone},
            {"name": "third_date", "value": third_date.strftime("%m/%d/%Y")},
            {"name": "buyer_full_address",
             "value": main_customer.street + ", " + main_customer.city + ", " + main_customer.state + ", " + main_customer.zip}
        ]

        order_type = contact["order_type"]
        if order_type == 1:
            custom_fields.append({"name": "buyer_email", "value": main_customer.email})
            # custom_fields.append({"name": "dobM", "value": main_customer.dobM})
            # custom_fields.append({"name": "dobD", "value": main_customer.dobD})
            # custom_fields.append({"name": "dobY", "value": main_customer.dobY})
            # custom_fields.append({"name": "yt1", "value": main_customer.years_there_first})
            # custom_fields.append({"name": "yt2", "value": main_customer.years_there_second})
            # custom_fields.append({"name": "cell_phone", "value": main_customer.cell_phone})
            # custom_fields.append({"name": "ssn", "value": main_customer.ssn})
            # custom_fields.append({"name": "present_employer", "value": main_customer.present_employer})
            # custom_fields.append({"name": "position", "value": main_customer.job_title})
            # custom_fields.append({"name": "monthly_income", "value": main_customer.monthly_income})
            # custom_fields.append({"name": "driver_license", "value": main_customer.driver_license})
            # custom_fields.append({"name": "nod", "value": main_customer.no_of_dependents})
            # custom_fields.append({"name": "other_income", "value": main_customer.additional_income})
            # custom_fields.append({"name": "source", "value": main_customer.source})
            # custom_fields.append({"name": "landlord_holder", "value": main_customer.landlord_mortgage_holder})
            # custom_fields.append({"name": "monthly_rent", "value": main_customer.monthly_rent_mortgage_payment})

        co_enabled = contact["co_enabled"]
        if co_enabled == True:
            co_customer = Customer(
                name=co_app["name"],
                email=co_app["email"],
                dobY=co_app["dobY"],
                dobM=co_app["dobM"],
                dobD=co_app["dobD"],
                ssn=co_app["ssn"],
                driver_license=co_app["dl"],
                no_of_dependents=co_app["nod"],
                cell_phone=co_app["cell_phone"],
                home_phone=co_app["home_phone"],
                street=co_app["street"],
                city=co_app["city"],
                state=co_app["state"],
                zip=co_app["zip"],
                years_there_first=co_app["yt1"],
                own_or_rent=co_app["own_or_rent"],
                present_employer=co_app["present_employer"],
                years_there_second=co_app["yt2"],
                job_title=co_app["job_title"],
                employer_phone=co_app["employer_phone"],
                monthly_income=co_app["monthly_income"],
                additional_income=co_app["additional_income"],
                source=co_app["source"],
                landlord_mortgage_holder=co_app["landlord_holder"],
                monthly_rent_mortgage_payment=co_app["monthly_rent_payment"]
            )
            co_customer.save()
            co_customer.cif_number = createContact(co_customer)
            co_customer.save()

            application.co_applicant = co_customer
            application.co_enabled = True

            third_date = check_public_holiday(today + datetime.timedelta(days=3))
            if co_customer.state == "ME":
                third_date = check_public_holiday(today + datetime.timedelta(days=12))
            custom_fields.append({"name": "co_third_date", "value": third_date.strftime("%m/%d/%Y")})

            if order_type == 1:
                custom_fields.append({"name": "co_name", "value": co_customer.name})
                custom_fields.append({"name": "co_email", "value": co_customer.email})
                custom_fields.append({"name": "co_address", "value": co_customer.street})
                custom_fields.append({"name": "co_city", "value": co_customer.city})
                custom_fields.append({"name": "co_state", "value": co_customer.state})
                custom_fields.append({"name": "co_zip", "value": co_customer.zip})
                custom_fields.append({"name": "co_phone", "value": co_customer.home_phone})
            # custom_fields.append({"name": "co_home_phone", "value": co_customer.home_phone})
            #  custom_fields.append({"name": "co_dobM", "value": co_customer.dobM})
            #  custom_fields.append({"name": "co_dobD", "value": co_customer.dobD})
            #  custom_fields.append({"name": "co_dobY", "value": co_customer.dobY})
            #  custom_fields.append({"name": "co_yt1", "value": co_customer.years_there_first})
            #  custom_fields.append({"name": "co_yt2", "value": co_customer.years_there_second})
            #  custom_fields.append({"name": "co_cell_phone", "value": co_customer.cell_phone})
            #  custom_fields.append({"name": "co_ssn", "value": co_customer.ssn})
            #  custom_fields.append({"name": "co_present_employer", "value": co_customer.present_employer})
            #  custom_fields.append({"name": "co_position", "value": co_customer.job_title})
            #  custom_fields.append({"name": "co_monthly_income", "value": co_customer.monthly_income})
            #  custom_fields.append({"name": "co_driver_license", "value": co_customer.driver_license})
            #  custom_fields.append({"name": "co_nod", "value": co_customer.no_of_dependents})
            #  custom_fields.append({"name": "co_other_income", "value": co_customer.additional_income})
            #  custom_fields.append({"name": "co_source", "value": co_customer.source})
            #  custom_fields.append({"name": "co_landlord_holder", "value": co_customer.landlord_mortgage_holder})
            #  custom_fields.append({"name": "co_monthly_rent", "value": co_customer.monthly_rent_mortgage_payment})

        application.status = "waiting"
        application.created_at = datetime.date.today()
        application.save()

        products_count = len(products)
        template_id = ""
        scenario = 0
        if order_type == 1:
            if co_enabled == False:
                if products_count == 1:
                    template_id = "71deb1e2dad0d0a0f7dda94187274a70b0c42859"
                else:
                    template_id = "59f4b4f6beecdc1adf69b3f514254537e7df03e2"
            else:
                if co_complete == False:
                    if products_count == 1:
                        template_id = "c50646d726f8892cee46ec2b2695b68efe2a6d70"
                    else:
                        template_id = "2eed73d46c691102b93a6592486a05af25715113"
                else:
                    if co_separate == False:
                        if products_count == 1:
                            template_id = "ad4ccc1e4c23d1e92811a1dc1a0667151b0f247d"
                        else:
                            template_id = "d085baae4ac46ffd7359782cedf0b46bc03204a8"
                    else:
                        if products_count == 1:
                            template_id = "79597c3abf1aed2f90d778807fdd714041ba3714"
                        else:
                            template_id = "cba1acd7f1724f792decc49e49b32d445cb29a5b"
        elif order_type == 2:
            if co_enabled == False:
                if products_count == 1:
                    template_id = "1a3254cae49432e7f1eedb93c2cf00009dd14422"
                else:
                    template_id = "b1069d5dac0001f2b94cbf5c20c39b2274f114ea"
            else:
                if co_complete == False:
                    if products_count == 1:
                        template_id = "a0b37dfc5d3909a0d42f9c7a11553bd9adf5b672"
                    else:
                        template_id = "98642bf455ad62d7984ef8899a4389e8405d1f66"
                else:
                    if co_separate == False:
                        if products_count == 1:
                            template_id = "df05890933839a3d9879b4167b38ae907d135c57"
                        else:
                            template_id = "5a7bd4c90d262d667205f5151085014a9621210d"
                    else:
                        if products_count == 1:
                            template_id = "9529f3555e6ac8224e296f7a99c01267cbcb870e"
                        else:
                            template_id = "cfe9d26bdf7d1613530b9a23508d950189d1cb42"

        i = 0
        for product in products:
            product_type = product["product_type"]
            product = Product(
                app=application,
                product_type=product_type,
                price=float(product["price"]),
                total_discount=float(product["total_discount"]),
                coupon=float(product["coupon"]),
                add_discount=float(product["add_discount"]),
                tax=float(product["tax"]),
                cash_credit=float(product["cash_credit"]),
                check=float(product["check"]),
                finance_period=product["finance_period"],
                makemodel=product["makemodel"]
            )

            if i == 0:
                custom_fields.append({"name": "makemodel", "value": product.makemodel})
                custom_fields.append({"name": "s_price", "value": "${:.2f}".format(product.net_price())})
                custom_fields.append({"name": "s_tax", "value": "${:.2f}".format(product.tax)})
                custom_fields.append({"name": "s_balance", "value": "${:.2f}".format(product.balance())})
                custom_fields.append({"name": "s_down", "value": "${:.2f}".format(product.down_payment())})
                custom_fields.append(
                    {"name": "s_cc", "value": "${:.2f} / ${:.2f}".format(product.cash_credit, product.check)})
                custom_fields.append({"name": "s_unpaid", "value": "${:.2f}".format(product.unpaid_balance())})
                custom_fields.append({"name": "s_monthly", "value": "${:.2f}".format(product.monthly_minimum())})

                if product.product_type == "FOOD":
                    custom_fields.append({"name": "special", "value": '0% interest food order'})

                if product.cash_credit != 0 or product.check != 0:
                    custom_fields.append({"name": "check_cc", "value": True})
                else:
                    custom_fields.append({"name": "check_ach", "value": True})
            elif i == 1:
                custom_fields.append({"name": "makemodel_2", "value": product.makemodel})
                custom_fields.append({"name": "s_price_2", "value": "${:.2f}".format(product.net_price())})
                custom_fields.append({"name": "s_tax_2", "value": "${:.2f}".format(product.tax)})
                custom_fields.append({"name": "s_balance_2", "value": "${:.2f}".format(product.balance())})
                custom_fields.append({"name": "s_down_2", "value": "${:.2f}".format(product.down_payment())})
                custom_fields.append(
                    {"name": "s_cc_2", "value": "${:.2f} / ${:.2f}".format(product.cash_credit, product.check)})
                custom_fields.append({"name": "s_unpaid_2", "value": "${:.2f}".format(product.unpaid_balance())})
                custom_fields.append({"name": "s_monthly_2", "value": "${:.2f}".format(product.monthly_minimum())})

                if product.product_type == "FOOD":
                    custom_fields.append({"name": "special_2", "value": '0% interest food order'})

                if product.cash_credit != 0 or product.check != 0:
                    custom_fields.append({"name": "check_cc_2", "value": True})
                else:
                    custom_fields.append({"name": "check_ach_2", "value": True})

            i = i + 1

            product.save()
        url = 'https://api.hellosign.com/v3/signature_request/send_with_template'

        if co_enabled == False:
            message = "Dear " + main_customer.name
            message += "\n\n"
            message += "Thank you for your interest in American Frozen Foods!\n\n"
            message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
            message += "Thank you for the opportunity to be of service!"
            payload = {
                "test_mode": 1,
                "title": "American Frozen Foods Documentation",
                "subject": "American Frozen Foods Documentation",
                "message": message,
                "template_id": template_id,
                "signers[buyer][name]": main_customer.name,
                "signers[buyer][email_address]": main_customer.email,
                "custom_fields": json.dumps(custom_fields),
                "ccs[cc1][email_address]": "developer@dcg.dev"
                # "ccs[cc1][email_address]": "Billyrapp@yahoo.com",
                # "ccs[cc2][email_address]": "susan.treglia@yahoo.com",
                # "ccs[cc3][email_address]": "americanfoods5@gmail.com"
            }
        else:
            message = "Dear " + main_customer.name + " and " + contact["co_name"] + "\n"
            message += "\n\n"
            message += "Thank you for your interest in American Frozen Foods!\n\n"
            message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
            message += "Thank you for the opportunity to be of service!"

            payload = {
                "test_mode": 1,
                "title": "American Frozen Foods Documentation",
                "subject": "American Frozen Foods Documentation",
                "message": message,
                "template_id": template_id,
                "signers[buyer][name]": main_customer.name,
                "signers[buyer][email_address]": main_customer.email,
                "signers[cobuyer][name]": co_app["name"],
                "signers[cobuyer][email_address]": co_app["email"],
                "custom_fields": json.dumps(custom_fields),
                "ccs[cc1][email_address]": "developer@dcg.dev"
                # "ccs[cc1][email_address]": "Billyrapp@yahoo.com",
                # "ccs[cc2][email_address]": "susan.treglia@yahoo.com",
                # "ccs[cc3][email_address]": "americanfoods5@gmail.com"
            }

        env = settings.EMAIL_HOST_USER
        if env == 'developer@dcg.dev':
            applicantEmail = main_customer.email
            coApplicantEmail = co_app["email"]
            coApplicantEmail = coApplicantEmail if coApplicantEmail is not None else ''

            if sendEmailOkay(applicantEmail,coApplicantEmail):
                response = requests.post(url, data=payload, auth=HTTPBasicAuth(settings.HELLOSIGN_CLIENT_ID, ''))
                print(response.json())
                if response.status_code == 200:
                    data = response.json()
                    print(data['signature_request']['signature_request_id'])
                    application.hello_sign_ref = data['signature_request']['signature_request_id']
                    print('email sent ref----',data['signature_request']['signature_request_id'])
                else:
                    application.hello_sign_ref = "Email Not Sent"
        else:
            response = requests.post(url, data=payload, auth=HTTPBasicAuth(settings.HELLOSIGN_CLIENT_ID, ''))
            print(response.json())
            if response.status_code == 200:
                data = response.json()
                print(data['signature_request']['signature_request_id'])
                application.hello_sign_ref = data['signature_request']['signature_request_id']
            else:
                application.hello_sign_ref = "Email Not Sent"

        application.save()

        if preapproval_id != 0:
            approval = Preapproval.objects.get(id=preapproval_id)
            approval.status = 3
            approval.save()

        return Response({
            'ok': True
        })
    else:
        main_customer_set = Customer.objects.filter(cif_number=existing_id_cif).order_by('-id')[:1]
        #- is desc, [:1] is limit 1
        ex_customer = [m for m in main_customer_set]
        if len(ex_customer)==0:
            return Response("Invalid existing_customer_id", HTTP_400_BAD_REQUEST)

        main_customer = [m for m in main_customer_set][0]
        # deleting previous Hellosign contract-
        try:
            app = Application.objects.get(applicant=main_customer)
            result = delete_signature_request(app.hello_sign_ref)
            print('deleting previous Hellosign contract status-', result)
        except:
            pass
        main_customer.name = main_app["name"]
        main_customer.email = main_app["email"]
        main_customer.dobY = main_app["dobY"]
        main_customer.dobM = main_app["dobM"]
        main_customer.dobD = main_app["dobD"]
        main_customer.ssn = main_app["ssn"]
        main_customer.driver_license = main_app["dl"]
        main_customer.no_of_dependents = main_app["nod"]
        main_customer.cell_phone = main_app["cell_phone"]
        main_customer.home_phone = main_app["home_phone"]
        main_customer.street = main_app["street"]
        main_customer.city = main_app["city"]
        main_customer.state = main_app["state"]
        main_customer.zip = main_app["zip"]
        main_customer.years_there_first = main_app["yt1"]
        main_customer.own_or_rent = main_app["own_or_rent"]
        main_customer.present_employer = main_app["present_employer"]
        main_customer.years_there_second = main_app["yt2"]
        main_customer.job_title = main_app["job_title"]
        main_customer.employer_phone = main_app["employer_phone"]
        main_customer.monthly_income = main_app["monthly_income"]
        main_customer.additional_income = main_app["additional_income"]
        main_customer.source = main_app["source"]
        main_customer.landlord_mortgage_holder = main_app["landlord_holder"]
        main_customer.monthly_rent_mortgage_payment = main_app["monthly_rent_payment"]
        main_customer.save()
        application = Application.objects.get(applicant=main_customer)
        application.salesperson_email = request.user.email

        today = datetime.date.today()
        third_date = check_public_holiday(today + datetime.timedelta(days=3))
        if main_customer.state == "ME":
            third_date = check_public_holiday(today + datetime.timedelta(days=12))

        custom_fields = [
            {"name": "buyer_name", "value": main_customer.name},
            {"name": "buyer_address", "value": main_customer.street},
            {"name": "buyer_city", "value": main_customer.city},
            {"name": "buyer_state", "value": main_customer.state},
            {"name": "buyer_zip", "value": main_customer.zip},
            {"name": "buyer_phone", "value": main_customer.home_phone},
            {"name": "third_date", "value": third_date.strftime("%m/%d/%Y")},
            {"name": "buyer_full_address",
             "value": main_customer.street + ", " + main_customer.city + ", " + main_customer.state + ", " + main_customer.zip}
        ]

        order_type = contact["order_type"]
        if order_type == 1:
            custom_fields.append({"name": "buyer_email", "value": main_customer.email})
            # custom_fields.append({"name": "dobM", "value": main_customer.dobM})
            # custom_fields.append({"name": "dobD", "value": main_customer.dobD})
            # custom_fields.append({"name": "dobY", "value": main_customer.dobY})
            # custom_fields.append({"name": "yt1", "value": main_customer.years_there_first})
            # custom_fields.append({"name": "yt2", "value": main_customer.years_there_second})
            # custom_fields.append({"name": "cell_phone", "value": main_customer.cell_phone})
            # custom_fields.append({"name": "ssn", "value": main_customer.ssn})
            # custom_fields.append({"name": "present_employer", "value": main_customer.present_employer})
            # custom_fields.append({"name": "position", "value": main_customer.job_title})
            # custom_fields.append({"name": "monthly_income", "value": main_customer.monthly_income})
            # custom_fields.append({"name": "driver_license", "value": main_customer.driver_license})
            # custom_fields.append({"name": "nod", "value": main_customer.no_of_dependents})
            # custom_fields.append({"name": "other_income", "value": main_customer.additional_income})
            # custom_fields.append({"name": "source", "value": main_customer.source})
            # custom_fields.append({"name": "landlord_holder", "value": main_customer.landlord_mortgage_holder})
            # custom_fields.append({"name": "monthly_rent", "value": main_customer.monthly_rent_mortgage_payment})

        co_enabled = contact["co_enabled"]
        if co_enabled == True:
            co_customer = Customer.objects.get(id=application.co_applicant_id)
            co_customer.name = co_app["name"]
            co_customer.email = co_app["email"]
            co_customer.dobY = co_app["dobY"]
            co_customer.dobM = co_app["dobM"]
            co_customer.dobD = co_app["dobD"]
            co_customer.ssn = co_app["ssn"]
            co_customer.driver_license = co_app["dl"]
            co_customer.no_of_dependents = co_app["nod"]
            co_customer.cell_phone = co_app["cell_phone"]
            co_customer.home_phone = co_app["home_phone"]
            co_customer.street = co_app["street"]
            co_customer.city = co_app["city"]
            co_customer.state = co_app["state"]
            co_customer.zip = co_app["zip"]
            co_customer.years_there_first = co_app["yt1"]
            co_customer.own_or_rent = co_app["own_or_rent"]
            co_customer.present_employer = co_app["present_employer"]
            co_customer.years_there_second = co_app["yt2"]
            co_customer.job_title = co_app["job_title"]
            co_customer.employer_phone = co_app["employer_phone"]
            co_customer.monthly_income = co_app["monthly_income"]
            co_customer.additional_income = co_app["additional_income"]
            co_customer.source = co_app["source"]
            co_customer.landlord_mortgage_holder = co_app["landlord_holder"]
            co_customer.monthly_rent_mortgage_payment = co_app["monthly_rent_payment"]
            co_customer.save()

            application.co_applicant = co_customer
            application.co_enabled = True

            third_date = check_public_holiday(today + datetime.timedelta(days=3))
            if co_customer.state == "ME":
                third_date = check_public_holiday(today + datetime.timedelta(days=12))
            custom_fields.append({"name": "co_third_date", "value": third_date.strftime("%m/%d/%Y")})

            if order_type == 1:
                custom_fields.append({"name": "co_name", "value": co_customer.name})
                custom_fields.append({"name": "co_email", "value": co_customer.email})
                custom_fields.append({"name": "co_address", "value": co_customer.street})
                custom_fields.append({"name": "co_city", "value": co_customer.city})
                custom_fields.append({"name": "co_state", "value": co_customer.state})
                custom_fields.append({"name": "co_zip", "value": co_customer.zip})
                custom_fields.append({"name": "co_phone", "value": co_customer.home_phone})
                # custom_fields.append({"name": "co_home_phone", "value": co_customer.home_phone})
                # custom_fields.append({"name": "co_dobM", "value": co_customer.dobM})
                # custom_fields.append({"name": "co_dobD", "value": co_customer.dobD})
                # custom_fields.append({"name": "co_dobY", "value": co_customer.dobY})
                # custom_fields.append({"name": "co_yt1", "value": co_customer.years_there_first})
                # custom_fields.append({"name": "co_yt2", "value": co_customer.years_there_second})
                # custom_fields.append({"name": "co_cell_phone", "value": co_customer.cell_phone})
                # custom_fields.append({"name": "co_ssn", "value": co_customer.ssn})
                # custom_fields.append({"name": "co_present_employer", "value": co_customer.present_employer})
                # custom_fields.append({"name": "co_position", "value": co_customer.job_title})
                # custom_fields.append({"name": "co_monthly_income", "value": co_customer.monthly_income})
                # custom_fields.append({"name": "co_driver_license", "value": co_customer.driver_license})
                # custom_fields.append({"name": "co_nod", "value": co_customer.no_of_dependents})
                # custom_fields.append({"name": "co_other_income", "value": co_customer.additional_income})
                # custom_fields.append({"name": "co_source", "value": co_customer.source})
                # custom_fields.append({"name": "co_landlord_holder", "value": co_customer.landlord_mortgage_holder})
                # custom_fields.append({"name": "co_monthly_rent", "value": co_customer.monthly_rent_mortgage_payment})

        application.status = "waiting"
        application.created_at = datetime.date.today()
        application.save()

        products_count = len(products)
        template_id = ""
        if order_type == 1:
            if co_enabled == False:
                if products_count == 1:
                    template_id = "71deb1e2dad0d0a0f7dda94187274a70b0c42859"
                else:
                    template_id = "59f4b4f6beecdc1adf69b3f514254537e7df03e2"
            else:
                if co_complete == False:
                    if products_count == 1:
                        template_id = "c50646d726f8892cee46ec2b2695b68efe2a6d70"
                    else:
                        template_id = "2eed73d46c691102b93a6592486a05af25715113"
                else:
                    if co_separate == False:
                        if products_count == 1:
                            template_id = "ad4ccc1e4c23d1e92811a1dc1a0667151b0f247d"
                        else:
                            template_id = "d085baae4ac46ffd7359782cedf0b46bc03204a8"
                    else:
                        if products_count == 1:
                            template_id = "79597c3abf1aed2f90d778807fdd714041ba3714"
                        else:
                            template_id = "cba1acd7f1724f792decc49e49b32d445cb29a5b"
        elif order_type == 2:
            if co_enabled == False:
                if products_count == 1:
                    template_id = "1a3254cae49432e7f1eedb93c2cf00009dd14422"
                else:
                    template_id = "b1069d5dac0001f2b94cbf5c20c39b2274f114ea"
            else:
                if co_complete == False:
                    if products_count == 1:
                        template_id = "a0b37dfc5d3909a0d42f9c7a11553bd9adf5b672"
                    else:
                        template_id = "98642bf455ad62d7984ef8899a4389e8405d1f66"
                else:
                    if co_separate == False:
                        if products_count == 1:
                            template_id = "df05890933839a3d9879b4167b38ae907d135c57"
                        else:
                            template_id = "5a7bd4c90d262d667205f5151085014a9621210d"
                    else:
                        if products_count == 1:
                            template_id = "9529f3555e6ac8224e296f7a99c01267cbcb870e"
                        else:
                            template_id = "cfe9d26bdf7d1613530b9a23508d950189d1cb42"

        prod = Product.objects.filter(app=application)
        prod.delete()

        i = 0
        for product in products:
            product_type = product["product_type"]
            product = Product(
                app=application,
                product_type=product_type,
                price=float(product["price"]),
                total_discount=float(product["total_discount"]),
                coupon=float(product["coupon"]),
                add_discount=float(product["add_discount"]),
                tax=float(product["tax"]),
                cash_credit=float(product["cash_credit"]),
                check=float(product["check"]),
                finance_period=product["finance_period"],
                makemodel=product["makemodel"]
            )

            if i == 0:
                custom_fields.append({"name": "makemodel", "value": product.makemodel})
                custom_fields.append({"name": "s_price", "value": "${:.2f}".format(product.net_price())})
                custom_fields.append({"name": "s_tax", "value": "${:.2f}".format(product.tax)})
                custom_fields.append({"name": "s_balance", "value": "${:.2f}".format(product.balance())})
                custom_fields.append({"name": "s_down", "value": "${:.2f}".format(product.down_payment())})
                custom_fields.append(
                    {"name": "s_cc", "value": "${:.2f} / ${:.2f}".format(product.cash_credit, product.check)})
                custom_fields.append({"name": "s_unpaid", "value": "${:.2f}".format(product.unpaid_balance())})
                custom_fields.append({"name": "s_monthly", "value": "${:.2f}".format(product.monthly_minimum())})

                if product.product_type == "FOOD":
                    custom_fields.append({"name": "special", "value": '0% interest food order'})

                if product.cash_credit != 0 or product.check != 0:
                    custom_fields.append({"name": "check_cc", "value": True})
                else:
                    custom_fields.append({"name": "check_ach", "value": True})
            elif i == 1:
                custom_fields.append({"name": "makemodel_2", "value": product.makemodel})
                custom_fields.append({"name": "s_price_2", "value": "${:.2f}".format(product.net_price())})
                custom_fields.append({"name": "s_tax_2", "value": "${:.2f}".format(product.tax)})
                custom_fields.append({"name": "s_balance_2", "value": "${:.2f}".format(product.balance())})
                custom_fields.append({"name": "s_down_2", "value": "${:.2f}".format(product.down_payment())})
                custom_fields.append(
                    {"name": "s_cc_2", "value": "${:.2f} / ${:.2f}".format(product.cash_credit, product.check)})
                custom_fields.append({"name": "s_unpaid_2", "value": "${:.2f}".format(product.unpaid_balance())})
                custom_fields.append({"name": "s_monthly_2", "value": "${:.2f}".format(product.monthly_minimum())})

                if product.product_type == "FOOD":
                    custom_fields.append({"name": "special_2", "value": '0% interest food order'})

                if product.cash_credit != 0 or product.check != 0:
                    custom_fields.append({"name": "check_cc_2", "value": True})
                else:
                    custom_fields.append({"name": "check_ach_2", "value": True})

            i = i + 1

            product.save()
        url = 'https://api.hellosign.com/v3/signature_request/send_with_template'

        if co_enabled == False:
            message = "Dear " + main_customer.name
            message += "\n\n"
            message += "Thank you for your interest in American Frozen Foods!\n\n"
            message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
            message += "Thank you for the opportunity to be of service!"
            payload = {
                "test_mode": 1,
                "title": "American Frozen Foods Documentation",
                "subject": "American Frozen Foods Documentation",
                "message": message,
                "template_id": template_id,
                "signers[buyer][name]": main_customer.name,
                "signers[buyer][email_address]": main_customer.email,
                "custom_fields": json.dumps(custom_fields),
                "ccs[cc1][email_address]": "developer@dcg.dev"
                # "ccs[cc1][email_address]": "Billyrapp@yahoo.com",
                # "ccs[cc2][email_address]": "susan.treglia@yahoo.com",
                # "ccs[cc3][email_address]": "americanfoods5@gmail.com"
            }
        else:
            message = "Dear " + main_customer.name + " and " + contact["co_name"] + "\n"
            message += "\n\n"
            message += "Thank you for your interest in American Frozen Foods!\n\n"
            message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
            message += "Thank you for the opportunity to be of service!"

            payload = {
                "test_mode": 1,
                "title": "American Frozen Foods Documentation",
                "subject": "American Frozen Foods Documentation",
                "message": message,
                "template_id": template_id,
                "signers[buyer][name]": main_customer.name,
                "signers[buyer][email_address]": main_customer.email,
                "signers[cobuyer][name]": co_app["name"],
                "signers[cobuyer][email_address]": co_app["email"],
                "custom_fields": json.dumps(custom_fields),
                "ccs[cc1][email_address]": "developer@dcg.dev"
                # "ccs[cc1][email_address]": "Billyrapp@yahoo.com",
                # "ccs[cc2][email_address]": "susan.treglia@yahoo.com",
                # "ccs[cc3][email_address]": "americanfoods5@gmail.com"
            }
        env = settings.EMAIL_HOST_USER
        if env == 'developer@dcg.dev':
            applicantEmail = main_customer.email
            coApplicantEmail = co_app["email"]
            coApplicantEmail = coApplicantEmail if coApplicantEmail is not None else ''
            if sendEmailOkay(applicantEmail,coApplicantEmail):
                response = requests.post(url, data=payload, auth=HTTPBasicAuth(settings.HELLOSIGN_CLIENT_ID, ''))
                #print(response)

                if response.status_code == 200:
                    data = response.json()
                    print(data['signature_request']['signature_request_id'])
                    application.hello_sign_ref = data['signature_request']['signature_request_id']
                    print('email sent---------ref=', data['signature_request']['signature_request_id'])
                else:
                    application.hello_sign_ref = "Email Not Sent"
        else:
            response = requests.post(url, data=payload, auth=HTTPBasicAuth(settings.HELLOSIGN_CLIENT_ID, ''))
            # print(response)

            if response.status_code == 200:
                data = response.json()
                print(data['signature_request']['signature_request_id'])
                application.hello_sign_ref = data['signature_request']['signature_request_id']
            else:
                application.hello_sign_ref = "Email Not Sent"


        application.save()

        if preapproval_id != 0:
            approval = Preapproval.objects.get(id=preapproval_id)
            approval.status = 3
            approval.save()

        return Response({
            'ok': True
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def AppsView(request):
    # customers = Customer.objects.filter(~Q(co_applicant_id = -1))
    apps = Application.objects.all().exclude(status='deleted').exclude(status='funded').exclude(status='cancelled').order_by('-updated_at')
    result = []

    for app in apps:
        customer = app.applicant
        item = {
            "id": app.id,
            "name": customer.name,
            "email": customer.email,
            "status": app.status,
            "created_at": app.created_at,
            "updated_at":app.updated_at,
            "city": customer.city,
            "street": customer.street,
            "state": customer.state,
            "zip": customer.zip,
            "co_customer": app.co_enabled,
            "salesperson_email": app.salesperson_email,
            "rating": app.rating,
            "message": app.message
        }
        try:
            if app.co_applicant.name is not None:
                item["co_name"] = app.co_applicant.name
        except Exception as e:
            item["co_name"] = ""

        item_products = []
        products = Product.objects.filter(app=app)
        for product in products:
            item_products.append({
                "id": product.id,
                "type": product.product_type,
                "balance": round(product.balance(), 2),
                "monthly_minimum": round(product.monthly_minimum(), 2)
            })
        item["products"] = item_products
        if app.hello_sign_ref == None or app.hello_sign_ref == "Email Not Sent":
            item["hello_sign"] = []
        else:
            item["hello_sign"] = get_signature_status(app.hello_sign_ref)
        result.append(item)

    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def Appsnohello(request):
    salesperson_email = request.data.get('email')
    if salesperson_email is None:
        apps = Application.objects.exclude(hello_sign_ref='Email Not Sent').exclude(status='deleted').order_by('-updated_at')
    else:
        apps = Application.objects.filter(salesperson_email=salesperson_email).exclude(hello_sign_ref='Email Not Sent').exclude(status='deleted').order_by('-updated_at')


    result = []
    for app in apps:
        customer = app.applicant
        item = {
            "id": app.id,
            "name": customer.name,
            "email": customer.email,
            "status": app.status,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
            "city": customer.city,
            "street": customer.street,
            "state": customer.state,
            "zip": customer.zip,
            "co_customer": app.co_enabled,
            "salesperson_email": app.salesperson_email,
            "rating": app.rating,
            "message": app.message
        }
        try:
            if app.co_applicant.name is not None:
                item["co_name"] = app.co_applicant.name
        except Exception as e:
            item["co_name"] = ""
        item_products = []
        products = Product.objects.filter(app=app)
        for product in products:
            item_products.append({
                "id": product.id,
                "type": product.product_type,
                "balance": round(product.balance(), 2),
                "monthly_minimum": round(product.monthly_minimum(), 2)
            })
        item["products"] = item_products

        data = get_signature_status(app.hello_sign_ref)
        total_signers = len(data)
        print("Total Signers", total_signers)
        if total_signers == 0:
            print("No Info Found for Hellosign")
            continue
        signed_count = 0
        for i in data:
            print(i['status_code'])
            if i['status_code'] == "signed":
                signed_count += 1

        if signed_count == total_signers:
            print("Application is Pending")
            if item["status"] == "waiting":
                item["status"] = "pending"
            result.append(item)
        else:
            item["hello_sign"] = data
            result.append(item)
            print("Application is Incomplete")
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def AppByIdView(request, pk):
    app = Application.objects.get(id=pk)

    if app == None:
        return Response("Invalid App Id", HTTP_400_BAD_REQUEST)
    #customer = Customer.objects.get(id= app)

    result = {
        "id": app.id,
        "status": app.status,
        "salesperson_email": app.salesperson_email,
        "rating": app.rating,
        "message": app.message,
        "cif_number": app.applicant.cif_number,
        "applicant": {
            "id": app.applicant.id,
            "name": app.applicant.name,
            "email": app.applicant.email,
            "address": app.applicant.street,
            "zip": app.applicant.zip,
            "city": app.applicant.city,
            "state": app.applicant.state,
            "phone": app.applicant.home_phone,
            "dobY": app.applicant.dobY,
            "dobM": app.applicant.dobM,
            "dobD": app.applicant.dobD,
            "ssn": app.applicant.ssn,
            "dl": app.applicant.driver_license,
            "nod": app.applicant.no_of_dependents,
            "yt1": app.applicant.years_there_first,
            "yt2": app.applicant.years_there_second,
            "own_or_rent": app.applicant.own_or_rent,
            "present_employer": app.applicant.present_employer,
            "job_title": app.applicant.job_title,
            "employer_phone": app.applicant.employer_phone,
            "monthly_income": app.applicant.monthly_income,
            "additional_income": app.applicant.additional_income,
            "source": app.applicant.source,
            "landlord_holder": app.applicant.landlord_mortgage_holder,
            "monthly_rent_payment": app.applicant.monthly_rent_mortgage_payment

        },
        "products": []
    }

    if app.co_enabled:
        result["co_applicant"] = {
            "id": app.co_applicant.id,
            "name": app.co_applicant.name,
            "email": app.co_applicant.email,
            "address": app.co_applicant.street,
            "zip": app.co_applicant.zip,
            "city": app.co_applicant.city,
            "state": app.co_applicant.state,
            "phone": app.co_applicant.home_phone,
            "dobY": app.co_applicant.dobY,
            "dobM": app.co_applicant.dobM,
            "dobD": app.co_applicant.dobD,
            "ssn": app.co_applicant.ssn,
            "dl": app.co_applicant.driver_license,
            "nod": app.co_applicant.no_of_dependents,
            "nod": app.co_applicant.no_of_dependents,
            "yt1": app.co_applicant.years_there_first,
            "yt2": app.co_applicant.years_there_second,
            "own_or_rent": app.co_applicant.own_or_rent,
            "present_employer": app.co_applicant.present_employer,
            "job_title": app.co_applicant.job_title,
            "employer_phone": app.co_applicant.employer_phone,
            "monthly_income": app.co_applicant.monthly_income,
            "additional_income": app.co_applicant.additional_income,
            "source": app.co_applicant.source,
            "landlord_holder": app.co_applicant.landlord_mortgage_holder,
            "monthly_rent_payment": app.co_applicant.monthly_rent_mortgage_payment
        }

    if app.hello_sign_ref is None or app.hello_sign_ref == "Email Not Sent":
        result["hello_sign"] = []
    else:
        result["hello_sign"] = get_signature_status(app.hello_sign_ref)

    products = Product.objects.filter(app=app)
    for product in products:
        result["products"].append({
            "id": product.id,
            "product_type": product.product_type,
            "balance": product.balance(),
            "period": product.finance_period,
            "price": product.price,
            "coupon": product.coupon,
            "tax": product.tax,
            "finance_period": product.finance_period,
            "check": product.check,
            "makemodel": product.makemodel,
            "cash_credit": product.cash_credit,
            "total_discount": product.total_discount,
            "add_discount": product.add_discount
        })
    funding_requests = FundingRequest.objects.filter(app_id=pk)
    res = []
    for fitem in funding_requests:
        item = {
            "id": fitem.id,
            "created_at": fitem.created_at,
            "status": fitem.status,
            "delivery_date": fitem.delivery_date
        }
        res.append(item)
    result['funding'] = res

    return Response(result)


# Local Database Search
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SearchCustomerViewLocal(request):
    data = request.data
    customers = Customer.objects.filter(email__icontains=data["email"]).filter(cell_phone__icontains=data["phone"])
    result = []
    for customer in customers:
        if customer.dobD is None or customer.dobM is None or customer.dobY is None:
            customer.dobD = str(00)
            customer.dobM = str(00)
            customer.dobY = str(0000)
        result.append({
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "street": customer.street,
            "city": customer.city,
            "state": customer.state,
            "zip": customer.zip,
            "phone": customer.cell_phone,
            "dob": customer.dobM + "/" + customer.dobM + "/" + customer.dobY,
            "cifnumber": customer.cif_number
        })
    return Response(result)


# Nortridge Search

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SearchCustomer(request):
    data = request.data
    customer = None
    try:
        main_customer_set = Customer.objects.filter(email = data['email'], cell_phone = data['phone']).order_by('-id')[:1]
        # - is desc, [:1] is limit 1
        customer = [m for m in main_customer_set][-1]
        #customer = Customer.objects.get(email = data['email'], cell_phone = data['phone'])
    except:
        pass
    if customer is not None:
        #converting db row to dict
        all_field_data = model_to_dict(customer, fields=[field.name for field in customer._meta.fields])
        credit_application = None
        customer_co_app_id = None
        try:
            credit_application = CreditApplication.objects.get(credit_app_id=customer.id)
            customer_co_app_id = credit_application.credit_co_app_id
        except:
            pass
        result = {}
        result['main_app'] = all_field_data
        if credit_application is not None and customer_co_app_id is not None:
            print('credit_application.credit_co_app_id=',credit_application.credit_co_app_id)
            co_customer = Customer.objects.get(id=credit_application.credit_co_app_id)
            result['co_enabled'] = True
            result['co_app'] = model_to_dict(co_customer, fields=[field.name for field in co_customer._meta.fields])
        else:
            result['co_enabled'] = False
            result['co_app'] = {}
        return Response({'status':'success','message':'','ok':True,'data':result})
    result = []
    try:
        r = searchContactsByPhoneEmail(data['phone'], data['email'])  # searchContacts(data["name"], data["city"])
        final = r['payload']['data']
        for data in final:
            result.append(data)
        if len(result) == 0:
            return Response({'status': 'error', 'message': 'No Data found', 'ok': True, 'data': [], 'msg': 'No Data found'})
    except Exception as e:
        print(e, "No Data found")
        return Response({'status':'error','message':'No Data found','ok':True,'data':[], 'msg':'No Data found'})
    r = result[-1]

    cif_no = r['Cifno']
    import traceback
    try:
        nor_customer = getContact(cif_no)
        print(nor_customer)

        main_app = {}
        main_app['name'] = nor_customer['Firstname1']
        main_app['first_name'] = nor_customer['Firstname1'] +' '+nor_customer['Lastname1']
        main_app['last_name'] = nor_customer['Lastname1']
        main_app['email'] = nor_customer['Email']
        main_app['dobY'] = ''
        main_app['dobM'] = ''
        main_app['dobD'] = ''
        main_app['ssn'] = None
        main_app['driver_license'] = None
        main_app['no_of_dependents'] = None
        main_app['cell_phone'] = nor_customer['Cif_Phone_Nums'][0]['Phone_Raw']
        main_app['home_phone'] = None
        main_app['street'] = nor_customer['Street_Address1']
        main_app['city'] = nor_customer['City']
        main_app['state'] = nor_customer['State']
        main_app['zip'] = nor_customer['Zip']
        main_app['years_there_first'] = None
        main_app['own_or_rent'] = None
        main_app['employement_status'] = None
        main_app['present_employer'] = None
        main_app['years_there_second'] = None
        main_app['job_title'] = None
        main_app['employer_phone'] = None
        main_app['monthly_income'] = None
        main_app['additional_income'] = None
        main_app['source'] = None
        main_app['landlord_mortgage_holder'] = None
        main_app['monthly_rent_mortgage_payment'] = None
        main_app['cif_number'] = nor_customer['Cifno']
        main_app['nortridge_cif_number'] = nor_customer['Cifnumber']

        data = {'main_app':main_app,'co_app':{}, 'co_enabled':False}

        return Response({'status':'success','message':'','ok':True,'data':data})
    except Exception as e:
        print(e)
        traceback.print_exc()
        return Response({'status':'error','message':'Çustomer Not Found'}, HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def SearchCustomerByID(request):
    data = request.data
    customer_id = data['id']
    token = data['token']
    try:
        customer = Customer.objects.get(id=customer_id)
        digest = customer.email + str(customer_id)
        digest_token = hashlib.sha512(digest.encode())
        digest_token = digest_token.hexdigest()
        #print(digest_token, '==', token)
        if digest_token != token:
            return Response({
                'status': 'error',
                'message': 'Authentication failure',
                'ok': False
            })

        all_field_data = model_to_dict(customer, fields=[field.name for field in customer._meta.fields])
        credit_application = None
        try:
            credit_application = CreditApplication.objects.get(credit_app_id=customer.id)
        except Exception as e:
            print(e)
            pass
        result = {}
        result['main_app'] = all_field_data
        if credit_application is not None:
            co_customer = Customer.objects.get(id=credit_application.credit_co_app_id)
            result['co_enabled'] = True
            result['co_app'] = model_to_dict(co_customer, fields=[field.name for field in co_customer._meta.fields])
        else:
            result['co_enabled'] = False
            result['co_app'] = {}
        return Response({'status': 'success', 'message': '', 'ok': True, 'data': result})
    except:
        return Response({'status': 'error', 'message': 'Çustomer Not Found'}, HTTP_400_BAD_REQUEST)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SearchCustomerViewNortridge(request):
    data = request.data
    result = []
    try:
        r = searchContactsByPhoneEmail(data['phone'],data['email'])#searchContacts(data["name"], data["city"])
        final = r['payload']['data']
        for data in final:
            print(data,'..................')
            result.append(data)
    except Exception as e:
        print(e,"No Data found")

    return Response(result)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetCustomerByIdView(request, pk):
    try:
        customer = Customer.objects.get(id=pk)
    except Customer.DoesNotExist:
        customer = None

    if customer == None:
        return Response("Invalid Customer Id", HTTP_400_BAD_REQUEST)
    if customer.dobD == None or customer.dobM == None or customer.dobY == None:
        customer.dobD = str(00)
        customer.dobM = str(00)
        customer.dobY = str(0000)

    print(customer.name)

    result = {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "street": customer.street,
        "city": customer.city,
        "state": customer.state,
        "zip": customer.zip,
        "cell_phone": customer.cell_phone,
        "home_phone": customer.home_phone,
        "dob": customer.dobM + "/" + customer.dobM + "/" + customer.dobY,
        "dobY": customer.dobY,
        "dobM": customer.dobM,
        "dobD": customer.dobD,
        "ssn": customer.ssn,
        "dl": customer.driver_license,
        "nod": customer.no_of_dependents,
        "yt1": customer.years_there_first,
        "yt2": customer.years_there_second,
        "own_or_rent": customer.own_or_rent,
        "present_employer": customer.present_employer,
        "job_title": customer.job_title,
        "employer_phone": customer.employer_phone,
        "monthly_income": customer.monthly_income,
        "additional_income": customer.additional_income,
        "source": customer.source,
        "landlord_holder": customer.landlord_mortgage_holder,
        "monthly_rent_payment": customer.monthly_rent_mortgage_payment,
        "apps": [],
        "cif_number": customer.cif_number,
        "nortridge_cif_number": customer.nortridge_cif_number,
        "co_customer": {}

    }
    try:
        apps = Application.objects.get(applicant=customer)
        if apps == None:
            print("Application is None")
        else:
            user = User.objects.get(email=apps.salesperson_email)
            company = Company.objects.get(id = user.dealer_company_id)
            result["apps"].append({
                "id": apps.id,
                "status": apps.status,
                "created_at": apps.created_at,
                "co_enabled": apps.co_enabled,
                "co_app_id": apps.co_applicant_id,
                "salesperson_email": apps.salesperson_email,
                "salesperson_first_name": user.first_name,
                "salesperson_last_name": user.last_name,
                "salesperson_company_name": company.name
            })


        if apps.hello_sign_ref == None or apps.hello_sign_ref == "Email Not Sent":
            result["hello_sign"] = {}
        else:
            result["hello_sign"] = get_signature_status(apps.hello_sign_ref)

        if apps.co_enabled == True:
            co_customer = Customer.objects.get(id=apps.co_applicant_id)
            if co_customer.dobD == None or co_customer.dobM == None or co_customer.dobY == None:
                co_customer.dobD = str(00)
                co_customer.dobM = str(00)
                co_customer.dobY = str(0000)
            result["co_customer"] = {
                "id": co_customer.id,
                "name": co_customer.name,
                "email": co_customer.email,
                "street": co_customer.street,
                "city": co_customer.city,
                "state": co_customer.state,
                "zip": co_customer.zip,
                "cell_phone": co_customer.cell_phone,
                "home_phone": co_customer.home_phone,
                "dob": co_customer.dobM + "/" + co_customer.dobM + "/" + co_customer.dobY,
                "dobY": co_customer.dobY,
                "dobM": co_customer.dobM,
                "dobD": co_customer.dobD,
                "ssn": co_customer.ssn,
                "dl": co_customer.driver_license,
                "nod": co_customer.no_of_dependents,
                "yt1": co_customer.years_there_first,
                "yt2": co_customer.years_there_second,
                "own_or_rent": co_customer.own_or_rent,
                "present_employer": co_customer.present_employer,
                "job_title": co_customer.job_title,
                "employer_phone": co_customer.employer_phone,
                "monthly_income": co_customer.monthly_income,
                "additional_income": co_customer.additional_income,
                "source": co_customer.source,
                "landlord_holder": co_customer.landlord_mortgage_holder,
                "monthly_rent_payment": co_customer.monthly_rent_mortgage_payment
            }
        else:
            print("Else Condition")
        pre_approvals = []
        preapprovals = Preapproval.objects.filter(customer=customer)
        for approval in preapprovals:
            pre_req_id = approval.preapproval_request
            pre_req = ''
            if pre_req_id==0:
                pre_req = ''
            elif pre_req_id==1:
                pre_req = 'requested for pre-approval'
            else:
                pre_req = 'admin decline'
            pre_approvals.append({
                "id": approval.id,
                "status": approval.status,
                "message": approval.message,
                "created_at": approval.created_at,
                "updated_at": approval.updated_at,
                "product_type": approval.product_type,
                "appliance": approval.appliance,
                "earliest_delivery_date": approval.earliest_delivery_date,
                "pre_approvals_request_id": pre_req_id,
                "pre_approvals_request": pre_req

            })
        result["preapproval"] = pre_approvals
        return Response(result)
    except Exception as e:
        return Response("Application/Customer Not Found", HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetCustomersView(request):
    customers = Customer.objects.all()
    result = []

    for customer in reversed(customers):
        item = {}
        print("Customer ID ", customer.id)
        if customer.dobD is None or customer.dobM is None or customer.dobY is None:
            customer.dobD = str(00)
            customer.dobM = str(00)
            customer.dobY = str(0000)

        item = {"id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "street": customer.street,
                "city": customer.city,
                "state": customer.state,
                "zip": customer.zip,
                "cell_phone": customer.cell_phone,
                "home_phone": customer.home_phone,
                "dob": customer.dobM + "/" + customer.dobM + "/" + customer.dobY,
                "dobY": customer.dobY,
                "dobM": customer.dobM,
                "dobD": customer.dobD,
                "ssn": customer.ssn,
                "dl": customer.driver_license,
                "nod": customer.no_of_dependents,
                "yt1": customer.years_there_first,
                "yt2": customer.years_there_second,
                "own_or_rent": customer.own_or_rent,
                "present_employer": customer.present_employer,
                "job_title": customer.job_title,
                "employer_phone": customer.employer_phone,
                "monthly_income": customer.monthly_income,
                "additional_income": customer.additional_income,
                "source": customer.source,
                "landlord_holder": customer.landlord_mortgage_holder,
                "monthly_rent_payment": customer.monthly_rent_mortgage_payment,
                "co_customer": {},
                "preapproval": {}
                }
        try:
            apps = Application.objects.get(applicant=customer.id)
            if apps.co_enabled == True:
                print("This is IF Condition")
                co_customer = Customer.objects.get(id=apps.co_applicant_id)
                if co_customer.dobD is None or co_customer.dobM is None or co_customer.dobY is None:
                    co_customer.dobD = str(00)
                    co_customer.dobM = str(00)
                    co_customer.dobY = str(0000)
                item["co_customer"] = {
                    "id": co_customer.id,
                    "name": co_customer.name,
                    "email": co_customer.email,
                    "street": co_customer.street,
                    "city": co_customer.city,
                    "state": co_customer.state,
                    "zip": co_customer.zip,
                    "cell_phone": co_customer.cell_phone,
                    "home_phone": co_customer.home_phone,
                    "dob": co_customer.dobM + "/" + co_customer.dobM + "/" + co_customer.dobY,
                    "dobY": co_customer.dobY,
                    "dobM": co_customer.dobM,
                    "dobD": co_customer.dobD,
                    "ssn": co_customer.ssn,
                    "dl": co_customer.driver_license,
                    "nod": co_customer.no_of_dependents,
                    "yt1": co_customer.years_there_first,
                    "yt2": co_customer.years_there_second,
                    "own_or_rent": co_customer.own_or_rent,
                    "present_employer": co_customer.present_employer,
                    "job_title": co_customer.job_title,
                    "employer_phone": co_customer.employer_phone,
                    "monthly_income": co_customer.monthly_income,
                    "additional_income": co_customer.additional_income,
                    "source": co_customer.source,
                    "landlord_holder": co_customer.landlord_mortgage_holder,
                    "monthly_rent_payment": co_customer.monthly_rent_mortgage_payment
                }
            else:
                print("This is Else ")
            preapprovals = Preapproval.objects.filter(customer=int(apps.applicant_id))
            for pre in preapprovals:
                temp = {
                    "id": pre.id,
                    "status": pre.status,
                    "product_type": pre.product_type,
                    "message": pre.message,
                    "created_at": pre.created_at,
                    "updated_at": pre.updated_at,
                    "app_id": pre.app_id,
                    "appliance": pre.appliance,
                    "earliest_delivery_date": pre.earliest_delivery_date
                }
                item["preapproval"] = temp
                result.append(item)

        except Exception as ModuleNotFoundError:
            print("Exception Found", ModuleNotFoundError)

    return Response(result)


class PreapprovalsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        approvals = Preapproval.objects.all().exclude(status=3).exclude(status=4)
        result = []
        for approval in reversed(approvals):
            if approval.customer is None:
                continue
            pre_req_id = approval.preapproval_request
            pre_req = ''
            if pre_req_id==0:
                pre_req = ''
            elif pre_req_id==1:
                pre_req = 'requested for pre-approval'
            else:
                pre_req = 'admin decline'
            result.append({
                "id": approval.id,
                "created_at": approval.created_at,
                "updated_at": approval.updated_at,
                "status": approval.status,
                "message": approval.message,
                "product_type": approval.product_type,
                "appliance": approval.appliance,
                "earliest_delivery_date": approval.earliest_delivery_date,
                "pre_approvals_request_id": pre_req_id,
                "pre_approvals_request": pre_req,
                "customer": {
                    "id": approval.customer.id,
                    "name": approval.customer.name,
                    "email": approval.customer.email,
                    "street": approval.customer.street,
                    "city": approval.customer.city,
                    "state": approval.customer.state,
                    "zip": approval.customer.zip
                }
            })
        return Response(result)

    def post(self, request, *args, **kwargs):
        customer_id = request.data.get('customer_id')
        customer = Customer.objects.filter(id=customer_id).first()
        approval = Preapproval(
            customer=customer,
            created_at=datetime.date.today()
        )
        approval.save()
        return Response('ok')


class PreapprovalDetailView(APIView):
    def put(self, request, pk, *args, **kwargs):
        status = request.data.get('status')
        message = request.data.get('message')
        appliance = request.data.get('appliance')
        product_type = ''
        try:
            product_type = request.data.get('product_type')
        except:
            pass
        earliest_delivery_date = request.data.get('earliest_delivery_date')
        approval = Preapproval.objects.get(id=pk)
        pre_req = approval.preapproval_request
        approval.status = status
        approval.message = message
        approval.updated_at = datetime.date.today()
        if product_type != '':
            approval.product_type = product_type
        approval.appliance = appliance
        approval.earliest_delivery_date = earliest_delivery_date
        if status==1:
            approval.preapproval_request = 0
        elif status==2:
            if pre_req == 0:
                approval.preapproval_request = 0
            else:
                approval.preapproval_request = 2
        else:
            print(status)
        approval.save()
        return Response("ok")


class FundingRequestsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        funding_requests = FundingRequest.objects.all().order_by('-updated_at')
        result = []
        for fitem in funding_requests:
            item = {
                "id": fitem.id,
                "created_at": fitem.created_at,
                "updated_at": fitem.updated_at,
                "status": fitem.status,
                "delivery_date": fitem.delivery_date,
                "salesperson_email": fitem.app.salesperson_email,
                "applicant": {
                    "id": fitem.app.applicant.id,
                    "name": fitem.app.applicant.name,
                    "email": fitem.app.applicant.email,
                    "address": fitem.app.applicant.street,
                    "zip": fitem.app.applicant.zip,
                    "city": fitem.app.applicant.city,
                    "state": fitem.app.applicant.state,
                    "phone": fitem.app.applicant.home_phone,
                    "dobY": fitem.app.applicant.dobY,
                    "dobM": fitem.app.applicant.dobM,
                    "dobD": fitem.app.applicant.dobD,
                    "ssn": fitem.app.applicant.ssn,
                    "dl": fitem.app.applicant.driver_license,
                    "nod": fitem.app.applicant.no_of_dependents
                },
                "products": []
            }
            if fitem.app.co_applicant != None:
                item["co_applicant"] = {
                    "id": fitem.app.co_applicant.id,
                    "name": fitem.app.co_applicant.name,
                    "email": fitem.app.co_applicant.email,
                    "phone": fitem.app.co_applicant.home_phone
                }
            products = Product.objects.filter(app=fitem.app)
            for product in products:
                item["products"].append({
                    "id": product.id,
                    "type": product.product_type,
                    "balance": product.balance(),
                    "period": product.finance_period
                })
            result.append(item)
        return Response(result)

    def post(self, request, *args, **kwargs):
        app_id = request.data.get('app_id')
        delivery_date = request.data.get('delivery_date')
        app = Application.objects.filter(id=app_id).first()
        funding = FundingRequest(
            app=app,
            created_at=datetime.date.today(),
            delivery_date=delivery_date
        )
        funding.save()
        return Response('ok')


class FundingRequestDetailView(APIView):
    def put(self, request, pk, *args, **kwargs):
        status = request.data.get('status')
        funding = FundingRequest.objects.get(id=pk)
        funding.status = status
        funding.save()
        app = Application.objects.get(id=funding.app_id)
        if status == 1:
            app.status = "funded"
        elif status == 2:
            app.status = "declined"

        app.save()
        return Response("ok")

    def get(self, request, pk, *args, **kwargs):
        funding_requests = FundingRequest.objects.get(id=pk)
        print(funding_requests)
        result = []
        for fitem in funding_requests:
            item = {
                "id": fitem.id,
                "created_at": fitem.created_at,
                "updated_at": fitem.updated_at,
                "status": fitem.status,
                "delivery_date": fitem.delivery_date,
                "applicant": {
                    "id": fitem.app.applicant.id,
                    "name": fitem.app.applicant.name,
                    "email": fitem.app.applicant.email,
                    "address": fitem.app.applicant.street,
                    "zip": fitem.app.applicant.zip,
                    "city": fitem.app.applicant.city,
                    "state": fitem.app.applicant.state,
                    "phone": fitem.app.applicant.home_phone,
                    "dobY": fitem.app.applicant.dobY,
                    "dobM": fitem.app.applicant.dobM,
                    "dobD": fitem.app.applicant.dobD,
                    "ssn": fitem.app.applicant.ssn,
                    "dl": fitem.app.applicant.driver_license,
                    "nod": fitem.app.applicant.no_of_dependents
                },
                "products": []
            }
            if fitem.app.co_applicant != None:
                item["co_applicant"] = {
                    "id": fitem.app.co_applicant.id,
                    "name": fitem.app.co_applicant.name,
                    "email": fitem.app.co_applicant.email,
                    "phone": fitem.app.co_applicant.home_phone
                }
            products = Product.objects.filter(app=fitem.app)
            for product in products:
                item["products"].append({
                    "id": product.id,
                    "type": product.product_type,
                    "balance": product.balance(),
                    "period": product.finance_period
                })
            result.append(item)
        return Response(result)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def PreapprovalRequest(request,pk):
    try:
        customer = Customer.objects.get(id = pk)
        preapprovals = Preapproval.objects.get(customer_id = customer.id)

        preapprovals.status = 0 #set to 0 for new preaproval request
        preapprovals.preapproval_request = 1
        preapprovals.save()
        return Response("ok")
    except Exception as e:
        print(e)
        return Response("Not updated",HTTP_400_BAD_REQUEST)
        pass


@api_view(['GET'])
def HelloSign(request):
    return get_all_signature_status()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def SendApproval(request):
    data = request.data

    if data is None:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)

    contact = data["contact"]
    main_app = contact["main_app"]
    co_app = contact["co_app"]
    co_enabled = contact["co_enabled"]
    co_complete = contact["co_complete"]
    co_separate = contact["co_separate"]
    product_type = contact["product_type"]

    main_customer = Customer(
        cif_number=main_app["cif_number"],
        nortridge_cif_number = main_app['nortridge_cif_number'],
        name=main_app["name"],
        email=main_app["email"],
        # dobY=main_app["dobY"],
        # dobM=main_app["dobM"],
        # dobD=main_app["dobD"],
        # ssn=main_app["ssn"],
        # driver_license=main_app["dl"],
        # no_of_dependents=main_app["nod"],
        cell_phone=main_app["cell_phone"],
        home_phone=main_app["home_phone"],
        street=main_app["street"],
        city=main_app["city"],
        state=main_app["state"],
        zip=main_app["zip"]
        # years_there_first=main_app["yt1"],
        # own_or_rent=main_app["own_or_rent"],
        # present_employer=main_app["present_employer"],
        # years_there_second=main_app["yt2"],
        # job_title=main_app["job_title"],
        # employer_phone=main_app["employer_phone"],
        # monthly_income=main_app["monthly_income"],
        # additional_income=main_app["additional_income"],
        # source=main_app["source"],
        # landlord_mortgage_holder=main_app["landlord_holder"],
        # monthly_rent_mortgage_payment=main_app["monthly_rent_payment"]
    )
    main_customer.save()
    application = Application(applicant=main_customer)
    application.salesperson_email = request.user.email

    if co_enabled == True:
        co_customer = Customer(
            name=co_app["name"],
            email=co_app["email"],
            # dobY=co_app["dobY"],
            # dobM=co_app["dobM"],
            # dobD=co_app["dobD"],
            # ssn=co_app["ssn"],
            # driver_license=co_app["dl"],
            # no_of_dependents=co_app["nod"],
            cell_phone=co_app["cell_phone"],
            home_phone=co_app["home_phone"],
            street=co_app["street"],
            city=co_app["city"],
            state=co_app["state"],
            zip=co_app["zip"]
            # years_there_first=co_app["yt1"],
            # own_or_rent=co_app["own_or_rent"],
            # present_employer=co_app["present_employer"],
            # years_there_second=co_app["yt2"],
            # job_title=co_app["job_title"],
            # employer_phone=co_app["employer_phone"],
            # monthly_income=co_app["monthly_income"],
            # additional_income=co_app["additional_income"],
            # source=co_app["source"],
            # landlord_mortgage_holder=co_app["landlord_holder"],
            # monthly_rent_mortgage_payment=co_app["monthly_rent_payment"]
        )
        co_customer.save()
        application.co_applicant = co_customer
        application.co_enabled = True
        application.status = "waiting"
        application.created_at = datetime.date.today()
        application.hello_sign_ref = "Email Not Sent"
        application.co_complete = co_complete
        application.co_separate = co_separate
        application.save()

        for product in product_type:
            print(product)
            approval = Preapproval(
                customer=main_customer,
                created_at=datetime.date.today(),
                product_type=product
            )
            approval.save()

        return Response('ok')
    else:
        application.co_enabled = False
        application.status = "waiting"
        application.created_at = datetime.date.today()
        application.hello_sign_ref = "Email Not Sent"
        application.co_complete = co_complete
        application.co_separate = co_separate
        application.save()

        for product in product_type:
            approval = Preapproval(
                customer=main_customer,
                app_id=application.id,
                created_at=datetime.date.today(),
                product_type=product
            )
            approval.save()
        return Response('ok')


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def CancelApprovalView(request):
    id = request.data.get('id')
    app = Application.objects.get(id=id)
    print(app.status)
    try:
        funding = FundingRequest.objects.get(id=app.id)
        print(funding.status)
        if funding.status == 1:
            return Response("False")
        else:
            app.status = "cancelled"
            app.save()
        Response("ok")
    except Exception as e:
        app.status = "cancelled"
        app.save()
        Response("ok")
    return Response("Ok")


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def Updateappstatus(request):
    id = request.data.get('id')
    status = request.data.get('status')
    rating = request.data.get('rating')
    message = request.data.get('message')
    page = request.data.get('page')

    app = Application.objects.get(id=id)
    if app == None:
        return Response("Invalid App Id", HTTP_400_BAD_REQUEST)
    if status == 'deleted':
        if page == "incomplete":
            res = delete_signature_request(app.hello_sign_ref)
            app.status = status
            app.save()
        else:
            app.status = status
            app.save()
    else:
        app.status = status
        app.rating = rating
        app.message = message
        app.save()
    return Response("Ok")


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def ReSendEmailView(request):
    data = request.data
    app_id = data["app_id"]
    applicant_email = data["applicant_email"]
    co_applicant_email = data["co_applicant_email"]
    order_type = data["order_type"]
    products = data["products"]
    cif_number = data["cif_number"]
    if cif_number == 0:
        app = Application.objects.get(id=app_id)
        app.applicant.email = applicant_email
        app.applicant.save()
        app.save()

        today = datetime.date.today()
        third_date = check_public_holiday(today + datetime.timedelta(days=3))
        if app.applicant.state == "ME":
            third_date = check_public_holiday(today + datetime.timedelta(days=12))

        custom_fields = [
            {"name": "buyer_name", "value": app.applicant.name},
            {"name": "buyer_address", "value": app.applicant.street},
            {"name": "buyer_city", "value": app.applicant.city},
            {"name": "buyer_state", "value": app.applicant.state},
            {"name": "buyer_zip", "value": app.applicant.zip},
            {"name": "buyer_phone", "value": app.applicant.home_phone},  # buyer_home_phone
            {"name": "third_date", "value": third_date.strftime("%m/%d/%Y")},
            {"name": "buyer_full_address",
             "value": app.applicant.street + ", " + app.applicant.city + ", " + app.applicant.state + ", " + app.applicant.zip}

        ]

        if order_type == 1:
            custom_fields.append({"name": "buyer_email", "value": app.applicant.email})
            # custom_fields.append({"name": "dobM", "value": app.applicant.dobM})
            # custom_fields.append({"name": "dobD", "value": app.applicant.dobD})
            # custom_fields.append({"name": "dobY", "value": app.applicant.dobY})
            # custom_fields.append({"name": "yt1", "value": app.applicant.years_there_first})
            # custom_fields.append({"name": "yt2", "value": app.applicant.years_there_second})
            # custom_fields.append({"name": "cell_phone", "value": app.applicant.cell_phone})
            # custom_fields.append({"name": "ssn", "value": app.applicant.ssn})
            # custom_fields.append({"name": "present_employer", "value": app.applicant.present_employer})
            # custom_fields.append({"name": "position", "value": app.applicant.job_title})
            # custom_fields.append({"name": "monthly_income", "value": app.applicant.monthly_income})
            # custom_fields.append({"name": "driver_license", "value": app.applicant.driver_license})
            # custom_fields.append({"name": "nod", "value": app.applicant.no_of_dependents})
            # custom_fields.append({"name": "other_income", "value": app.applicant.additional_income})
            # custom_fields.append({"name": "source", "value": app.applicant.source})
            # custom_fields.append({"name": "landlord_holder", "value": app.applicant.landlord_mortgage_holder})
            # custom_fields.append({"name": "monthly_rent", "value": app.applicant.monthly_rent_mortgage_payment})

        if app.co_enabled == True:
            app.co_applicant.email = co_applicant_email
            app.co_applicant.save()
            third_date = check_public_holiday(today + datetime.timedelta(days=3))
            if app.co_applicant.state == "ME":
                third_date = check_public_holiday(today + datetime.timedelta(days=12))
            custom_fields.append({"name": "co_third_date", "value": third_date.strftime("%m/%d/%Y")})

            if order_type == 1:
                custom_fields.append({"name": "co_name", "value": app.co_applicant.name})
                custom_fields.append({"name": "co_email", "value": app.co_applicant.email})
                custom_fields.append({"name": "co_address", "value": app.co_applicant.street})
                custom_fields.append({"name": "co_city", "value": app.co_applicant.city})
                custom_fields.append({"name": "co_state", "value": app.co_applicant.state})
                custom_fields.append({"name": "co_zip", "value": app.co_applicant.zip})
                custom_fields.append({"name": "co_phone", "value": app.co_applicant.home_phone})
                # custom_fields.append({"name": "co_home_phone", "value": app.co_applicant.home_phone})
                # custom_fields.append({"name": "co_dobM", "value": app.co_applicant.dobM})
                # custom_fields.append({"name": "co_dobD", "value": app.co_applicant.dobD})
                # custom_fields.append({"name": "co_dobY", "value": app.co_applicant.dobY})
                # custom_fields.append({"name": "co_yt1", "value": app.co_applicant.years_there_first})
                # custom_fields.append({"name": "co_yt2", "value": app.co_applicant.years_there_second})
                # custom_fields.append({"name": "co_cell_phone", "value": app.co_applicant.cell_phone})
                # custom_fields.append({"name": "co_ssn", "value": app.co_applicant.ssn})
                # custom_fields.append({"name": "co_present_employer", "value": app.co_applicant.present_employer})
                # custom_fields.append({"name": "co_position", "value": app.co_applicant.job_title})
                # custom_fields.append({"name": "co_monthly_income", "value": app.co_applicant.monthly_income})
                # custom_fields.append({"name": "co_driver_license", "value": app.co_applicant.driver_license})
                # custom_fields.append({"name": "co_nod", "value": app.co_applicant.no_of_dependents})
                # custom_fields.append({"name": "co_other_income", "value": app.co_applicant.additional_income})
                # custom_fields.append({"name": "co_source", "value": app.co_applicant.source})
                # custom_fields.append({"name": "co_landlord_holder", "value": app.co_applicant.landlord_mortgage_holder})
                # custom_fields.append({"name": "co_monthly_rent", "value": app.co_applicant.monthly_rent_mortgage_payment})

        products_count = len(products)
        template_id = ""
        if order_type == 1:
            if app.co_enabled == False:
                if products_count == 1:
                    template_id = "71deb1e2dad0d0a0f7dda94187274a70b0c42859"
                else:
                    template_id = "59f4b4f6beecdc1adf69b3f514254537e7df03e2"
            else:
                if app.co_complete == False:
                    if products_count == 1:
                        template_id = "c50646d726f8892cee46ec2b2695b68efe2a6d70"
                    else:
                        template_id = "2eed73d46c691102b93a6592486a05af25715113"
                else:
                    if app.co_separate == False:
                        if products_count == 1:
                            template_id = "ad4ccc1e4c23d1e92811a1dc1a0667151b0f247d"
                        else:
                            template_id = "d085baae4ac46ffd7359782cedf0b46bc03204a8"
                    else:
                        if products_count == 1:
                            template_id = "79597c3abf1aed2f90d778807fdd714041ba3714"
                        else:
                            template_id = "cba1acd7f1724f792decc49e49b32d445cb29a5b"
        elif order_type == 2:
            if app.co_enabled == False:
                if products_count == 1:
                    template_id = "1a3254cae49432e7f1eedb93c2cf00009dd14422"
                else:
                    template_id = "b1069d5dac0001f2b94cbf5c20c39b2274f114ea"
            else:
                if app.co_complete == False:
                    if products_count == 1:
                        template_id = "a0b37dfc5d3909a0d42f9c7a11553bd9adf5b672"
                    else:
                        template_id = "98642bf455ad62d7984ef8899a4389e8405d1f66"
                else:
                    if app.co_separate == False:
                        if products_count == 1:
                            template_id = "df05890933839a3d9879b4167b38ae907d135c57"
                        else:
                            template_id = "5a7bd4c90d262d667205f5151085014a9621210d"
                    else:
                        if products_count == 1:
                            template_id = "9529f3555e6ac8224e296f7a99c01267cbcb870e"
                        else:
                            template_id = "cfe9d26bdf7d1613530b9a23508d950189d1cb42"

        i = 0

        for product in products:
            product_q_obj = Product.objects.filter(app=app.id)  # get(app=app.id)
            print(product)
            for product in product_q_obj:
                if i == 0:
                    custom_fields.append({"name": "makemodel", "value": product.makemodel})
                    custom_fields.append({"name": "s_price", "value": "${:.2f}".format(product.net_price())})
                    custom_fields.append({"name": "s_tax", "value": "${:.2f}".format(product.tax)})
                    custom_fields.append({"name": "s_balance", "value": "${:.2f}".format(product.balance())})
                    custom_fields.append({"name": "s_down", "value": "${:.2f}".format(product.down_payment())})
                    custom_fields.append(
                        {"name": "s_cc", "value": "${:.2f} / ${:.2f}".format(product.cash_credit, product.check)})
                    custom_fields.append({"name": "s_unpaid", "value": "${:.2f}".format(product.unpaid_balance())})
                    custom_fields.append({"name": "s_monthly", "value": "${:.2f}".format(product.monthly_minimum())})

                    if product.product_type == "FOOD":
                        custom_fields.append({"name": "special", "value": '0% interest food order'})

                    if product.cash_credit != 0 or product.check != 0:
                        custom_fields.append({"name": "check_cc", "value": True})
                    else:
                        custom_fields.append({"name": "check_ach", "value": True})
                elif i == 1:
                    custom_fields.append({"name": "makemodel_2", "value": product.makemodel})
                    custom_fields.append({"name": "s_price_2", "value": "${:.2f}".format(product.net_price())})
                    custom_fields.append({"name": "s_tax_2", "value": "${:.2f}".format(product.tax)})
                    custom_fields.append({"name": "s_balance_2", "value": "${:.2f}".format(product.balance())})
                    custom_fields.append({"name": "s_down_2", "value": "${:.2f}".format(product.down_payment())})
                    custom_fields.append(
                        {"name": "s_cc_2", "value": "${:.2f} / ${:.2f}".format(product.cash_credit, product.check)})
                    custom_fields.append({"name": "s_unpaid_2", "value": "${:.2f}".format(product.unpaid_balance())})
                    custom_fields.append({"name": "s_monthly_2", "value": "${:.2f}".format(product.monthly_minimum())})

                    if product.product_type == "FOOD":
                        custom_fields.append({"name": "special_2", "value": '0% interest food order'})

                    if product.cash_credit != 0 or product.check != 0:
                        custom_fields.append({"name": "check_cc_2", "value": True})
                    else:
                        custom_fields.append({"name": "check_ach_2", "value": True})

            i = i + 1

        url = 'https://api.hellosign.com/v3/signature_request/send_with_template'

        payload = {}
        if app.co_enabled == False:
            message = "Dear " + app.applicant.name
            message += "\n\n"
            message += "Thank you for your interest in American Frozen Foods!\n\n"
            message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
            message += "Thank you for the opportunity to be of service!"
            payload = {
                "test_mode": 1,
                "title": "American Frozen Foods Documentation",
                "subject": "American Frozen Foods Documentation",
                "message": message,
                "template_id": template_id,
                "signers[buyer][name]": app.applicant.name,
                "signers[buyer][email_address]": app.applicant.email,
                "custom_fields": json.dumps(custom_fields)
            }
        else:
            print("Else")
            message = "Dear " + app.applicant.name
            message += " and " + app.co_applicant.name + "\n"
            message += "\n\n"
            message += "Thank you for your interest in American Frozen Foods!\n\n"
            message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
            message += "Thank you for the opportunity to be of service!"

            payload = {
                "test_mode": 1,
                "title": "American Frozen Foods Documentation",
                "subject": "American Frozen Foods Documentation",
                "message": message,
                "template_id": template_id,
                "signers[buyer][name]": app.applicant.name,
                "signers[buyer][email_address]": app.applicant.email,
                "signers[cobuyer][name]": app.co_applicant.name,
                "signers[cobuyer][email_address]": app.co_applicant.email,
                "custom_fields": json.dumps(custom_fields)
            }
        env = settings.EMAIL_HOST_USER
        if env == 'developer@dcg.dev':
            applicantEmail = applicant_email
            coApplicantEmail = co_applicant_email
            coApplicantEmail = coApplicantEmail if coApplicantEmail is not None else ''
            if sendEmailOkay(applicantEmail,coApplicantEmail):
                response = requests.post(url, data=payload, auth=HTTPBasicAuth(settings.HELLOSIGN_CLIENT_ID, ''))
                if response.status_code == 200:
                    data = response.json()

                    print(data['signature_request']['signature_request_id'],'............')
                    app.hello_sign_ref = data['signature_request']['signature_request_id']
                    app.save()
                else:
                    app.hello_sign_ref = "Email Not Sent"
                    app.save()
        else:
            response = requests.post(url, data=payload, auth=HTTPBasicAuth(settings.HELLOSIGN_CLIENT_ID, ''))
            if response.status_code == 200:
                data = response.json()

                print(data['signature_request']['signature_request_id'])
                app.hello_sign_ref = data['signature_request']['signature_request_id']
                app.save()
            else:
                app.hello_sign_ref = "Email Not Sent"
                app.save()

        return Response({
            'ok': True
        })
    else:

        app = Application.objects.get(id=app_id)
        main_customer = Customer.objects.get(id=app.applicant.id , cif_number=cif_number)
        if main_customer.email != applicant_email:
            result = delete_signature_request(app.hello_sign_ref)
        if co_applicant_email is not None:
            co_applicant_customer = Customer.objects.get(id=app.co_applicant_id)
            if co_applicant_customer.email != co_applicant_email:
                result = delete_signature_request(app.hello_sign_ref)
        #main_customer.name = main_app["name"]
        main_customer.email = applicant_email
        #main_customer.dobY = main_app["dobY"]
        #main_customer.dobM = main_app["dobM"]
        # main_customer.dobD = main_app["dobD"]
        # main_customer.ssn = main_app["ssn"]
        # main_customer.driver_license = main_app["dl"]
        # main_customer.no_of_dependents = main_app["nod"]
        # main_customer.cell_phone = main_app["cell_phone"]
        # main_customer.home_phone = main_app["home_phone"]
        # main_customer.street = main_app["street"]
        # main_customer.city = main_app["city"]
        # main_customer.state = main_app["state"]
        # main_customer.zip = main_app["zip"]
        # main_customer.years_there_first = main_app["yt1"]
        # main_customer.own_or_rent = main_app["own_or_rent"]
        # main_customer.present_employer = main_app["present_employer"]
        # main_customer.years_there_second = main_app["yt2"]
        # main_customer.job_title = main_app["job_title"]
        # main_customer.employer_phone = main_app["employer_phone"]
        # main_customer.monthly_income = main_app["monthly_income"]
        # main_customer.additional_income = main_app["additional_income"]
        # main_customer.source = main_app["source"]
        # main_customer.landlord_mortgage_holder = main_app["landlord_holder"]
        # main_customer.monthly_rent_mortgage_payment = main_app["monthly_rent_payment"]
        main_customer.save()
        app = Application.objects.get(applicant=main_customer)
        app.salesperson_email = request.user.email

        today = datetime.date.today()
        third_date = check_public_holiday(today + datetime.timedelta(days=3))
        if app.applicant.state == "ME":
            third_date = check_public_holiday(today + datetime.timedelta(days=12))

        custom_fields = [
            {"name": "buyer_name", "value": app.applicant.name},
            {"name": "buyer_address", "value": app.applicant.street},
            {"name": "buyer_city", "value": app.applicant.city},
            {"name": "buyer_state", "value": app.applicant.state},
            {"name": "buyer_zip", "value": app.applicant.zip},
            {"name": "buyer_phone", "value": app.applicant.home_phone},  # buyer_home_phone
            {"name": "third_date", "value": third_date.strftime("%m/%d/%Y")},
            {"name": "buyer_full_address",
             "value": app.applicant.street + ", " + app.applicant.city + ", " + app.applicant.state + ", " + app.applicant.zip}

        ]

        if order_type == 1:
            print(app.applicant.email)
            custom_fields.append({"name": "buyer_email", "value": app.applicant.email})
            # custom_fields.append({"name": "dobM", "value": app.applicant.dobM})
            # custom_fields.append({"name": "dobD", "value": app.applicant.dobD})
            # custom_fields.append({"name": "dobY", "value": app.applicant.dobY})
            # custom_fields.append({"name": "yt1", "value": app.applicant.years_there_first})
            # custom_fields.append({"name": "yt2", "value": app.applicant.years_there_second})
            # custom_fields.append({"name": "cell_phone", "value": app.applicant.cell_phone})
            # custom_fields.append({"name": "ssn", "value": app.applicant.ssn})
            # custom_fields.append({"name": "present_employer", "value": app.applicant.present_employer})
            # custom_fields.append({"name": "position", "value": app.applicant.job_title})
            # custom_fields.append({"name": "monthly_income", "value": app.applicant.monthly_income})
            # custom_fields.append({"name": "driver_license", "value": app.applicant.driver_license})
            # custom_fields.append({"name": "nod", "value": app.applicant.no_of_dependents})
            # custom_fields.append({"name": "other_income", "value": app.applicant.additional_income})
            # custom_fields.append({"name": "source", "value": app.applicant.source})
            # custom_fields.append({"name": "landlord_holder", "value": app.applicant.landlord_mortgage_holder})
            # custom_fields.append({"name": "monthly_rent", "value": app.applicant.monthly_rent_mortgage_payment})

        if app.co_enabled == True:
            app.co_applicant.email = co_applicant_email
            app.co_applicant.save()
            third_date = check_public_holiday(today + datetime.timedelta(days=3))
            if app.co_applicant.state == "ME":
                third_date = check_public_holiday(today + datetime.timedelta(days=12))
            custom_fields.append({"name": "co_third_date", "value": third_date.strftime("%m/%d/%Y")})

            if order_type == 1:
                custom_fields.append({"name": "co_name", "value": app.co_applicant.name})
                custom_fields.append({"name": "co_email", "value": app.co_applicant.email})
                custom_fields.append({"name": "co_address", "value": app.co_applicant.street})
                custom_fields.append({"name": "co_city", "value": app.co_applicant.city})
                custom_fields.append({"name": "co_state", "value": app.co_applicant.state})
                custom_fields.append({"name": "co_zip", "value": app.co_applicant.zip})
                custom_fields.append({"name": "co_phone", "value": app.co_applicant.home_phone})
                # custom_fields.append({"name": "co_home_phone", "value": app.co_applicant.home_phone})
                # custom_fields.append({"name": "co_dobM", "value": app.co_applicant.dobM})
                # custom_fields.append({"name": "co_dobD", "value": app.co_applicant.dobD})
                # custom_fields.append({"name": "co_dobY", "value": app.co_applicant.dobY})
                # custom_fields.append({"name": "co_yt1", "value": app.co_applicant.years_there_first})
                # custom_fields.append({"name": "co_yt2", "value": app.co_applicant.years_there_second})
                # custom_fields.append({"name": "co_cell_phone", "value": app.co_applicant.cell_phone})
                # custom_fields.append({"name": "co_ssn", "value": app.co_applicant.ssn})
                # custom_fields.append({"name": "co_present_employer", "value": app.co_applicant.present_employer})
                # custom_fields.append({"name": "co_position", "value": app.co_applicant.job_title})
                # custom_fields.append({"name": "co_monthly_income", "value": app.co_applicant.monthly_income})
                # custom_fields.append({"name": "co_driver_license", "value": app.co_applicant.driver_license})
                # custom_fields.append({"name": "co_nod", "value": app.co_applicant.no_of_dependents})
                # custom_fields.append({"name": "co_other_income", "value": app.co_applicant.additional_income})
                # custom_fields.append({"name": "co_source", "value": app.co_applicant.source})
                # custom_fields.append({"name": "co_landlord_holder", "value": app.co_applicant.landlord_mortgage_holder})
                # custom_fields.append({"name": "co_monthly_rent", "value": app.co_applicant.monthly_rent_mortgage_payment})

        products_count = len(products)
        template_id = ""
        if order_type == 1:
            if app.co_enabled == False:
                if products_count == 1:
                    template_id = "71deb1e2dad0d0a0f7dda94187274a70b0c42859"
                else:
                    template_id = "59f4b4f6beecdc1adf69b3f514254537e7df03e2"
            else:
                if app.co_complete == False:
                    if products_count == 1:
                        template_id = "c50646d726f8892cee46ec2b2695b68efe2a6d70"
                    else:
                        template_id = "2eed73d46c691102b93a6592486a05af25715113"
                else:
                    if app.co_separate == False:
                        if products_count == 1:
                            template_id = "ad4ccc1e4c23d1e92811a1dc1a0667151b0f247d"
                        else:
                            template_id = "d085baae4ac46ffd7359782cedf0b46bc03204a8"
                    else:
                        if products_count == 1:
                            template_id = "79597c3abf1aed2f90d778807fdd714041ba3714"
                        else:
                            template_id = "cba1acd7f1724f792decc49e49b32d445cb29a5b"
        elif order_type == 2:
            if app.co_enabled == False:
                if products_count == 1:
                    template_id = "1a3254cae49432e7f1eedb93c2cf00009dd14422"
                else:
                    template_id = "b1069d5dac0001f2b94cbf5c20c39b2274f114ea"
            else:
                if app.co_complete == False:
                    if products_count == 1:
                        template_id = "a0b37dfc5d3909a0d42f9c7a11553bd9adf5b672"
                    else:
                        template_id = "98642bf455ad62d7984ef8899a4389e8405d1f66"
                else:
                    if app.co_separate == False:
                        if products_count == 1:
                            template_id = "df05890933839a3d9879b4167b38ae907d135c57"
                        else:
                            template_id = "5a7bd4c90d262d667205f5151085014a9621210d"
                    else:
                        if products_count == 1:
                            template_id = "9529f3555e6ac8224e296f7a99c01267cbcb870e"
                        else:
                            template_id = "cfe9d26bdf7d1613530b9a23508d950189d1cb42"

        i = 0

        for product in products:
            product_q_obj = Product.objects.filter(app=app.id)  # get(app=app.id)
            print(product)
            for product in product_q_obj:
                if i == 0:
                    custom_fields.append({"name": "makemodel", "value": product.makemodel})
                    custom_fields.append({"name": "s_price", "value": "${:.2f}".format(product.net_price())})
                    custom_fields.append({"name": "s_tax", "value": "${:.2f}".format(product.tax)})
                    custom_fields.append({"name": "s_balance", "value": "${:.2f}".format(product.balance())})
                    custom_fields.append({"name": "s_down", "value": "${:.2f}".format(product.down_payment())})
                    custom_fields.append(
                        {"name": "s_cc", "value": "${:.2f} / ${:.2f}".format(product.cash_credit, product.check)})
                    custom_fields.append({"name": "s_unpaid", "value": "${:.2f}".format(product.unpaid_balance())})
                    custom_fields.append({"name": "s_monthly", "value": "${:.2f}".format(product.monthly_minimum())})

                    if product.product_type == "FOOD":
                        custom_fields.append({"name": "special", "value": '0% interest food order'})

                    if product.cash_credit != 0 or product.check != 0:
                        custom_fields.append({"name": "check_cc", "value": True})
                    else:
                        custom_fields.append({"name": "check_ach", "value": True})
                elif i == 1:
                    custom_fields.append({"name": "makemodel_2", "value": product.makemodel})
                    custom_fields.append({"name": "s_price_2", "value": "${:.2f}".format(product.net_price())})
                    custom_fields.append({"name": "s_tax_2", "value": "${:.2f}".format(product.tax)})
                    custom_fields.append({"name": "s_balance_2", "value": "${:.2f}".format(product.balance())})
                    custom_fields.append({"name": "s_down_2", "value": "${:.2f}".format(product.down_payment())})
                    custom_fields.append(
                        {"name": "s_cc_2", "value": "${:.2f} / ${:.2f}".format(product.cash_credit, product.check)})
                    custom_fields.append({"name": "s_unpaid_2", "value": "${:.2f}".format(product.unpaid_balance())})
                    custom_fields.append({"name": "s_monthly_2", "value": "${:.2f}".format(product.monthly_minimum())})

                    if product.product_type == "FOOD":
                        custom_fields.append({"name": "special_2", "value": '0% interest food order'})

                    if product.cash_credit != 0 or product.check != 0:
                        custom_fields.append({"name": "check_cc_2", "value": True})
                    else:
                        custom_fields.append({"name": "check_ach_2", "value": True})

            i = i + 1
        url = 'https://api.hellosign.com/v3/signature_request/send_with_template'

        if app.co_enabled == False:
            print('main_customer.email=',main_customer.email)
            message = "Dear " + main_customer.name
            message += "\n\n"
            message += "Thank you for your interest in American Frozen Foods!\n\n"
            message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
            message += "Thank you for the opportunity to be of service!"
            payload = {
                "test_mode": 1,
                "title": "American Frozen Foods Documentation",
                "subject": "American Frozen Foods Documentation",
                "message": message,
                "template_id": template_id,
                "signers[buyer][name]": main_customer.name,
                "signers[buyer][email_address]": main_customer.email,
                "custom_fields": json.dumps(custom_fields),
                "ccs[cc1][email_address]": "developer@dcg.dev"
                # "ccs[cc1][email_address]": "Billyrapp@yahoo.com",
                # "ccs[cc2][email_address]": "susan.treglia@yahoo.com",
                # "ccs[cc3][email_address]": "americanfoods5@gmail.com"
            }
        else:
            co_customer = Customer.objects.get(id = app.co_applicant_id)
            message = "Dear " + main_customer.name +  "\n"
            message += " and " + co_customer.name + "\n"
            message += "\n\n"
            message += "Thank you for your interest in American Frozen Foods!\n\n"
            message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
            message += "Thank you for the opportunity to be of service!"

            payload = {
                "test_mode": 1,
                "title": "American Frozen Foods Documentation",
                "subject": "American Frozen Foods Documentation",
                "message": message,
                "template_id": template_id,
                "signers[buyer][name]": main_customer.name,
                "signers[buyer][email_address]": main_customer.email,
                "signers[cobuyer][name]": co_customer.name,
                "signers[cobuyer][email_address]": co_applicant_email,
                "custom_fields": json.dumps(custom_fields),
                "ccs[cc1][email_address]": "developer@dcg.dev"
                # "ccs[cc1][email_address]": "Billyrapp@yahoo.com",
                # "ccs[cc2][email_address]": "susan.treglia@yahoo.com",
                # "ccs[cc3][email_address]": "americanfoods5@gmail.com"
            }
        env = settings.EMAIL_HOST_USER
        if env == 'developer@dcg.dev':
            applicantEmail = applicant_email
            coApplicantEmail = co_applicant_email
            coApplicantEmail = coApplicantEmail if coApplicantEmail is not None else ''
            if sendEmailOkay(applicantEmail,coApplicantEmail):
                response = requests.post(url, data=payload, auth=HTTPBasicAuth(settings.HELLOSIGN_CLIENT_ID, ''))
                print(response)

                if response.status_code == 200:
                    data = response.json()
                    print(data['signature_request']['signature_request_id'],'...........')
                    app.hello_sign_ref = data['signature_request']['signature_request_id']
                else:
                    app.hello_sign_ref = "Email Not Sent"

                app.save()
        else:
            response = requests.post(url, data=payload, auth=HTTPBasicAuth(settings.HELLOSIGN_CLIENT_ID, ''))
            print(response)

            if response.status_code == 200:
                data = response.json()
                print(data['signature_request']['signature_request_id'])
                app.hello_sign_ref = data['signature_request']['signature_request_id']
            else:
                app.hello_sign_ref = "Email Not Sent"

            app.save()



        # if preapproval_id != 0:
        #     approval = Preapproval.objects.get(id=preapproval_id)
        #     approval.status = 3
        #     approval.save()


        return Response({
            'ok': True
        })






@api_view(['POST'])
@permission_classes([IsAuthenticated])
def GetCustomersByCif(request):
    cif_number = request.data.get('cif_no')

    try:
        customer = getContact(cif_number)
        print(customer)
        result = {
            "cifno": customer['Cifno'],
            "nortridge_cif_number":customer['Cifnumber'],#TCP customer number
            "name": customer['Firstname1'],
            "lastname": customer['Lastname1'],
            "email": customer['Email'],
            "street": customer['Street_Address1'],
            "city": customer['City'],
            "state": customer['State'],
            "county": customer['County'],
            "zip": customer['Zip'],
            "cell_phone": customer['Cif_Phone_Nums'][0]['Phone_Raw'],
            "dob": customer['Dob'],
            "tin": customer['Tin'],
            "fulldata": customer
        }

        if len(customer['Cif_Phone_Nums']) > 1:
            result["home_phone"] = customer['Cif_Phone_Nums'][1]['Phone_Raw']
        else:
            print("Nothing")
        return Response(result)
    except Exception as e:
        print(e)
        return Response("Customer Not Found", HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def AppCountsView(request):
    counts = Application.objects.raw("""SELECT id,
count(CASE WHEN sa.status='waiting' and sa.hello_sign_ref !='Email Not Sent' THEN 1 END) as waiting ,
count(CASE WHEN sa.status='approved' THEN 1 END) as approved ,
count(CASE WHEN sa.status='declined' THEN 1 END) as declined ,
count(CASE WHEN sa.status='funded' THEN 1 END) as funded ,
count(CASE WHEN sa.status='cancelled' THEN 1 END) as cancelled,
count(CASE WHEN sa.status='waiting' and sa.hello_sign_ref ='Email Not Sent' THEN 1 END) as preapproval
FROM sales_application sa;""")
    result = {}
    for count in counts:
        result['counts'] = {
            "approved": count.approved,
            "declined": count.declined,
            "funded": count.funded,
            "cancelled": count.cancelled
        }
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def InCompleteCountsView(request):
    counts = Application.objects.raw("""SELECT id, sa.status as status, sa.hello_sign_ref as helloref FROM
                                            sales_application sa
                                            where sa.hello_sign_ref!='Email Not Sent' and sa.status='waiting';""")
    pending = 0
    incomplete = 0
    for count in counts:
        data = get_signature_status(count.helloref)
        total_signers = len(data)
        print("Total Signers", total_signers)
        if total_signers == 0:
            print("No Info Found for Hellosign")
            continue
        signed_count = 0
        for i in data:
            print(i['status_code'])
            if i['status_code'] == "signed":
                signed_count += 1

        if count.status == "waiting" and signed_count == total_signers:
            pending += 1
        else:
            incomplete += 1
    result = {
        "counts": {
            "pending": pending,
            "incomplete": incomplete
        }
    }

    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def PreapprovalCountsView(request):
    counts = Application.objects.raw(
        """SELECT id, count(*) as preapproval FROM sales_preapproval where status not in (3,4);""")
    result = {}
    for count in counts:
        result['counts'] = {
            "preapproval": count.preapproval
        }
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def AppslistView(request):
    status = request.data.get('status')
    # Case First Approved, Funded, Cancelled, Declined
    if status == "approved" or status == "funded" or status == "cancelled" or status == "declined":
        apps = Application.objects.filter(status=status).order_by('-updated_at')
        result = []
        for app in apps:
            customer = app.applicant
            item = {
                "id": app.id,
                "name": customer.name,
                "email": customer.email,
                "status": app.status,
                "city": customer.city,
                "street": customer.street,
                "state": customer.state,
                "zip": customer.zip,
                "co_customer": app.co_enabled,
                "salesperson_email": app.salesperson_email,
                "rating": app.rating,
                "message": app.message,
                "updated_at": app.updated_at,
                "created_at": app.created_at
            }
            try:
                if app.co_applicant.name is not None:
                    item["co_name"] = app.co_applicant.name
            except Exception as e:
                item["co_name"] = ""

            item_products = []
            products = Product.objects.filter(app=app)
            for product in products:
                item_products.append({
                    "id": product.id,
                    "type": product.product_type,
                    "balance": round(product.balance(), 2),
                    "monthly_minimum": round(product.monthly_minimum(), 2)
                })
            item["products"] = item_products
            result.append(item)
        return Response(result)
    # Case Pending
    elif status == "pending":
        apps = Application.objects.filter(status="waiting").exclude(hello_sign_ref='Email Not Sent').order_by('-updated_at')
        result = []
        for app in apps:
            customer = app.applicant
            item = {
                "id": app.id,
                "name": customer.name,
                "email": customer.email,
                "status": app.status,
                "city": customer.city,
                "street": customer.street,
                "state": customer.state,
                "zip": customer.zip,
                "co_customer": app.co_enabled,
                "salesperson_email": app.salesperson_email,
                "rating": app.rating,
                "message": app.message,
                "updated_at": app.updated_at,
                "created_at": app.created_at
            }

            try:
                if app.co_applicant.name is not None:
                    item["co_name"] = app.co_applicant.name
            except Exception as e:
                item["co_name"] = ""
            item_products = []
            products = Product.objects.filter(app=app)
            for product in products:
                item_products.append({
                    "id": product.id,
                    "type": product.product_type,
                    "balance": round(product.balance(), 2),
                    "monthly_minimum": round(product.monthly_minimum(), 2)
                })
            item["products"] = item_products
            data = get_signature_status(app.hello_sign_ref)
            total_signers = len(data)
            print("Total Signers", total_signers)
            if total_signers == 0:
                print("No Info Found for Hellosign")
                continue
            signed_count = 0
            for i in data:
                print(i['status_code'])
                if i['status_code'] == "signed":
                    signed_count += 1
            ###

            if signed_count == total_signers:
                item["hello_sign"] = data
                if item["status"] == "waiting":
                    item["status"] = "pending"
                result.append(item)
            else:
                print("Application is Incomplete")


            print(app.hello_sign_ref)
        return Response(result)
    # Case Incomplete
    elif status == "incomplete":
        apps = Application.objects.filter(status="waiting").order_by('-updated_at')#exclude(hello_sign_ref='Email Not Sent').
        result = []

        for app in apps:
            customer = app.applicant
            item = {
                "id": app.id,
                "name": customer.name,
                "email": customer.email,
                "status": app.status,
                "city": customer.city,
                "street": customer.street,
                "state": customer.state,
                "zip": customer.zip,
                "co_customer": app.co_enabled,
                "salesperson_email": app.salesperson_email,
                "rating": app.rating,
                "message": app.message,
                "updated_at": app.updated_at,
                "created_at": app.created_at
            }

            try:
                if app.co_applicant.name is not None:
                    item["co_name"] = app.co_applicant.name
            except Exception as e:
                item["co_name"] = ""
            item_products = []
            products = Product.objects.filter(app=app)
            for product in products:
                item_products.append({
                    "id": product.id,
                    "type": product.product_type,
                    "balance": round(product.balance(), 2),
                    "monthly_minimum": round(product.monthly_minimum(), 2)
                })
            item["products"] = item_products
            data = []
            if app.hello_sign_ref!= 'Email Not Sent':
                data = get_signature_status(app.hello_sign_ref)
            total_signers = len(data)
            print("Total Signers", total_signers)
            if data == []:
                item["hello_sign"] = data
                result.append(item)
            if total_signers == 0:
                print("No Info Found for Hellosign")
                continue
            signed_count = 0
            for i in data:
                print(i['status_code'])
                if i['status_code'] == "signed":
                    signed_count += 1

            if signed_count == total_signers:
                print("Application is Pending")
            else:
                item["hello_sign"] = data
                result.append(item)

                print("Application is Incomplete")
        return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetCustomernewView(request):
    customers = Application.objects.raw("""select  sc.id as id,
                                                    sc.name as name,
                                                    sc.email as email,
                                                    sc.street as street,
                                                    sc.city as city,
                                                    sc.state as state,
                                                    sc.zip as zip,
                                                    sc.cell_phone as cell_phone,
                                                    sc.home_phone as home_phone,
                                                    sc.dobM||'/'||sc.dobM||'/'||sc.dobY as dob,
                                                    sc.dobY as dobY,
                                                    sc.dobM as dobM,
                                                    sc.dobD as dobD,
                                                    sc.ssn as ssn,
                                                    sc.driver_license as dl,
                                                    sc.no_of_dependents as nod,
                                                    sc.years_there_first as yt1,
                                                    sc.years_there_second as yt2,
                                                    sc.own_or_rent as own_or_rent,
                                                    sc.present_employer as present_employer,
                                                    sc.job_title as job_title,
                                                    sc.employer_phone as employer_phone,
                                                    sc.monthly_income as monthly_income,
                                                    sc.additional_income as additional_income,
                                                    sc.source as source,
                                                    sc.landlord_mortgage_holder as landlord_mortgage_holder,
                                                    sc.monthly_rent_mortgage_payment as monthly_rent_payment,
                                                    sc.cif_number as cif_number,
                                                    scc.id as cid,
                                                    scc.name as cname,
                                                    scc.email as cemail,
                                                    scc.street as cstreet,
                                                    scc.city as ccity,
                                                    scc.state as cstate,
                                                    scc.zip as czip,
                                                    scc.cell_phone as ccell_phone,
                                                    scc.home_phone as chome_phone,
                                                    scc.dobM||'/'||sc.dobM||'/'||sc.dobY as cdob,
                                                    scc.dobY as cdobY,
                                                    scc.dobM as cdobM,
                                                    scc.dobD as cdobD,
                                                    scc.ssn as cssn,
                                                    scc.driver_license as cdl,
                                                    scc.no_of_dependents as cnod,
                                                    scc.years_there_first as cyt1,
                                                    scc.years_there_second as cyt2,
                                                    scc.own_or_rent as cown_or_rent,
                                                    scc.present_employer as cpresent_employer,
                                                    scc.job_title as cjob_title,
                                                    scc.employer_phone as cemployer_phone,
                                                    scc.monthly_income as cmonthly_income,
                                                    scc.additional_income as cadditional_income,
                                                    scc.source as csource,
                                                    scc.landlord_mortgage_holder as clandlord_mortgage_holder,
                                                    scc.monthly_rent_mortgage_payment as cmonthly_rent_payment,
                                                    sp.id as preid,
                                                    sp.status as prestatus,
                                                    sp.message as premessage,
                                                    sp.created_at as precreated_at,
                                                    sp.updated_at as preupdated_at,
                                                    sp.customer_id as precustomer_id,
                                                    sp.appliance as preappliance,
                                                    sp.product_type as preproduct_type,
                                                    sp.earliest_delivery_date as preearliest_delivery_date
                                                    from sales_application sa 
                                                    left join sales_customer sc 
                                                    on sa.applicant_id = sc.id
                                                    left join sales_customer scc on sa.co_applicant_id = scc.id
                                                    inner join sales_preapproval sp on sp.customer_id = sc.id 
                                                    where hello_sign_ref ='Email Not Sent'and sa.status != 'deleted' and sp.status not in (3,4) order by preupdated_at desc;""")
    result = []
    for customer in customers:
        preapprovals = Preapproval.objects.get(id = customer.preid)
        pre_req_id = preapprovals.preapproval_request
        pre_req = ''
        if pre_req_id == 0:
            pre_req = ''
        elif pre_req_id == 1:
            pre_req = 'requested for pre-approval'
        else:
            pre_req = 'admin decline'
        result.append({
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "street": customer.street,
            "city": customer.city,
            "state": customer.state,
            "zip": customer.zip,
            "cell_phone": customer.cell_phone,
            "home_phone": customer.home_phone,
            "dob": customer.dob,
            "dobY": customer.dobY,
            "dobM": customer.dobM,
            "dobD": customer.dobD,
            "ssn": customer.ssn,
            "dl": customer.dl,
            "nod": customer.nod,
            "yt1": customer.yt1,
            "yt2": customer.yt2,
            "own_or_rent": customer.own_or_rent,
            "present_employer": customer.present_employer,
            "job_title": customer.job_title,
            "employer_phone": customer.employer_phone,
            "monthly_income": customer.monthly_income,
            "additional_income": customer.additional_income,
            "source": customer.source,
            "landlord_holder": customer.landlord_mortgage_holder,
            "monthly_rent_payment": customer.monthly_rent_payment,
            "cif_number":customer.cif_number,
            "co_customer": {"id": customer.cid,
                            "name": customer.cname,
                            "email": customer.cemail,
                            "street": customer.cstreet,
                            "city": customer.ccity,
                            "state": customer.cstate,
                            "zip": customer.czip,
                            "cell_phone": customer.ccell_phone,
                            "home_phone": customer.chome_phone,
                            "dob": customer.cdob,
                            "dobY": customer.cdobY,
                            "dobM": customer.cdobM,
                            "dobD": customer.cdobD,
                            "ssn": customer.cssn,
                            "dl": customer.cdl,
                            "nod": customer.cnod,
                            "yt1": customer.cyt1,
                            "yt2": customer.cyt2,
                            "own_or_rent": customer.cown_or_rent,
                            "present_employer": customer.cpresent_employer,
                            "job_title": customer.cjob_title,
                            "employer_phone": customer.cemployer_phone,
                            "monthly_income": customer.cmonthly_income,
                            "additional_income": customer.cadditional_income,
                            "source": customer.csource,
                            "landlord_holder": customer.clandlord_mortgage_holder,
                            "monthly_rent_payment": customer.cmonthly_rent_payment},
            "preapproval": {"id": customer.preid,
                            "status": customer.prestatus,
                            "product_type": customer.preproduct_type,
                            "message": customer.premessage,
                            "created_at": customer.precreated_at,
                            "updated_at": customer.preupdated_at,
                            "appliance": customer.preappliance,
                            "earliest_delivery_date": customer.preearliest_delivery_date,
                            "customerid": customer.precustomer_id,
                            "pre_approvals_request_id": pre_req_id,
                            "pre_approvals_request": pre_req
                            }

        })
    return Response(result)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def PreapprovalDelete(request):
    id = request.data.get('id')
    approval = Preapproval.objects.get(id=id)
    if approval == None:
        return Response("Invalid App Id", HTTP_400_BAD_REQUEST)

    approval.status = 4
    approval.save()
    approval.customer
    return Response("Ok")


@api_view(['POST'])
@permission_classes([IsHellosignCallback])
@parser_classes([MultiPartParser])
def EventView(request):
    try:

        data = json.loads(request.data.get('json'))
        if data:
            status = log_hellosign_data(data)
            if status:
                return Response("Hello API Event Received")
    except Exception:
        pass

    return Response("Something went wrong", status=HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def NortridgeLoanDetail(request, pk):
    return Response(getContactloan(pk))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def NortridgeLoanPayment(request, pk):
    return Response(getPaymentHistory(pk))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def NortridgePaymentdue(request, pk):
    return Response(getPaymentDue(pk))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def NortridgePaymentinfo(request, pk):
    return Response(getPaymentinfo(pk))

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def HellosignReminder(request, pk):
    app = Application.objects.get(id=pk)
    email = request.data.get('email')

    if app is None:
        return Response("Invalid App Id", HTTP_400_BAD_REQUEST)

    hellosign_ref = app.hello_sign_ref
    response = send_reminder(hellosign_ref, email)
    if response == "ok":
        return Response(response)
    else:
        return Response({'detail': "Reminder already sent for this ID, Please try after 1 hour."}, HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def AppCredict(request):
    customer_email = request.data.get('customer_email')
    customer_phone = request.data.get('customer_phone')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    name = request.data.get('name')
    street = request.data.get('street')
    city = request.data.get('city')
    state = request.data.get('state')
    zip_code = request.data.get('zip_code')
    action = request.data.get('action')
    # dealer company info
    user = User.objects.get(email=request.user.email)
    company = Company.objects.get(id=user.dealer_company_id)

    if action is None:
        return Response({
            'status': 'error',
            'message': 'Action attribute is missing.',
            'ok': False,
            'error': 'Action attribute is missing.'
        }, HTTP_400_BAD_REQUEST)

    if action == 'ondevice':
        print(action)
        #all_field_data = model_to_dict(customer, fields=[field.name for field in customer._meta.fields])

        return Response({
                            'status': 'success',
                            'ok': True,
                            'message': 'Customer’s details have been saved.',
                            'data':request.data
                        })
    elif action == 'onlink':
        customer = Customer.objects.filter(email=customer_email, cell_phone=customer_phone).first()
        if customer is None:
            customer = Customer(email=customer_email, cell_phone=customer_phone)
            customer.save()
        customer.first_name = first_name
        customer.last_name = last_name
        customer.name = name
        customer.cell_phone = customer_phone
        customer.street = street
        customer.city = city
        customer.state = state
        customer.zip = zip_code
        customer.save()
        credit_application = CreditApplication(credit_app=customer)
        credit_application.status = 'link_sent'
        credit_application.save()
        result = send_link_email(customer_email, customer.id , customer_phone, company.name,customer_email+str(customer.id), user.email)
        return Response({
            'status': 'success',
            'ok': result,
            'message': 'Mail has been sent.'
        })
    elif action == 'save&exit':
        customer = Customer.objects.filter(email=customer_email, cell_phone=customer_phone).first()
        if customer is None:
            customer = Customer(email=customer_email, cell_phone=customer_phone)
            customer.save()
        customer.first_name = first_name
        customer.last_name = last_name
        customer.name = name
        customer.cell_phone = customer_phone
        customer.street = street
        customer.city = city
        customer.state = state
        customer.zip = zip_code
        customer.save()

        return Response({
            'status': 'success',
            'ok': True,
            'message': 'Data saved.'
        })


    else:
        return Response({
            'status': 'error',
            'ok': False,
            'message': 'action attribute is not correct.'
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def AppCredictDetails(request):
    data = request.data
    contact = data["contact"]
    main_app = contact["main_app"]
    co_app = contact["co_app"]
    co_enabled = contact["co_enabled"]
    co_complete = contact["co_complete"]
    co_separate = contact["co_separate"]
    existing_id = contact["id"]
    if existing_id is not None and existing_id !=0:
        main_customer = Customer.objects.get(id = existing_id)
        main_customer.name = main_app["name"]
        main_customer.email = main_app["email"]
        main_customer.dobY = main_app["dobY"]
        main_customer.dobM = main_app["dobM"]
        main_customer.dobD = main_app["dobD"]
        main_customer.ssn = main_app["ssn"]
        main_customer.driver_license = main_app["driver_license"]
        main_customer.no_of_dependents = main_app["no_of_dependents"]
        main_customer.cell_phone = main_app["cell_phone"]
        #main_customer.home_phone = main_app["home_phone"]
        main_customer.street = main_app["street"]
        main_customer.city = main_app["city"]
        main_customer.state = main_app["state"]
        main_customer.zip = main_app["zip"]
        main_customer.years_there_first = main_app["years_there_first"]
        main_customer.own_or_rent = main_app["own_or_rent"]
        main_customer.present_employer = main_app["present_employer"]
        main_customer.years_there_second = main_app["years_there_second"]
        main_customer.job_title = main_app["job_title"]
        main_customer.employer_phone = main_app["employer_phone"]
        main_customer.monthly_income = main_app["monthly_income"]
        main_customer.additional_income = main_app["additional_income"]
        main_customer.source = main_app["source"]
        main_customer.landlord_mortgage_holder = main_app["landlord_mortgage_holder"]
        main_customer.monthly_rent_mortgage_payment = main_app["monthly_rent_mortgage_payment"]
        main_customer.employement_status = main_app['employement_status']
        main_customer.first_name = main_app['first_name']
        main_customer.last_name = main_app['last_name']
        main_customer.save()
        #dealer company info
        user = User.objects.get(email=request.user.email)
        company = Company.objects.get(id=user.dealer_company_id)
        print(company.contact_type,company.contact_code)

        main_customer.cif_number = '158'+str(main_customer.id)#createContact(main_customer)
        main_customer.save()
        credit_application = None
        try:
            credit_application = CreditApplication.objects.get(credit_app_id = main_customer.id)#(credit_app = main_customer)
            credit_application.salesperson_email = request.user.email
            #credit_application.save()
        except:
            credit_application = CreditApplication(credit_app=main_customer)
            credit_application.salesperson_email = request.user.email



        co_enabled = contact["co_enabled"]
        if co_enabled == True:
            co_customer = None
            try:
                co_customer = Customer.objects.get(id=credit_application.credit_co_app_id)
            except:
                co_customer = Customer(email = co_app["email"], cell_phone = co_app['cell_phone'])
                co_customer.save()
            co_customer.name = co_app["name"]
            co_customer.email = co_app["email"]
            co_customer.dobY = co_app["dobY"]
            co_customer.dobM = co_app["dobM"]
            co_customer.dobD = co_app["dobD"]
            co_customer.ssn = co_app["ssn"]
            co_customer.driver_license = co_app["driver_license"]
            co_customer.no_of_dependents = co_app["no_of_dependents"]
            co_customer.cell_phone = co_app["cell_phone"]
            #co_customer.home_phone = co_app["home_phone"]
            co_customer.street = co_app["street"]
            co_customer.city = co_app["city"]
            co_customer.state = co_app["state"]
            co_customer.zip = co_app["zip"]
            co_customer.years_there_first = co_app["years_there_first"]
            co_customer.own_or_rent = co_app["own_or_rent"]
            co_customer.present_employer = co_app["present_employer"]
            co_customer.years_there_second = co_app["years_there_second"]
            co_customer.job_title = co_app["job_title"]
            co_customer.employer_phone = co_app["employer_phone"]
            co_customer.monthly_income = co_app["monthly_income"]
            co_customer.additional_income = co_app["additional_income"]
            co_customer.source = co_app["source"]
            co_customer.landlord_mortgage_holder = co_app["landlord_mortgage_holder"]
            co_customer.monthly_rent_mortgage_payment = co_app["monthly_rent_mortgage_payment"]
            co_customer.employement_status = co_app['employement_status']
            co_customer.first_name = co_app['first_name']
            co_customer.last_name = co_app['last_name']
            co_customer.save()

            co_customer.cif_number = '158'+str(co_customer.id)#createContact(co_customer)
            co_customer.save()

            credit_application.credit_co_app = co_customer
            credit_application.co_enabled = True

        credit_application.status = "completed"
        credit_application.created_at = datetime.date.today()
        credit_application.save()
        send_invite_email(main_customer.email,'User', company.name, main_customer.name)
        both_user = main_customer.name
        if co_enabled == True:
            send_invite_email(co_customer.email, 'User', company.name, co_customer.name)
            both_user = both_user + '&' + co_customer.name
        send_invite_email(settings.EMAIL_HOST_USER, 'Admin', company.name, both_user)



        return Response({
            'status': 'success',
            'message': 'Application Updated Successfully ',
            'ok': True
        })
    elif existing_id == 0:
        main_customer = Customer(email = main_app["email"], cell_phone = main_app["cell_phone"])
        main_customer.save()
        main_customer.name = main_app["name"]
        #main_customer.email = main_app["email"]
        main_customer.dobY = main_app["dobY"]
        main_customer.dobM = main_app["dobM"]
        main_customer.dobD = main_app["dobD"]
        main_customer.ssn = main_app["ssn"]
        main_customer.driver_license = main_app["driver_license"]
        main_customer.no_of_dependents = main_app["no_of_dependents"]
        main_customer.cell_phone = main_app["cell_phone"]
        #main_customer.home_phone = main_app["home_phone"]
        main_customer.street = main_app["street"]
        main_customer.city = main_app["city"]
        main_customer.state = main_app["state"]
        main_customer.zip = main_app["zip"]
        main_customer.years_there_first = main_app["years_there_first"]
        main_customer.own_or_rent = main_app["own_or_rent"]
        main_customer.present_employer = main_app["present_employer"]
        main_customer.years_there_second = main_app["years_there_second"]
        main_customer.job_title = main_app["job_title"]
        main_customer.employer_phone = main_app["employer_phone"]
        main_customer.monthly_income = main_app["monthly_income"]
        main_customer.additional_income = main_app["additional_income"]
        main_customer.source = main_app["source"]
        main_customer.landlord_mortgage_holder = main_app["landlord_mortgage_holder"]
        main_customer.monthly_rent_mortgage_payment = main_app["monthly_rent_mortgage_payment"]
        main_customer.employement_status = main_app['employement_status']
        main_customer.first_name = main_app['first_name']
        main_customer.last_name = main_app['last_name']
        main_customer.save()
        # dealer company info
        user = User.objects.get(email=request.user.email)
        company = Company.objects.get(id=user.dealer_company_id)
        print(company.contact_type, company.contact_code)

        main_customer.cif_number = '158'+str(main_customer.id)#createContact(main_customer)
        main_customer.save()
        credit_application = CreditApplication(credit_app=main_customer)
        credit_application.salesperson_email = request.user.email

        co_enabled = contact["co_enabled"]
        if co_enabled == True:
            co_customer = Customer(
                name=co_app["name"],
                email=co_app["email"],
                dobY=co_app["dobY"],
                dobM=co_app["dobM"],
                dobD=co_app["dobD"],
                ssn=co_app["ssn"],
                driver_license=co_app["driver_license"],
                no_of_dependents=co_app["no_of_dependents"],
                cell_phone=co_app["cell_phone"],
                street=co_app["street"],
                city=co_app["city"],
                state=co_app["state"],
                zip=co_app["zip"],
                years_there_first=co_app["years_there_first"],
                own_or_rent=co_app["own_or_rent"],
                present_employer=co_app["present_employer"],
                years_there_second=co_app["years_there_second"],
                job_title=co_app["job_title"],
                employer_phone=co_app["employer_phone"],
                monthly_income=co_app["monthly_income"],
                additional_income=co_app["additional_income"],
                source=co_app["source"],
                landlord_mortgage_holder=co_app["landlord_mortgage_holder"],
                monthly_rent_mortgage_payment=co_app["monthly_rent_mortgage_payment"],
                employement_status=co_app['employement_status'],
                first_name=co_app['first_name'],
                last_name=co_app['last_name']
            )
            co_customer.save()
            co_customer.cif_number = '158'+str(co_customer.id)#createContact(co_customer)
            co_customer.save()

            credit_application.credit_co_app = co_customer
            credit_application.co_enabled = True

        credit_application.status = "completed"
        credit_application.created_at = datetime.date.today()
        credit_application.save()

        send_invite_email(main_customer.email,'User', company.name, main_customer.name)
        both_user = main_customer.name
        if co_enabled == True:
            send_invite_email(co_customer.email, 'User', company.name, co_customer.name)
            both_user = both_user + '&' + co_customer.name
        send_invite_email(settings.EMAIL_HOST_USER, 'Admin', company.name, both_user)

        return Response({
            'status': 'success',
            'message': 'Application Submitted Successfully. ',
            'ok': True
        })
    else:
        return Response({
            'status': 'error',
            'message': 'Customer Not Found. ',
            'ok':False
        })


@api_view(['POST'])
def AppCredictDetailsonLink(request):
    data = request.data
    contact = data["contact"]
    main_app = contact["main_app"]
    co_app = contact["co_app"]
    co_enabled = contact["co_enabled"]
    co_complete = contact["co_complete"]
    co_separate = contact["co_separate"]
    existing_id = contact["id"]
    salesperson_email = contact['salesperson_email']
    token = contact['token']
    if existing_id is not None and existing_id !=0:

        main_customer = Customer.objects.get(id = existing_id)
        digest = main_customer.email+str(existing_id)
        digest_token = hashlib.sha512(digest.encode())
        digest_token = digest_token.hexdigest()
        print(digest_token, '==', token)
        if digest_token != token:
            return Response({
                'status': 'error',
                'message': 'Authentication failure',
                'ok': False
            })
        main_customer.name = main_app["name"]
        main_customer.email = main_app["email"]
        main_customer.dobY = main_app["dobY"]
        main_customer.dobM = main_app["dobM"]
        main_customer.dobD = main_app["dobD"]
        main_customer.ssn = main_app["ssn"]
        main_customer.driver_license = main_app["driver_license"]
        main_customer.no_of_dependents = main_app["no_of_dependents"]
        main_customer.cell_phone = main_app["cell_phone"]
        #main_customer.home_phone = main_app["home_phone"]
        main_customer.street = main_app["street"]
        main_customer.city = main_app["city"]
        main_customer.state = main_app["state"]
        main_customer.zip = main_app["zip"]
        main_customer.years_there_first = main_app["years_there_first"]
        main_customer.own_or_rent = main_app["own_or_rent"]
        main_customer.present_employer = main_app["present_employer"]
        main_customer.years_there_second = main_app["years_there_second"]
        main_customer.job_title = main_app["job_title"]
        main_customer.employer_phone = main_app["employer_phone"]
        main_customer.monthly_income = main_app["monthly_income"]
        main_customer.additional_income = main_app["additional_income"]
        main_customer.source = main_app["source"]
        main_customer.landlord_mortgage_holder = main_app["landlord_mortgage_holder"]
        main_customer.monthly_rent_mortgage_payment = main_app["monthly_rent_mortgage_payment"]
        main_customer.employement_status = main_app['employement_status']
        main_customer.first_name = main_app['first_name']
        main_customer.last_name = main_app['last_name']
        main_customer.save()
        #dealer company info
        user = User.objects.get(email=salesperson_email)
        company = Company.objects.get(id=user.dealer_company_id)
        print(company.contact_type,company.contact_code)

        main_customer.cif_number = '158'+str(main_customer.id)#createContact(main_customer)
        main_customer.save()
        credit_application = None
        try:
            credit_application = CreditApplication.objects.get(credit_app_id = main_customer.id)#(credit_app = main_customer)
            credit_application.salesperson_email = salesperson_email
            #credit_application.save()
        except Exception as e:
            print(e)
            credit_application = CreditApplication(credit_app=main_customer)
            credit_application.salesperson_email = salesperson_email



        co_enabled = contact["co_enabled"]
        if co_enabled == True:
            co_customer = None
            try:
                co_customer = Customer.objects.get(id=credit_application.credit_co_app_id)
            except:
                co_customer = Customer(email = co_app["email"], cell_phone = co_app['cell_phone'])
                co_customer.save()
            co_customer.name = co_app["name"]
            co_customer.email = co_app["email"]
            co_customer.dobY = co_app["dobY"]
            co_customer.dobM = co_app["dobM"]
            co_customer.dobD = co_app["dobD"]
            co_customer.ssn = co_app["ssn"]
            co_customer.driver_license = co_app["driver_license"]
            co_customer.no_of_dependents = co_app["no_of_dependents"]
            co_customer.cell_phone = co_app["cell_phone"]
            #co_customer.home_phone = co_app["home_phone"]
            co_customer.street = co_app["street"]
            co_customer.city = co_app["city"]
            co_customer.state = co_app["state"]
            co_customer.zip = co_app["zip"]
            co_customer.years_there_first = co_app["years_there_first"]
            co_customer.own_or_rent = co_app["own_or_rent"]
            co_customer.present_employer = co_app["present_employer"]
            co_customer.years_there_second = co_app["years_there_second"]
            co_customer.job_title = co_app["job_title"]
            co_customer.employer_phone = co_app["employer_phone"]
            co_customer.monthly_income = co_app["monthly_income"]
            co_customer.additional_income = co_app["additional_income"]
            co_customer.source = co_app["source"]
            co_customer.landlord_mortgage_holder = co_app["landlord_mortgage_holder"]
            co_customer.monthly_rent_mortgage_payment = co_app["monthly_rent_mortgage_payment"]
            co_customer.employement_status = co_app['employement_status']
            co_customer.first_name = co_app['first_name']
            co_customer.last_name = co_app['last_name']
            co_customer.save()

            co_customer.cif_number = '158'+str(co_customer.id)#createContact(co_customer)
            co_customer.save()

            credit_application.credit_co_app = co_customer
            credit_application.co_enabled = True

        credit_application.status = "completed"
        credit_application.created_at = datetime.date.today()
        credit_application.save()

        send_invite_email(main_customer.email,'User', company.name, main_customer.name)
        both_user = main_customer.name
        if co_enabled == True:
            send_invite_email(co_customer.email, 'User', company.name, co_customer.name)
            both_user = both_user + '&' + co_customer.name
        send_invite_email(settings.EMAIL_HOST_USER, 'Admin', company.name, both_user)




        return Response({
            'status': 'success',
            'message': 'Application Updated Successfully ',
            'ok': True
        })

    else:
        return Response({
            'status': 'error',
            'message': 'Customer Not Found. ',
            'ok':False
        })
