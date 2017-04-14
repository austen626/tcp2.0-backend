# from requests.auth import HTTPBasicAuth
# import requests
# url = 'https://api.hellosign.com/v3/signature_request/send_with_template'
# message = "Dear Developer"
# # if scenario == 1 or scenario == 2:
# # 	message = message + " and " + contact["co_name"] + "\n"
# message += "\n\n"
# message += "Thank you for your interest in American Frozen Foods!\n\n"
# message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
# message += "Thank you for the opportunity to be of service!"
#
# payload = {
#     "test_mode": 1,
#     "title": "American Frozen Foods Documentation",
#     "subject": "American Frozen Foods Documentation",
#     "message": message,
#     "template_id": 'cf6d6ffacfba521937c0e25fe17744aead9e8ed5',
#     "signers[buyer][name]": 'Developer',
#     "signers[buyer][email_address]": 'developer@dcg.dev',
#     # "custom_fields": json.dumps(custom_fields)
#     # "ccs[cc1][email_address]": "Billyrapp@yahoo.com",
#     # "ccs[cc2][email_address]": "susan.treglia@yahoo.com",
#     # "ccs[cc3][email_address]": "americanfoods5@gmail.com"
# }
#
# response = requests.post(url, data=payload, auth=HTTPBasicAuth('bd14b5416189d99e482a28f8b508ba6a581894ab2f3049eb50b779492da2b832', ''))
#
# if response.status_code == 200:
#     data = response.json()
#     print(data['signature_request'])
#     print(data['signature_request']['signature_request_id'])

# message = "Dear " + "rohit"
# message = message + " and " +"Rahul" + "\n"
# message += "\n\n"
# message += "Thank you for your interest in American Frozen Foods!\n\n"
# message += "Included in the link above are the documents associated with your purchase(s). Please complete all of the blank fields to the best of your ability and sign each of the documents. Where information has been pre-filled for you, please review it to ensure there are no errors. If you are unable to complete a required field (marked with a red asterisk), please write “N/A” in that field and someone will reach out to you after you submit the form. Should any of the pre-filled fields need corrections or you have any other questions, please reach out to Bill at American Frozen Foods. You can reach him at (800) 233-5554 x3330.\n\n"
# message += "Thank you for the opportunity to be of service!"
#
# print(message)

# from authy.api import AuthyApiClient
#
# authy_api = AuthyApiClient('Pc99f7ztx1M2UTlrUR3qRl57HJHADFML')
#
# sms = authy_api.users.delete(164207175)
# print(sms.ok())

# a= ["food", "appliance"]
#
#
# for i in a:
#     print(a[i])

from datetime import date
import datetime
import holidays


# print('2020-12-25' in us_holidays)
# today = datetime.date.today()
# third_date = today+datetime.timedelta(days=3)


# Public Holidays Check
# def check_public_holiday(selected_date):
#     final_date = selected_date
#     us_holidays = holidays.UnitedStates()
#     # Sunday Check
#     if final_date.weekday() == 6:
#         print("This Date %s Comes on Sunday, Selecting next day" % final_date)
#         final_date = final_date + datetime.timedelta(days=1)
#         return check_public_holiday(final_date)
#     else:
#         day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
#         print("This Date %s Comes on" % final_date, day_name[final_date.weekday()])
#
#     # Public Holiday Check
#     if final_date in us_holidays:
#         print("This Date %s Comes on Public Holiday %s, Selecting next day" % (final_date, us_holidays.get(final_date)))
#         final_date = final_date + datetime.timedelta(days=1)
#         return check_public_holiday(final_date)
#     else:
#         print("Final Selected Date is", final_date)
#         return final_date
#
#
# today = datetime.date.today()
# third_date = today + datetime.timedelta(days=26)
# data = check_public_holiday(today + datetime.timedelta(days=23))

# print("Date is ", data)
# print(today)
# day = datetime.datetime.strptime(str(today), '%Y-%m-%d').weekday()
# print(day)
# day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday','Sunday']
# print(day_name[day])

# today = datetime.date.today()
# third_date = today + datetime.timedelta(days=3)
#
# print(third_date)
