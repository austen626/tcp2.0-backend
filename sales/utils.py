import hashlib, hmac


def xstr(s):
    return '' if s is None else str(s)


def verify_hash(request_hash, event_hash):
    if request_hash == event_hash:
        return True
    return False


def get_hellosign_event_hash(apikey, event_time, event_type):
    apikey = apikey.encode('utf-8')
    event_time = event_time.encode('utf-8')
    event_type = event_type.encode('utf-8')
    return hmac.new(apikey, (event_time + event_type), hashlib.sha256).hexdigest()


def get_status_from_hellosign_event(event_type):
    opened = ['signature_request_viewed']
    signed = ['signature_request_signed', 'signature_request_all_signed']
    delivered = ['signature_request_sent']
    not_delivered = ['signature_request_email_bounce', 'signature_request_invalid']
    delivery_in_queue = ['signature_request_prepared']
    error = ['file_error', 'unknown_error', 'sign_url_invalid']

    # ignored = ['signature_request_downloadable', 'signature_request_declined', 'signature_request_reassigned',
    #            'signature_request_remind', 'signature_request_canceled', 'account_confirmed', 'template_created',
    #            'template_error']

    if event_type in opened:
        return 'opened'
    elif event_type in signed:
        return 'signed'
    elif event_type in delivered:
        return 'delivered'
    elif event_type in not_delivered:
        return 'not_delivered'
    elif event_type in delivery_in_queue:
        return 'delivery_in_queue'
    elif event_type in error:
        return 'error'
    else:
        return
