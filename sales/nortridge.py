from pprint import pprint

import requests
import random
import string
from datetime import datetime
from .models import NortridgeToken

# Get Token from Nortridge
def getToken():
    url = 'https://auth.nortridgehosting.com/10.0.1/core/connect/token'
    data = {
        "username": "DCGTest8370",
        "password": "!17nLs468",
        "client_id": "08370T",
        "client_secret": "x8LrG!Za^",
        "scope": "openid api server:rnn1-nls-sqlt01.nls.nortridge.tech db:Travis_Capital_Test",
        "grant_type": "password"
    }



    r = requests.post(url, data=data)
    result = r.json()
    print(result)
    return result["access_token"]


# Return Token from local database
def getdbToken():
    data = NortridgeToken.objects.get(id=1)
    print("Token Number", data.token)
    return data.token


# Update New token in the database
def updatedbToken():
    data = NortridgeToken.objects.get(id=1)
    data.token = getToken()
    data.save()
    print("Updated Token")
    return data.token


def revokeToken(token):
    url = "https://auth.nortridgehosting.com/10.0.1/core/connect/revocation"
    data = {
        "token_type_hint": "access_token",
        "token": token
    }
    header = {
        "Authorization": "Basic MDgzNzBUOng4THJHIVphXg=="
    }
    r = requests.post(url, headers=header, data=data)
    print(r)


def createContact(customer):
    try:
        token = getdbToken()
        #cif_number = 'TCP-' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)) + '-' + str(customer.id)
        cif_number = '158'+str(customer.id)

        nameArr = customer.name.split()
        first_name = nameArr[0]
        last_name = ''
        if len(nameArr) > 1:
            last_name = nameArr[1]

        payload = """<?xml version="1.0" encoding="UTF-8"?>
    <NLS>
    <CIF
        CIFNumber="%s"
        EmailAddress1="%s"
        FirstName1="%s"
        LastName1="%s"
        FullName1="%s"
        StreetAddress1="%s"
        City="%s"
        State="%s"
        ZipCode="%s"
        Entity="individual">
        <CIFPHONENUMBER PhoneNumber = "%s"></CIFPHONENUMBER>
    </CIF>
    </NLS>
    """ % (
            cif_number,
            customer.email,
            first_name,
            last_name,
            customer.name,
            customer.street,
            customer.city,
            customer.state,
            customer.zip,
            customer.cell_phone
        )
        url = "https://api.nortridgehosting.com/10.0.1/nls/xml-import"
        headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/xml"
        }
        r = requests.post(url, headers=headers, data=payload)

        result = r.json()
        if result['status']['code'] != 200:
            raise Exception("Invalid Token")
        return cif_number
    except Exception as e:
        token = updatedbToken()
        #cif_number = 'TCP-' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)) + '-' + str(customer.id)
        cif_number = '158' + str(customer.id)
        nameArr = customer.name.split()
        first_name = nameArr[0]
        last_name = ''
        if len(nameArr) > 1:
            last_name = nameArr[1]

        payload = """<?xml version="1.0" encoding="UTF-8"?>
            <NLS>
            <CIF
                CIFNumber="%s"
                EmailAddress1="%s"
                FirstName1="%s"
                LastName1="%s"
                FullName1="%s"
                StreetAddress1="%s"
                City="%s"
                State="%s"
                ZipCode="%s"
                Entity="individual">
                <CIFPHONENUMBER PhoneNumber = "%s"></CIFPHONENUMBER>
            </CIF>
            </NLS>
            """ % (
            cif_number,
            customer.email,
            first_name,
            last_name,
            customer.name,
            customer.street,
            customer.city,
            customer.state,
            customer.zip,
            customer.cell_phone
        )
        url = "https://api.nortridgehosting.com/10.0.1/nls/xml-import"
        headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/xml"
        }
        r = requests.post(url, headers=headers, data=payload)


        return cif_number


def searchContacts(last_name, city):
    try:
        token = getdbToken()
        url = "https://api.nortridgehosting.com/10.0.1/contacts/search"
        header = {
            "Authorization": "Bearer " + token
        }
        data = {
            "Lastname1": "%"+last_name,
            "City": "%"+city
        }
        r = requests.post(url, headers=header, data=data)
        result = r.json()
        if result['status']['code'] != 200:
            raise Exception("Invalid Token No data found")
        return result
    except Exception as e:
        token = updatedbToken()
        url = "https://api.nortridgehosting.com/10.0.1/contacts/search"
        header = {
            "Authorization": "Bearer " + token
        }
        data = {
            "Lastname1": "%" + last_name,
            "City": "%" + city
        }
        r = requests.post(url, headers=header, data=data)
        result = r.json()
        return result

def searchContactsByPhoneEmail(phone,email):
    try:
        token = getdbToken()
        url = "https://api.nortridgehosting.com/10.0.1/contacts/search"
        header = {
            "Authorization": "Bearer " + token
        }
        data = {
            "Phone_Number":phone,
            "Email": email
        }
        r = requests.post(url, headers=header, data=data)
        result = r.json()
        print(result)
        if result['status']['code'] != 200:
            raise Exception("Invalid Token No data found")
        return result
    except Exception as e:
        token = updatedbToken()
        url = "https://api.nortridgehosting.com/10.0.1/contacts/search"
        header = {
            "Authorization": "Bearer " + token
        }
        data = {
            "Phone_Number": phone,
            "Email": email
        }
        r = requests.post(url, headers=header, data=data)
        result = r.json()
        print(result)
        return result


def getContact(cifno):
    try:
        token = getdbToken()
        url = "https://api.nortridgehosting.com/10.0.1/contacts/%s" % (cifno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        if result['status']['code'] != 200:
            raise Exception("Invalid Token No data found")
        return result['payload']['data']
    except Exception as e:
        token = updatedbToken()
        url = "https://api.nortridgehosting.com/10.0.1/contacts/%s" % (cifno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        return result['payload']['data']


def getContactloan(cifno):
    cont_loans = []
    try:
        token = getdbToken()
        url = "https://api.nortridgehosting.com/10.0.1/contacts/%s/loans" % (cifno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        print(result)
        cont_loans = result['payload']['data']
    except Exception as e:
        token = updatedbToken()
        url = "https://api.nortridgehosting.com/10.0.1/contacts/%s/loans" % (cifno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        cont_loans = result['payload']['data']

    data_response = []
    date_list = []
    import traceback as tb
    for cons in cont_loans:
        date_list.append(datetime.timestamp(datetime.strptime(cons['Open_Date'],'%Y-%m-%dT%H:%M:%S')))#cons['Open_Date'])
        data_details = get_details(cons['Acctrefno'])
        try:
            #payment_history = getPaymentHistoryRaw(cons['Acctrefno'])[-1]
            amortization_schedule_data = getAmortization_Schedule(cons['Acctrefno'])
            print(amortization_schedule_data)
            details_dict = {}
            if data_details != []:
                details_dict['Total_Balance'] = data_details[0]['Current_Payoff_Balance']
                details_dict['Maturity_Date'] = data_details[0]['Curr_Maturity_Date']
                details_dict['Total_Curr_Due'] = data_details[0]['Total_Current_Due_Balance']
                details_dict['Total_Past_Due'] = data_details[0]['Total_Past_Due_Balance']
                details_dict['Days_Past_Due'] = data_details[0]['Days_Past_Due']
                details_dict['Last_Payment_Amount'] = amortization_schedule_data['PaymentAmount']
                details_dict['Last_Payment_Date'] = amortization_schedule_data['PaymentDate']
                cons['Details'] = details_dict
        except Exception as e:
            print(e)
            tb.print_exc()
            details_dict = {}
            if data_details != []:
                details_dict['Total_Balance'] = data_details[0]['Current_Payoff_Balance']
                details_dict['Maturity_Date'] = data_details[0]['Curr_Maturity_Date']
                details_dict['Total_Curr_Due'] = data_details[0]['Total_Current_Due_Balance']
                details_dict['Total_Past_Due'] = data_details[0]['Total_Past_Due_Balance']
                details_dict['Days_Past_Due'] = data_details[0]['Days_Past_Due']
                details_dict['Last_Payment_Amount'] = 'NA'
                details_dict['Last_Payment_Date'] = None
                cons['Details'] = details_dict


        data_response.append(cons)
    #date time stamp sorting
    date_list.sort(reverse=True)
    print(date_list)

    res = []
    loan_number_list = []
    #sorting based on date
    for dt in date_list:
        for data in data_response:
            data_dt = datetime.timestamp(datetime.strptime(data['Open_Date'],'%Y-%m-%dT%H:%M:%S'))
            if dt == data_dt:
                if data['Loan_Number'] not in loan_number_list:
                    res.append(data)
                loan_number_list.append(data['Loan_Number'])
    #swaping based on Loan_Number with same date
    for i in range(0,len(res)):
        r = res[i]
        try:
            nxt_r = res[i+1]
            if r['Open_Date'] == nxt_r['Open_Date']:
                Loan_r = int(r['Loan_Number'])
                Loan_nxt_r = int(nxt_r['Loan_Number'])
                if Loan_r<Loan_nxt_r:
                    res[i] = nxt_r
                    res[i+1] = r
        except:
            pass

    return res
def get_details(loan_id):
    try:
        token = getdbToken()
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s" % (loan_id)
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + token
        }
        res= requests.get(url, headers=headers)
        result = res.json()
        return [result['payload']['data']]
    except:
        token = updatedbToken()
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s" % (loan_id)
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + token
        }
        res = requests.get(url, headers=headers)
        result = res.json()
        return [result['payload']['data']]
def getPaymentHistoryRaw(Acctrefno):
    res = {}
    loan_transaction = []
    try:
        token = getdbToken()#getToken()#
        loan_transaction = get_loan_transation(Acctrefno,token)
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/payment-history" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        return result['payload']['data']
    except Exception as e:
        print(e)
        token = updatedbToken()
        loan_transaction = get_loan_transation(Acctrefno,token)
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/payment-history" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        return result['payload']['data']


def getAmortization_Schedule(Acctrefno):
    amortization_data = []
    try:
        token = getdbToken()#getToken()#
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/amortization-schedule" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        amortization_data = result['payload']['data']
    except Exception as e:
        print(e)
        token = updatedbToken()
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/amortization-schedule" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        amortization_data = result['payload']['data']
    today_date = datetime.now().date()#datetime.date.today()
    dict_data = {}
    for amo in amortization_data:
        PaymentDate = datetime.strptime(amo['PaymentDate'], '%m/%d/%Y').date()
        if PaymentDate>today_date:
            dict_data['PaymentDate'] = amo['PaymentDate']
            dict_data['PaymentAmount'] = amo['PaymentAmount']
            break
    return dict_data

def getPaymentHistory(Acctrefno):
    res = {}
    data = []
    loan_transaction = []
    try:
        token = getdbToken()#getToken()#
        loan_transaction = get_loan_transation(Acctrefno, token)
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/payment-history" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        data = result['payload']['data']
    except Exception as e:
        print(e)
        token = updatedbToken()
        loan_transaction = get_loan_transation(Acctrefno, token)
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/payment-history" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        data = result['payload']['data']
    #payment_types = ['PI', 'L', 'U1', 'F']
    transaction_code = [i for i in range(200,251) if i%2==0]
        #selecting all even trnsation code from 200-250
        #[200, 202, 204, 206, 208, 210, 212, 214,
        #216, 218, 220, 222, 224, 226, 228, 230,
        #232, 234, 236, 238, 240, 242, 244, 246, 248, 250]
    data_res = []


    for hist in data:
        if hist['Transaction_Code'] in transaction_code:
            data_details = {}
            data_details['Row_Id'] = hist['Row_Id']
            data_details['Date_Due'] = hist['Date_Due']
            data_details['Amount_Paid'] = hist['Payment_Amount']
            data_details['Payment_Effective_Date'] = hist['Date_Paid']
            data_details['Description'] = hist['Payment_Description']
            check_method = [1]
            ach_method = [5, 7, 9, 11]
            card_method = [8, 6, 10, 12, 13]
            #credit_method = [13]
            method_no = hist['Payment_Method_No']
            if method_no in check_method:
                data_details['Payment_Method'] = 'Check'
            elif method_no in ach_method:
                data_details['Payment_Method'] = 'ACH'
            elif method_no in card_method:
                data_details['Payment_Method'] = 'Card'
            else:
                data_details['Payment_Method'] = "None"#str(method_no)
            data_details['Payment_Type'] = hist['Payment_Type']
            data_details['Transaction_Code'] = hist['Transaction_Code']
            data_details['Transaction_Reference_No'] = hist['Transaction_Reference_No']
            data_res.append(data_details)

    payment_types_list = list(dict.fromkeys([dt['Payment_Type'] for dt in data_res]))
    payment_type_data_dict = {}
    #adding data to dict where payment type as key
    for ptl in payment_types_list:
        data_list = []
        for data in data_res:
            if ptl == data['Payment_Type']:
                data_list.append(data)
        payment_type_data_dict[ptl] = data_list
    #key itaraion for date based data coupling and extraction
    print(payment_types_list)
    res_data = []
    for key in payment_type_data_dict:
        dict_temp = {}
        hist_data = payment_type_data_dict[key]
        payed_date_list = list(dict.fromkeys([hdt['Payment_Effective_Date'] for hdt in hist_data]))
        print('dates = ', payed_date_list)
        for pdt in payed_date_list:
            payment = 0
            for dt in hist_data:
                if pdt == dt['Payment_Effective_Date'] :
                    payment = round(payment + dt['Amount_Paid'], 2)
                    dt['Amount_Paid'] = payment
                    if dt['Transaction_Code'] == 204:
                        dt['Description'] = 'Payment'

                    dict_temp[pdt] = dt

        for tk in dict_temp:
            res_data.append(dict_temp[tk])
    #geting all odd trnsation code for reverse payment
    odd_trans_code = [t['Transaction_Code'] for t in loan_transaction if t['Transaction_Code']%2 != 0 ]
    print('odd_trans_code=',odd_trans_code)

    trans_des = []
    for trans in loan_transaction:
        transation_code = trans['Transaction_Code']
        # removal of reverse trnsation
        if transation_code in odd_trans_code :
            #for removing from transation
            reversal_transrefno = trans['Reversal_Transrefno']
            trans_ref_no = 0
            for tr in loan_transaction:
                if tr['Transrefno']== reversal_transrefno:
                    trans_ref_no = tr['Transaction_Reference_No']
                    loan_transaction.remove(tr)
            #for removing from payment history
            for res in res_data:
                if res['Transaction_Reference_No']== trans_ref_no:
                    res_data.remove(res)
    for trans in loan_transaction:

        transation_code = trans['Transaction_Code']
        if transation_code == 100 or transation_code == 260:
            tdict = {}
            tdict['Payment_Effective_Date'] = trans['Transaction_Date']
            tdict['Amount_Paid'] = trans['Transaction_Amount']
            tdict['Description'] = trans['Transaction_Description']
            trans_des.append(tdict)
    res_data.reverse()
    trans_des.reverse()
    data_list = list()
    #getting all Payment_Effective_Date
    payment_dates = [datetime.strptime(r['Payment_Effective_Date'], '%Y-%m-%dT%H:%M:%S').date() for r in res_data]
    #sorting Payment_Effective_Date list in desending order
    payment_dates.sort(reverse=True)
    #removing duplicates
    payment_dates = list(dict.fromkeys(payment_dates))
    #adding data with desending date order
    for pd in payment_dates:
        for rd in res_data:
            rd_date = datetime.strptime(rd['Payment_Effective_Date'], '%Y-%m-%dT%H:%M:%S').date()
            if pd == rd_date:
                data_list.append(rd)
    #swaping same date data based on row_id numbers
    for i in range(0,len(data_list)):
        try:
            dl_row = data_list[i]
            nxt_dl_row = data_list[i+1]
            dr_date = datetime.strptime(dl_row['Payment_Effective_Date'], '%Y-%m-%dT%H:%M:%S').date()
            ndr_date = datetime.strptime(nxt_dl_row['Payment_Effective_Date'], '%Y-%m-%dT%H:%M:%S').date()
            if dr_date == ndr_date:
                dl_row_id = dl_row['Row_Id']
                nxt_dl_row_id = nxt_dl_row['Row_Id']
                if nxt_dl_row_id>dl_row_id:
                    data_list[i] = nxt_dl_row
                    data_list[i+1] = dl_row

        except:
            pass

    response_data = data_list+trans_des
    return response_data

def getPaymentHistory_old(Acctrefno):
    res = {}
    data = []
    loan_transaction = []
    try:
        token = getdbToken()#getToken()#
        loan_transaction = get_loan_transation(Acctrefno, token)
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/payment-history" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        data = result['payload']['data']
    except Exception as e:
        print(e)
        token = updatedbToken()
        loan_transaction = get_loan_transation(Acctrefno, token)
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/payment-history" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        data = result['payload']['data']
    payment_types = ['PI', 'L', 'U1', 'F']
    data_res = []

    for hist in data:
        if hist['Payment_Type'] in payment_types:
            data_details = {}
            data_details['Date_Due'] = hist['Date_Due']
            data_details['Amount_Paid'] = hist['Payment_Amount']
            data_details['Payment_Effective_Date'] = hist['Date_Paid']
            data_details['Description'] = hist['Payment_Description']
            check_method = [1]
            ach_method = [5, 7, 9, 11]
            card_method = [8, 6, 10, 12, 13]
            #credit_method = [13]
            method_no = hist['Payment_Method_No']
            if method_no in check_method:
                data_details['Payment_Method'] = 'Check'
            elif method_no in ach_method:
                data_details['Payment_Method'] = 'ACH'
            elif method_no in card_method:
                data_details['Payment_Method'] = 'Card'
            else:
                data_details['Payment_Method'] = 'NA'#str(method_no)
            data_details['Payment_Type'] = hist['Payment_Type']
            data_res.append(data_details)
    payed_date_list = list(dict.fromkeys([dt['Payment_Effective_Date'] for dt in data_res]))
    dict_data = {}
    for pdt in payed_date_list:
        payment = 0
        for dt in data_res:
            if pdt == dt['Payment_Effective_Date'] and dt['Payment_Type'] == 'PI':
                payment = round(payment + dt['Amount_Paid'], 2)
                dt['Amount_Paid'] = payment
                dt['Description'] = 'Payment'
                dict_data[pdt] = dt
            #for non PI payment type
            elif pdt == dt['Payment_Effective_Date']:
                dict_data[pdt+dt['Date_Due']] = dt


    response_data = [dict_data[key] for key in dict_data]

    trans_des = []
    for trans in loan_transaction:
        transation_code = trans['Transaction_Code']

        if transation_code == 100 or transation_code == 260:
            tdict = {}
            tdict['Payment_Effective_Date'] = trans['Transaction_Date']
            tdict['Amount_Paid'] = trans['Transaction_Amount']
            tdict['Description'] = trans['Transaction_Description']
            trans_des.append(tdict)
    response_data.reverse()
    response_data = response_data+trans_des
    return response_data


def get_loan_transation(loan_id,token):
    try:
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/transactions" % (loan_id)
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + token
        }
        res= requests.get(url, headers=headers)
        result = res.json()
        return result['payload']['data']
    except:
        return []


def getPaymentDue(Acctrefno,token):
    try:
        token = getdbToken()
        #Acctrefno = int(Acctrefno)
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/payments-due" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        print("PaymentDue APi")
        print(result)
        if result==[]:
            return []
        else:
            print(result['payload']['data'], type(result['payload']['data']))
            return result['payload']['data']
    except Exception as e:
        token = updatedbToken()
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/payments-due" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }
        r = requests.get(url, headers=header)
        result = r.json()
        if result==[]:
            return []
        else:
            print(result['payload']['data'], type(result['payload']['data']))
            return result['payload']['data']
        # print(result['payload']['data'],type(result['payload']['data']))
        # return result['payload']['data']


def getPaymentinfo(Acctrefno):
    try:
        token = getdbToken()
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/payment-info" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        return result['payload']['data']
    except Exception as e:
        token = updatedbToken()
        url = "https://api.nortridgehosting.com/10.0.1/loans/%s/payment-info" % (Acctrefno)
        header = {
            "Authorization": "Bearer " + token
        }

        r = requests.get(url, headers=header)
        result = r.json()
        return result['payload']['data']

# pprint(getContactloan(1))
# pprint(getPaymentHistory(483))
# print(revokeToken("3526d2f906ccb9d0a1cee0064564a0d8"))
# print(getToken())
# r = searchContacts("","HAMPTON")
#
# final = r['payload']['data']
# for data in final:
#     print(data)
# print(getContact(103))
