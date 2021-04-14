from django.urls import path, include

from .views import *

urlpatterns = [
    path('send-signature', SendSignatureView),
    path('apps', AppsView),
    path('app/<int:pk>', AppByIdView),
    path('apps-nohello', Appsnohello),

    path('search-customer-local', SearchCustomerViewLocal),
    path('search-customer-nortridge', SearchCustomerViewNortridge),
    path('customer/<int:pk>', GetCustomerByIdView),
    path('customers', GetCustomersView),
    path('customer-cif', GetCustomersByCif),

    path('preapprovals', PreapprovalsView.as_view()),
    path('preapproval/<int:pk>', PreapprovalDetailView.as_view()),
    path('preapprovalrequest/<int:pk>', PreapprovalRequest),

    path('fundingrequests', FundingRequestsView.as_view()),
    path('fundingrequest/<int:pk>', FundingRequestDetailView.as_view()),

    path('hellosign', HelloSign),
    path('sendpreapproval', SendApproval),
    path('cancelapp', CancelApprovalView),
    path('appstatuschange', Updateappstatus),
    path('resendemail', ReSendEmailView),

    path('counts-app', AppCountsView),
    path('counts-incomplete', InCompleteCountsView),
    path('counts-preapproval', PreapprovalCountsView),
    path('apps-list', AppslistView),
    path('customersnew', GetCustomernewView),
    path('preapproval-delete', PreapprovalDelete),
    path('hellosign-reminder/<int:pk>', HellosignReminder),

    path('events', EventView),

    # Nortridge APIs
    path('nortridge-loandetail/<int:pk>', NortridgeLoanDetail),
    path('nortridge-loanpayment/<int:pk>', NortridgeLoanPayment),
    path('nortridge-loanpaymentdue/<int:pk>', NortridgePaymentdue),
    path('nortridge-loanpaymentinfo/<int:pk>', NortridgePaymentinfo)

]
