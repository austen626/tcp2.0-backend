from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from .models import Invites
from .models import Company
from authy.api import AuthyApiClient
from accounts.models import User
from quickemailverification import Client as QEVClient
import secrets

authy_api = AuthyApiClient(settings.AUTHY_API_KEY)
qev_api = QEVClient(settings.QEV_API_KEY)


@api_view(['POST'])
def RegisterView(request):
    email = request.data.get('email')
    password = request.data.get('password')
    phone = request.data.get('phone')
    if email is None or password is None or phone is None:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email=email).first()

    if user is not None:
        return Response({
            'ok': False,
            'error': 'User {} is already exist'.format(email)
        }, HTTP_400_BAD_REQUEST)

    user = User.objects.filter(phone=phone).first()

    if user is not None:
        return Response({
            'ok': False,
            'error': '{} has been registered already'.format(phone)
        }, HTTP_400_BAD_REQUEST)

    authy_user = authy_api.users.create(email=email, country_code=1, phone=phone)

    if not authy_user.ok():
        return Response({
            'ok': False,
            'error': 'Error while creating user'
        }, HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(email, authy_user.id, password, phone=phone, )

    sms = authy_api.users.request_sms(authy_user.id, {
        'force': True
    })

    return Response({
        'ok': True,
        'data': {
            'authy_id': authy_user.id,
            'ending': phone[-4:]
        }
    })


@api_view(['POST'])
def RegisterVerifyView(request):
    authy_id = request.data.get('authy_id')
    code = request.data.get('code')
    if authy_id is None or code is None:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)

    verification = authy_api.tokens.verify(authy_id, token=code)
    if not verification.ok():
        return Response({
            'ok': False,
            'error': 'Verificatin Code is not correct'
        }, HTTP_400_BAD_REQUEST)

    user = User.objects.get(authy_id=authy_id)
    user.active = True
    user.save()

    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'ok': True,
        'token': token.key
    })


@api_view(['POST'])
def LoginView(request):
    email = request.data.get("email")
    password = request.data.get("password")
    remember_device_check = request.data.get("check")

    if email is None or password is None or remember_device_check is None:
        return Response({
            'ok': False,
            'error': 'Please provide both email and password'
        }, status=HTTP_400_BAD_REQUEST)

    user = authenticate(username=email, password=password)

    if not user:
        return Response({
            'ok': False,
            'error': 'Please check your credentials'
        }, status=HTTP_400_BAD_REQUEST)

    if not user.account_status:
        return Response({
            'ok': False,
            'error': 'User Account Not Available or Deleted'
        }, status=HTTP_400_BAD_REQUEST)

    if remember_device_check == "true":
        user = User.objects.get(authy_id=user.authy_id)
        user.active = True
        user.last_login = timezone.now()
        user.save()
        # Create token
        token, _ = Token.objects.get_or_create(user=user)

        role = []
        if user.is_sales:
            role.append('sales')
        if user.is_dealer:
            role.append('dealer')
        if user.is_admin:
            role.append('admin')

        return Response({
            'ok': True,
            'token': token.key,
            'avatar': user.avatar,
            'role': role
        })
    else:
        sms = authy_api.users.request_sms(user.authy_id, {
            'force': True
        })
        print(sms.response)

        return Response({
            'ok': True,
            'data': {
                'authy_id': user.authy_id,
                'ending': user.phone[-4:]
            }
        })


@api_view(['POST'])
def LoginVerifyView(request):
    authy_id = request.data.get('authy_id')
    code = request.data.get('code')
    if authy_id is None or code is None:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)
    verification = authy_api.tokens.verify(authy_id, token=code)
    if not verification.ok():
        return Response({
            'ok': False,
            'error': 'Verificatin Code is not correct'
        }, HTTP_400_BAD_REQUEST)

    user = User.objects.get(authy_id=authy_id)
    token, _ = Token.objects.get_or_create(user=user)

    role = []
    if user.is_sales:
        role.append('sales')
    if user.is_dealer:
        role.append('dealer')
    if user.is_admin:
        role.append('admin')

    result = {
        'ok': True,
        'token': token.key,
        'avatar': user.avatar,
        'role': role
    }

    return Response(result)


@api_view(['POST'])
def SendAgainView(request):
    authy_id = request.data.get("authy_id")

    if authy_id is None:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, status=HTTP_400_BAD_REQUEST)

    sms = authy_api.users.request_sms(authy_id, {
        'force': True
    })

    return Response({
        'ok': True
    })


@api_view(['POST'])
def ResetView(request):
    email = request.data.get("email")
    phone = request.data.get('phone')

    if email is None:
        return Response({
            'ok': False,
            'error': 'Email is required'
        }, status=HTTP_400_BAD_REQUEST)

    if phone is None:
        return Response({
            'ok': False,
            'error': 'Phone Number is required'
        }, status=HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email=email).first()
    if not user.account_status:
        return Response({
            'ok': False,
            'error': 'User Account Not Available or Deleted'
        }, status=HTTP_400_BAD_REQUEST)

    if user is None:
        return Response({
            'ok': False,
            'error': 'User {} does not exist'.format(email)
        }, status=HTTP_404_NOT_FOUND)

    if user.phone != phone:
        return Response({
            'ok': False,
            'error': 'Incorrect Phone Number'.format(phone)
        }, status=HTTP_404_NOT_FOUND)
    else:
        sms = authy_api.users.request_sms(user.authy_id, {
            'force': True
        })
        return Response({
            'ok': True,
            'data': {
                'authy_id': user.authy_id
            }
        })


@api_view(['POST'])
def ResetVerifyView(request):
    authy_id = request.data.get('authy_id')
    code = request.data.get('code')
    if authy_id is None or code is None:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)

    verification = authy_api.tokens.verify(authy_id, token=code)
    if not verification.ok():
        return Response({
            'ok': False,
            'error': 'Verification Code is not correct'
        }, HTTP_400_BAD_REQUEST)

    user = User.objects.get(authy_id=authy_id)
    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'ok': True,
        'token': token.key
    })


@api_view(['POST'])
def ResetPasswordView(request):
    email = request.data.get('email')
    password = request.data.get('password')
    forgot_token = request.data.get('forgot_token')
    if password is None:
        return Response({
            'ok': False,
            'error': 'New Password is required'
        }, HTTP_400_BAD_REQUEST)

    if email is None:
        return Response({
            'ok': False,
            'error': 'Email is required'
        }, HTTP_400_BAD_REQUEST)

    if forgot_token is None:
        return Response({
            'ok': False,
            'error': 'Forgot Token is required'
        }, HTTP_400_BAD_REQUEST)

    user = User.objects.get(email=email)
    if user.pass_token == forgot_token:
        user.set_password(password)
        user.pass_token = None
        user.save()
        return Response({
            'ok': True,
            'message': 'Password Changed Successfully'
        })
    else:
        return Response({
            'ok': False,
            'error': 'Session has been expired'
        }, HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def CodeVerifyView(request):
    authy_id = request.data.get('authy_id')
    code = request.data.get('code')
    if authy_id is None or code is None:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)

    verification = authy_api.tokens.verify(authy_id, token=code)
    if not verification.ok():
        return Response({
            'ok': False,
            'error': 'Verification Code is not correct'
        }, HTTP_400_BAD_REQUEST)

    user = User.objects.get(authy_id=authy_id)
    user.active = True
    user.last_login = timezone.now()
    user.save()

    token, _ = Token.objects.get_or_create(user=user)

    role = []
    if user.is_sales:
        role.append('sales')
    if user.is_dealer:
        role.append('dealer')
    if user.is_admin:
        role.append('admin')

    return Response({
        'ok': True,
        'token': token.key,
        'avatar': user.avatar,
        'role': role
    })


@api_view(['POST'])
def CodeVerifyForgotView(request):
    authy_id = request.data.get('authy_id')
    code = request.data.get('code')
    if authy_id is None or code is None:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)

    verification = authy_api.tokens.verify(authy_id, token=code)
    if not verification.ok():
        return Response({
            'ok': False,
            'error': 'Verification Code is not correct'
        }, HTTP_400_BAD_REQUEST)

    forgot_token = secrets.token_hex(32)
    user = User.objects.get(authy_id=authy_id)
    user.pass_token = forgot_token
    user.save()

    return Response({
        'ok': True,
        'forgot_token': forgot_token
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def GetMe(request):
    user = request.user
    role = []
    if user.is_sales:
        role.append('sales')
    if user.is_dealer:
        role.append('dealer')
    if user.is_admin:
        role.append('admin')

    return Response({
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "role": role
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def UserView(request):
    user = request.user
    users = User.objects.filter(dealer_company=user.dealer_company).exclude(account_status=False)
    result = []
    for user in users:
        role = []
        if user.is_sales:
            role.append('sales')
        if user.is_dealer:
            role.append('dealer')
        if user.is_admin:
            role.append('admin')
        result.append({
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "avatar": user.avatar,
            "phone": user.phone,
            "role": role,
            "company": user.dealer_company.name,
            "status": user.account_status,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "contact_email":user.contact_email,
            "street": user.street,
            "city":user.city,
            "state":user.state,
            "zip":user.zip
        })

    return Response(result)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def UserDeleteView(request, pk):
    user = User.objects.get(id=pk)
    if user == None:
        return Response("Invalid User Id", HTTP_400_BAD_REQUEST)
    user.account_status = False
    user.save()
    return Response({'User Deleted Successfully': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ChangePass(request):
    currentpassword = request.data.get('currentpassword')
    newpassword = request.data.get('newpassword')
    if currentpassword is None or newpassword is None:
        return Response({
            'ok': False,
            'error': 'New Password or Old Password is required'
        }, HTTP_400_BAD_REQUEST)

    user = request.user
    print(user.password)

    if authenticate(username=user.email, password=currentpassword):
        user.set_password(newpassword)
        user.save()
        return Response({
            'Password Changed Successfully': True
        })
    else:
        return Response({
            'Incorrect Password': False
        })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def ChangeProfile(request):
    email = request.data.get('email')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    if email is None or first_name is None or last_name is None:
        return Response({'ok': False, 'error': 'email, first_name, last_name field is mandatory'}, HTTP_400_BAD_REQUEST)
    user = request.user
    print(user.email)
    user.email = email
    user.last_name = last_name
    user.first_name = first_name
    user.save()
    return Response({
        'Profile Updated Successfully': True
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ValidateEmail(request):
    email = request.data.get('email')
    response = {"status": False}

    if email is None:
        return Response({'status': False, 'error': 'email field is mandatory'}, HTTP_400_BAD_REQUEST)
    elif email.isnumeric() or '@' not in email or '.' not in email:
        return Response(response, HTTP_400_BAD_REQUEST)

    try:
        qev = qev_api.quickemailverification()
        qev_response = qev.verify(email)
        if qev_response.code == 200:
            qev_json = qev_response.body
            if qev_json.get('result', '') == 'valid' and qev_json.get('disposable', '') == 'false':
                response['status'] = True
    except Exception as e:
        pass

    if not response['status']:
        return Response(response, HTTP_400_BAD_REQUEST)
    return Response(response)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def UserInviteView(request):
    email = request.data.get('email')
    user_role = request.data.get('role')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    response = {"status": False, "message": "Invalid Email"}
    if email is None or user_role is None:
        return Response({'status': False, 'message': 'email and staff type is mandatory'}, HTTP_400_BAD_REQUEST)
    elif email.isnumeric() or '@' not in email or '.' not in email:
        return Response(response, HTTP_400_BAD_REQUEST)

    try:
        qev = qev_api.quickemailverification()
        qev_response = qev.verify(email)
        if qev_response.code == 200:
            qev_json = qev_response.body
            if qev_json.get('result', '') == 'valid' and qev_json.get('disposable', '') == 'false':
                response['status'] = True
    except Exception as e:
        pass
    user = User.objects.filter(email=email).first()
    if user is not None:
        return Response({
            'status': False,
            'message': 'User {} is already registered'.format(email)
        }, HTTP_400_BAD_REQUEST)

    if not response['status']:
        return Response(response, HTTP_400_BAD_REQUEST)
    else:
        try:
            invite = Invites.objects.get(email=email, token_status=True)
        except Invites.DoesNotExist:
            invite = None

        if invite is not None:
            # Setting Old Token Status False as De-active
            invite.token_status = False
            invite.save()

            # Generating new token and  new record in the table
            invite_token = secrets.token_hex(32)
            invited_user = Invites(email=email,
                                   user_role=user_role,
                                   invite_token=invite_token,
                                   token_status=True,
                                   generated_by=request.user.email,
                                   dealer_company=request.user.dealer_company,
                                   first_name=first_name,
                                   last_name=last_name)
            invited_user.save()
            # Send Email Invite
            send_invite_email(email, invite_token, request.user.dealer_company.name, user_role)
            response['message'] = "ok"
            return Response(response)
        else:
            invite_token = secrets.token_hex(32)
            invited_user = Invites(email=email,
                                   user_role=user_role,
                                   invite_token=invite_token,
                                   token_status=True,
                                   generated_by=request.user.email,
                                   dealer_company=request.user.dealer_company,
                                   first_name = first_name,
                                   last_name = last_name)
            invited_user.save()
            # Send Email Invite
            send_invite_email(email, invite_token, request.user.dealer_company.name, user_role)
            response['message'] = "ok"
            return Response(response)


def send_invite_email(email, invite_token, dealer_company, user_role):
    if email is None:
        return False
    emails = [email]
    subject = "TCP User Invitation"
    message = "Dear User,\n\n"
    message += "You have received an invitation from "+dealer_company+" to create an account with Travis Capital Partners.\nPlease click the link below to set up your account:\n\n"
    message += settings.INVITE_TOKEN_URL+invite_token+"&role="+user_role+"&email="+email
    message += "\n\nThanks!\nTravis Capital Partners"

    from_email = settings.DEFAULT_EMAIL_FROM
    html_message = ""
    msg = EmailMultiAlternatives(subject, message, from_email, emails)
    if html_message:
        msg.attach_alternative(html_message, 'text/html')
    msg.send()
    return True
def send_invite_email_dealer(email, invite_token, dealer_company, user_role):
    if email is None:
        return False
    emails = [email]
    subject = "TCP User Invitation"
    message = "Dear User,\n\n"
    message += "You have received an invitation from "+dealer_company+" to create an account with Travis Capital Partners.\nPlease click the link below to set up your account:\n\n"
    message += settings.INVITE_TOKEN_URL_ADMIN+invite_token+"&role="+user_role+"&email="+email
    message += "\n\nThanks!\nTravis Capital Partners"

    from_email = settings.DEFAULT_EMAIL_FROM
    html_message = ""
    msg = EmailMultiAlternatives(subject, message, from_email, emails)
    if html_message:
        msg.attach_alternative(html_message, 'text/html')
    msg.send()
    return True


@api_view(['POST'])
def UserInviteRegisterView(request):
    email = request.data.get('email')
    password = request.data.get('password')
    phone = request.data.get('phone')
    invite_token = request.data.get('invite_token')
    role = request.data.get('role')
    #first_name = request.data.get('first_name')
    #last_name = request.data.get('last_name')
    if email is None or password is None or phone is None or invite_token is None or role is None :
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email=email).first()
    if user is not None:
        return Response({
            'ok': False,
            'error': 'User {} is already exist'.format(email)
        }, HTTP_400_BAD_REQUEST)
    user = User.objects.filter(phone=phone).first()

    if user is not None:
        return Response({
            'ok': False,
            'error': '{} has been registered already'.format(phone)
        }, HTTP_400_BAD_REQUEST)

    try:
        invite = Invites.objects.get(email=email, token_status=True)
        if invite.invite_token == invite_token and invite.user_role == role:
            pass
        else:
            invite = None
    except Invites.DoesNotExist:
        invite = None

    if invite is not None:
        authy_user = authy_api.users.create(email=email, country_code=1, phone=phone)
        if not authy_user.ok():
            return Response({'ok': False, 'error': 'Please check your mobile number'}, HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(email, authy_user.id, password, phone=phone, )
        user.last_name = invite.last_name
        user.first_name = invite.first_name
        user.dealer_company = invite.dealer_company
        if role == "dealer":
            user.dealer = True
            user.save()
        user.save()
        sms = authy_api.users.request_sms(authy_user.id, {'force': True})
        invite.token_status = False
        invite.save()
        return Response({'ok': True, 'data': {'authy_id': authy_user.id, 'ending': phone[-4:]}})
    else:
        return Response({'ok': False, 'error': 'Invite Token Expired or Invalid Invite Token '}, HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def AddDealer(request):
    user = request.user
    response = {}
    if user.is_admin:
        dealer_email = request.data.get('dealer_email')
        dealer_company_name = request.data.get('dealer_company_name')
        dealer_contact_email = request.data.get('dealer_contact_email')
        dealer_phone = request.data.get('dealer_phone')
        dealer_address_street = request.data.get('dealer_address_street')
        dealer_address_city = request.data.get('dealer_address_city')
        dealer_address_state = request.data.get('dealer_address_state')
        dealer_address_zipcode = request.data.get('dealer_address_zipcode')

        if dealer_email is None or dealer_phone is None:
            return Response({
                'ok': False,
                'error': 'Invalid Request'
            }, HTTP_400_BAD_REQUEST)
        elif dealer_email.isnumeric() or '@' not in dealer_email or '.' not in dealer_email:
            return Response({
                'ok': False,
                'error': 'Invalid Email id'
            }, HTTP_400_BAD_REQUEST)
        old_user = User.objects.filter(email=dealer_email).first()
        if old_user is not None:
            return Response({
                'ok': False,
                'error': 'User {} is already exist'.format(dealer_email)
            }, HTTP_400_BAD_REQUEST)
        old_user = User.objects.filter(phone=dealer_phone).first()
        if old_user is not None:
            return Response({
                'ok': False,
                'error': 'User {} is already exist'.format(dealer_phone)
            }, HTTP_400_BAD_REQUEST)
        authy_user = authy_api.users.create(email=dealer_email, country_code=1, phone=dealer_phone)
        if not authy_user.ok():
            return Response({
                'ok': False,
                'error': 'Error while creating user'
            }, HTTP_400_BAD_REQUEST)

        try:
            qev = qev_api.quickemailverification()
            qev_response = qev.verify(dealer_email)
            if qev_response.code == 200:
                qev_json = qev_response.body
                if qev_json.get('result', '') == 'valid' and qev_json.get('disposable', '') == 'false':
                    response['ok'] = True
        except Exception as e:
            pass

        user = User.objects.create_user(dealer_email, authy_user.id, phone=dealer_phone )
        #user.dealer_company.name = dealer_company_name
        user.contact_email = dealer_contact_email
        user.street = dealer_address_street
        user.city = dealer_address_city
        user.state = dealer_address_state
        user.zip = dealer_address_zipcode
        user.dealer = True
        user.save()
        company = Company(name = dealer_company_name)
        company.save()
        user.dealer_company_id = company.id
        user.save()

        # sms = authy_api.users.request_sms(authy_user.id, {
        #     'force': True
        # })
        invite_token = secrets.token_hex(32)
        invited_user = Invites(email=dealer_email,
                               user_role='dealer',
                               invite_token=invite_token,
                               token_status=True,
                               generated_by=request.user.email,
                               dealer_company=company)
        invited_user.save()
        # Send Email Invite
        send_invite_email(dealer_email, invite_token, dealer_company_name, 'dealer')
        response['message'] = "Invite email has been sent"
        return Response(response)

    else:
        return Response({'ok':False})

@api_view(['POST'])
def RegisterDealerVerify(request):
    email = request.data.get('email')
    password = request.data.get('password')
    phone = request.data.get('phone')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    invite_token = request.data.get('invite_token')
    if email is None or password is None or phone is None:
        return Response({
            'ok': False,
            'error': 'Invalid Request'
        }, HTTP_400_BAD_REQUEST)
    invite = Invites.objects.get(email= email, invite_token = invite_token, token_status = True)
    if invite is not None:
        user = User.objects.get(email=email)
        user.set_password(password)
        user.active = True
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        invite.token_status = False
        invite.save()
        sms = authy_api.users.request_sms(user.authy_id, {'force': True})
        print(sms)
        return Response({
            'ok': True,
            'data': {
                'authy_id': user.authy_id,
                'ending': user.phone[-4:]
            }
        })

    else:
        return Response({'ok': False})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def DealerList(request):
    user = request.user
    dealers_data_response = []
    if user.is_admin:
        dealers_data = User.objects.filter(dealer= True, account_status= True).order_by('-id')#, active = True
        for dealer in dealers_data:
            role = []
            if dealer.is_sales:
                role.append('sales')
            if dealer.is_dealer:
                role.append('dealer')
            if dealer.is_admin:
                role.append('admin')
            data = {}
            data['id'] = dealer.id
            data['company_name'] = dealer.dealer_company.name
            data['email'] = dealer.email
            data['contact_email'] = dealer.contact_email
            data['phone'] = dealer.phone
            data['is_sales'] = dealer.is_sales
            data['is_active'] = dealer.is_active
            data['street'] = dealer.street
            data['city'] = dealer.city
            data['state'] = dealer.state
            data['zip'] = dealer.zip
            data['role'] = role
            dealers_data_response.append(data)
        return Response({'ok':True,'data':dealers_data_response})
    else:
        return Response({'ok':False,'data':''})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def UpdateStaff(request):
    req_user = request.user
    if req_user.is_admin:
        db_id = request.data.get('id')
        company_name = request.data.get('company_name')
        email = request.data.get('email')
        contact_email = request.data.get('contact_email')
        phone = request.data.get('phone')
        street = request.data.get('street')
        city = request.data.get('city')
        state = request.data.get('state')
        zip = request.data.get('zip')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        roles = request.data.get('role')
        updated_email = request.data.get('updated_email')
        updated_phone = request.data.get('updated_phone')
        db_user_email = User.objects.get(email=updated_email)
        db_user_mob = User.objects.get(phone=updated_phone)
        if db_user_email is None and db_user_mob is None :
            dealer_user = User.objects.get(id = db_id)
            dealer_company_id = dealer_user.dealer_company_id
            company = Company.objects.get(id=dealer_company_id)
            company.name = company_name
            company.save()
            dealer_user.email = updated_email
            dealer_user.contact_email = contact_email
            dealer_user.phone = updated_phone
            dealer_user.street = street
            dealer_user.city = city
            dealer_user.state = state
            dealer_user.zip = zip
            dealer_user.first_name = first_name
            dealer_user.last_name = last_name
            dealer_user.save()
            if roles is not None or roles!=[]:
                for r in roles:
                    if r == 'sales':
                        dealer_user.sales = True
                    elif r == 'dealer':
                        dealer_user.dealer = True
                dealer_user.save()
            return Response({'ok': True, 'message': 'User Updated Successfully.'})
        elif email == updated_email :
            dealer_user = User.objects.get(id=db_id)
            dealer_company_id = dealer_user.dealer_company_id
            company = Company.objects.get(id=dealer_company_id)
            company.name = company_name
            company.save()
            #dealer_user.email = updated_email
            dealer_user.contact_email = contact_email
            #dealer_user.phone = updated_phone
            dealer_user.street = street
            dealer_user.city = city
            dealer_user.state = state
            dealer_user.zip = zip
            dealer_user.first_name = first_name
            dealer_user.last_name = last_name
            dealer_user.save()
            if roles is not None or roles!=[]:
                for r in roles:
                    if r == 'sales':
                        dealer_user.sales = True
                    elif r == 'dealer':
                        dealer_user.dealer = True
                dealer_user.save()
            return Response({'ok': True, 'message': 'User Updated Successfully.'})
        elif phone == updated_phone:
            dealer_user = User.objects.get(id=db_id)
            dealer_company_id = dealer_user.dealer_company_id
            company = Company.objects.get(id=dealer_company_id)
            company.name = company_name
            company.save()
            #dealer_user.email = updated_email
            dealer_user.contact_email = contact_email
            #dealer_user.phone = updated_phone
            dealer_user.street = street
            dealer_user.city = city
            dealer_user.state = state
            dealer_user.zip = zip
            dealer_user.first_name = first_name
            dealer_user.last_name = last_name
            dealer_user.save()
            if roles is not None or roles!=[]:
                for r in roles:
                    if r == 'sales':
                        dealer_user.sales = True
                    elif r == 'dealer':
                        dealer_user.dealer = True
                dealer_user.save()
            return Response({'ok': True, 'message': 'User Updated Successfully.'})

        else:
            return Response({'ok': False, 'message': 'Email/Phone is in use'})
    elif req_user.is_dealer:
        db_id = request.data.get('id')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        roles = request.data.get('role')
        if email is None or roles is None:
            return Response({'ok': False, 'message': 'email and staff type is mandatory'}, HTTP_400_BAD_REQUEST)
        elif email.isnumeric() or '@' not in email or '.' not in email:
            return Response({'ok': False, 'message': 'email is not correct.'}, HTTP_400_BAD_REQUEST)
        user = User.objects.filter(email=email).exclude(id = db_id).first()
        if user is not None:
            return Response({
                'status': False,
                'message': 'User {} is already in use'.format(email)
            }, HTTP_400_BAD_REQUEST)
        user = User.objects.get(id = db_id)
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        for r in roles:
            if r == 'sales':
                user.sales = True
            elif r == 'dealer':
                user.dealer = True
        user.save()
        return Response({'ok': True, 'message': 'User Updated Successfully.'})
    else:
        return Response({'ok': True, 'message': 'User don not have permission to Update'})



















