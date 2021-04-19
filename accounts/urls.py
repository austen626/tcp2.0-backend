from django.urls import path

from .views import *

urlpatterns = [
    path('register', RegisterView),
    path('register-verify', RegisterVerifyView),
    path('login', LoginView),
    path('login-verify', LoginVerifyView),
    path('reset-verify', ResetVerifyView),
    path('send-again', SendAgainView),
    path('code-verify', CodeVerifyView),
    path('me', GetMe),
    path('change-password', ChangePass),
    path('update-profile', ChangeProfile),
    path('validate-email', ValidateEmail),
    # Forgot Password APIs
    path('reset', ResetView),
    path('code-verify-forgot', CodeVerifyForgotView),
    path('reset-password', ResetPasswordView),
    # Staff Management APIs
    path('users', UserView),
    path('user-delete/<int:pk>', UserDeleteView),
    path('invite', UserInviteView),
    path('invite-register', UserInviteRegisterView),
    path('update-user', UpdateUser),

    #create dealer
    path('add-dealer', AddDealer),
    path('register_dealer', RegisterDealerVerify),
    path('list-dealer', DealerList),
    path('update-dealer', UpdateDealer),


]
