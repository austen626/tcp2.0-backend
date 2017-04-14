from datetime import datetime
from hellosign_sdk import HSClient
from django.conf import settings
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from django.core.exceptions import ObjectDoesNotExist

from sales.models import HelloSignResponse, HelloSignLog

from .utils import get_hellosign_event_hash, verify_hash, get_status_from_hellosign_event

client = HSClient(api_key=settings.HELLOSIGN_CLIENT_ID)


def get_or_none(classmodel, **kwargs):
    try:
        return classmodel.objects.get(**kwargs)
    except ObjectDoesNotExist:
        return


def log_hellosign_data(data):
    # get event parameters
    event = data.get('event', {})

    event_time = event.get('event_time')
    event_type = event.get('event_type')
    event_hash = event.get('event_hash')

    # get event hash
    request_hash = get_hellosign_event_hash(settings.HELLOSIGN_CLIENT_ID, event_time, event_type)

    # check event hash
    if verify_hash(request_hash, event_hash):
        # parse data
        signature_request = data.get('signature_request', {})
        if signature_request:

            signature_request_id = signature_request.get('signature_request_id')
            status = get_status_from_hellosign_event(event_type)

            for signature in signature_request.get('signatures', []):

                signature_id = signature.get('signature_id')

                # store in DB
                if status and signature:
                    hellosign_response = get_or_none(HelloSignResponse, signature_request_id=signature_request_id,
                                                     signature_id=signature_id)
                    if hellosign_response:
                        hellosign_response.status_code = status
                        hellosign_response.signed_at = signature.get('signed_at')
                        hellosign_response.last_viewed_at = signature.get('last_viewed_at')
                        hellosign_response.last_reminded_at = signature.get('last_reminded_at')
                        hellosign_response.has_pin = signature.get('has_pin')
                        hellosign_response.order = signature.get('order')
                        hellosign_response.signer_email_address = signature.get('signer_email_address')
                        hellosign_response.signer_name = signature.get('signer_name')
                        hellosign_response.signer_role = signature.get('signer_role')

                        hellosign_response.save()
                    else:
                        hellosign_response = HelloSignResponse(
                            signature_request_id=signature_request_id,
                            has_pin=signature.get('has_pin'),
                            last_reminded_at=signature.get('last_reminded_at'),
                            last_viewed_at=signature.get('last_viewed_at'),
                            order=signature.get('order'),
                            signature_id=signature_id,
                            signed_at=signature.get('signed_at'),
                            signer_email_address=signature.get('signer_email_address'),
                            signer_name=signature.get('signer_name'),
                            signer_role=signature.get('signer_role'),
                            status_code=status
                        )
                        hellosign_response.save()

                event_log = HelloSignLog(signature_request_id=signature_request_id,
                                         signature_id=signature_id,
                                         status=event_type,
                                         response=data)
                event_log.save()
            return True
    return


# Get Application Signed Information using Request ID
def get_signature_status(sig_request_id):
    if sig_request_id is None:
        return []
    result = []

    try:
        # Data From Local Database
        localdata = HelloSignResponse.objects.filter(signature_request_id=sig_request_id)
        for data in localdata:
            result.append({
                "signature_id": data.signature_id,
                "signer_email": data.signer_email_address,
                "signer_name": data.signer_name,
                "signer_role": data.signer_role,
                "order": data.order,
                "status_code": data.status_code,
                "signed_at": data.signed_at,
                "last_viewed_at": data.last_viewed_at,
                "last_reminded_at": data.last_reminded_at,
                "has_pin": data.has_pin,
            })

    except Exception as e:

        # Real time data from Hellosign
        data = client.get_signature_request(sig_request_id)
        for i in range(len(data.signatures)):
            result.append({
                "signature_id": data.signatures[i].signature_id,
                "signer_email": data.signatures[i].signer_email_address,
                "signer_name": data.signatures[i].signer_name,
                "signer_role": data.signatures[i].signer_role,
                "order": data.signatures[i].order,
                "status_code": data.signatures[i].status_code,
                "signed_at": data.signatures[i].signed_at,
                "last_viewed_at": data.signatures[i].last_viewed_at,
                "last_reminded_at": data.signatures[i].last_reminded_at,
                "has_pin": data.signatures[i].has_pin,
            })


    return result


# Get all Signature list at once
def get_all_signature_status():
    signature_request_list = client.get_signature_request_list()
    print("numresult", signature_request_list.num_results)
    print("page", signature_request_list.page)
    print("pagesize", signature_request_list.page_size)
    print("numpages", signature_request_list.num_pages)
    response = {}
    for page in range(signature_request_list.num_pages):
        print("Page number ", page)
        signature_request_list = client.get_signature_request_list(page=page)
        for sign in signature_request_list:
            # print("Sign Details", sign)
            # print("Checking signature detail exist if exist delete and inserting new value")
            existrequest = HelloSignResponse.objects.filter(signature_request_id=sign.signature_request_id)
            existrequest.delete()
            for s in sign.signatures:
                print(sign.signature_request_id, s.signature_id, s.signer_name, s.status_code)
                hello_sign = HelloSignResponse(
                    signature_request_id=sign.signature_request_id,
                    has_pin=s.has_pin,
                    last_reminded_at=s.last_reminded_at,
                    last_viewed_at=s.last_viewed_at,
                    order=s.order,
                    signature_id=s.signature_id,
                    signed_at=s.signed_at,
                    signer_email_address=s.signer_email_address,
                    signer_name=s.signer_name,
                    signer_role=s.signer_role,
                    status_code=s.status_code
                )
                hello_sign.save()
    return Response(response)


# Send Signature with Templates
def send_signature_with_template(payload):
    signers = [
        {"name": "Jack", "email_address": "jack@example.com"},
        {"name": "Jill", "email_address": "jill@example.com"}
    ]
    ccs = [
        {"email_address": "lawyer@hellosign.com", "role_name": "Lawyer 1"},
        {"email_address": "lawyer@example.com", "role_name": "Lawyer 2"}
    ]
    custom_fields = [
        {"Field 1": "Value 1"},
        {"Field 2": "Value 2"}
    ]

    data = client.send_signature_request_with_template(
        test_mode=payload['test_mode'],
        template_id=payload['template_id'],
        title=payload['title'],
        subject=payload['subject'],
        message=payload['message'],
        signing_redirect_url=None,
        signers=payload['signers'],
        ccs=payload['ccs'],
        custom_fields=payload['custom_fields'])

    response = {
        "signature_id": data.signatures[0].signature_id,
        "signer_email": data.signatures[0].signer_email_address,
        "signer_name": data.signatures[0].signer_name,
        "signer_role": data.signatures[0].signer_role,
        "order": data.signatures[0].order,
        "status_code": data.signatures[0].status_code,
        "signed_at": data.signatures[0].signed_at,
        "last_viewed_at": data.signatures[0].last_viewed_at,
        "last_reminded_at": data.signatures[0].last_reminded_at,
        "has_pin": data.signatures[0].has_pin,
    }
    return response


def getpdfdoc(signaturerequestid):
    res = client.get_signature_request_file(
        signature_request_id=signaturerequestid,
        filename=signaturerequestid + '.pdf',
        file_type='pdf'
    )
    from django.http import FileResponse
    return FileResponse(open('file.pdf', 'rb'))


def send_reminder(signature_request_id, email):
    try:
        res = client.remind_signature_request(
            signature_request_id=signature_request_id,
            email_address=email
        )
        return "ok"
    except Exception as e:
        return "Error"


# Delete Incomplete Signature Requests
def delete_signature_request(signature_request_id):
    try:
        res = client.cancel_signature_request(signature_request_id)
        print("Incomplete Request Deleted")
        return "ok"
    except Exception as e:
        return "Error"

def sendEmailOkay(applicantEmail, coApplicantEmail):
    allowed_email = ['matt@traviscapitalpartners.com', 'mrappnyc@gmail.com', 'dcg.dev']
    if applicantEmail in allowed_email or coApplicantEmail in allowed_email or applicantEmail.find(allowed_email[-1])!=-1 or coApplicantEmail.find(allowed_email[-1]) != -1:

        return True
    else:

        return False
